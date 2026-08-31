#!/usr/bin/env python3
"""Four individual OpenAI judge calls on one compact transcript."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parents[1]
_JUDGE_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))
if str(_JUDGE_DIR) not in sys.path:
    sys.path.insert(0, str(_JUDGE_DIR))

from lib.transcript import (  # noqa: E402
    MAX_TRANSCRIPT_TOKENS,
    adapt_transcript,
    estimate_tokens,
    parse_trajectory,
    serialize_transcript,
)
from schema import JudgeVerdict  # noqa: E402
from test_workflow import error_judge_skips  # noqa: E402

PROMPTS_DIR = _JUDGE_DIR / "prompts"
CHECK_IDS = ("WF-E-01", "WF-E-02", "WF-T-01", "WF-T-02")
JUDGE_TIMEOUT_SEC = 30
MAX_OUTPUT_TOKENS = 512
RETRY_STATUSES = {429, 500, 502, 503, 504}


class JudgeInfraError(Exception):
    """Missing key, API failure, or unusable verdict — not an agent fail."""


def _read(path: Path) -> str:
    return path.read_text().strip()


def _instruction_text(path: Path) -> str:
    if path.is_file():
        return path.read_text().strip()
    fallback = PROMPTS_DIR / "TASK.md"
    if fallback.is_file():
        return fallback.read_text().strip()
    raise JudgeInfraError(f"instruction not found: {path}")


def _user_message(instruction: str, rubric: str, compact: str, output_spec: str) -> str:
    return (
        "TASK INPUT\n"
        f"{instruction}\n\n"
        "CHECK\n"
        f"{rubric}\n\n"
        "CONTEXT\n"
        f"{compact}\n\n"
        "OUTPUT\n"
        f"{output_spec}\n"
    )


def _set_gate(path: Path, check_id: str, passed: bool, status: str, notes: str) -> None:
    data: dict[str, dict[str, object]] = {}
    if path.is_file():
        data = json.loads(path.read_text())
    data[check_id] = {"passed": passed, "status": status, "notes": notes}
    path.write_text(json.dumps(data, indent=2) + "\n")


def _mark_error(gates: Path, notes: str) -> None:
    data: dict[str, dict[str, object]] = {}
    if gates.is_file():
        data = json.loads(gates.read_text())
    for check_id in CHECK_IDS:
        current = data.get(check_id) or {}
        if current.get("status") in {"passed", "failed", "error", "skipped"}:
            continue
        data[check_id] = {"passed": False, "status": "error", "notes": notes}
    gates.parent.mkdir(parents=True, exist_ok=True)
    gates.write_text(json.dumps(data, indent=2) + "\n")


def _call_openai(system: str, user: str) -> JudgeVerdict:
    from openai import APIStatusError, APITimeoutError, OpenAI

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise JudgeInfraError("OPENAI_API_KEY missing")
    model = os.environ.get("JUDGE_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna"
    client = OpenAI(api_key=api_key, timeout=JUDGE_TIMEOUT_SEC)
    kwargs: dict[str, object] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "response_format": JudgeVerdict,
        "max_completion_tokens": MAX_OUTPUT_TOKENS,
        "reasoning_effort": "low",
    }
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            try:
                completion = client.chat.completions.parse(**kwargs)
            except TypeError:
                kwargs.pop("reasoning_effort", None)
                completion = client.chat.completions.parse(**kwargs)
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                raise JudgeInfraError("judge returned empty structured output")
            return parsed
        except TypeError as exc:
            last_error = exc
            kwargs.pop("reasoning_effort", None)
            if "max_completion_tokens" in kwargs:
                kwargs.pop("max_completion_tokens")
                kwargs["max_tokens"] = MAX_OUTPUT_TOKENS
            continue
        except APITimeoutError as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
                continue
        except APIStatusError as exc:
            last_error = exc
            if exc.status_code in RETRY_STATUSES and attempt == 0:
                time.sleep(1)
                continue
            raise JudgeInfraError(f"OpenAI HTTP {exc.status_code}") from exc
        except JudgeInfraError:
            raise
        except Exception as exc:  # noqa: BLE001 — sandbox SDK surface varies
            raise JudgeInfraError(str(exc) or type(exc).__name__) from exc
    raise JudgeInfraError(str(last_error) if last_error else "judge call failed")


def run_judges(
    atif: Path,
    instruction_path: Path,
    out_dir: Path,
    gates: Path,
) -> None:
    if not atif.is_file():
        raise JudgeInfraError(f"trajectory not found: {atif}")
    adapted = adapt_transcript(parse_trajectory(atif))
    compact = serialize_transcript(adapted.parts)
    tokens = estimate_tokens(compact)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "compact-transcript.txt").write_text(compact)
    (out_dir / "compact-transcript-tokens.txt").write_text(f"{tokens}\n")
    if tokens > MAX_TRANSCRIPT_TOKENS:
        raise JudgeInfraError(
            f"compact transcript is {tokens} tokens (cap {MAX_TRANSCRIPT_TOKENS})"
        )
    system = _read(PROMPTS_DIR / "SYSTEM.md")
    output_spec = _read(PROMPTS_DIR / "OUTPUT.md")
    instruction = _instruction_text(instruction_path)
    error_notes = ""
    skips = error_judge_skips(adapted.tool_calls)
    for check_id, notes in skips.items():
        _set_gate(gates, check_id, True, "skipped", notes)
        (out_dir / f"judge-output-{check_id}.json").write_text(
            json.dumps(
                {"check_id": check_id, "verdict": "skipped", "reason": notes},
                indent=2,
            )
            + "\n"
        )
    for check_id in CHECK_IDS:
        if check_id in skips:
            continue
        rubric = _read(PROMPTS_DIR / f"{check_id}.md")
        user = _user_message(instruction, rubric, compact, output_spec)
        try:
            verdict = _call_openai(system, user)
        except JudgeInfraError as exc:
            error_notes = str(exc)
            _set_gate(gates, check_id, False, "error", error_notes)
            (out_dir / f"judge-output-{check_id}.json").write_text(
                json.dumps({"error": error_notes}, indent=2) + "\n"
            )
            continue
        payload = verdict.model_dump()
        payload["check_id"] = check_id
        (out_dir / f"judge-output-{check_id}.json").write_text(
            json.dumps(payload, indent=2) + "\n"
        )
        if verdict.verdict == "insufficient_evidence":
            _set_gate(
                gates,
                check_id,
                False,
                "error",
                verdict.reason or "insufficient_evidence",
            )
            error_notes = error_notes or "insufficient_evidence"
            continue
        passed = verdict.verdict == "pass"
        _set_gate(
            gates,
            check_id,
            passed,
            "passed" if passed else "failed",
            verdict.reason,
        )
    if error_notes:
        raise JudgeInfraError(error_notes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--atif", type=Path, required=True)
    parser.add_argument("--instruction", type=Path, default=Path("/instruction.md"))
    parser.add_argument("--out-dir", type=Path, default=Path("/logs/verifier"))
    parser.add_argument("--gates", type=Path, default=Path("/logs/verifier/gates.json"))
    args = parser.parse_args()
    try:
        run_judges(args.atif, args.instruction, args.out_dir, args.gates)
    except JudgeInfraError as exc:
        _mark_error(args.gates, str(exc))
        print(f"judge infra error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
