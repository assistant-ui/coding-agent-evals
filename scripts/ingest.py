#!/usr/bin/env python3
"""Walk Harbor jobs/ into report/latest.json + report/data.js."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_OFF = frozenset({"off", "0", "false", "no", "disabled"})
FOLDER_RE = re.compile(r"(?:^|/)(pb-1|pb-2|g\d[\w-]*)(?:/|$)")
CHECK_RE = re.compile(
    r'Check\(\s*"(?P<id>[A-Z0-9-]+)"\s*,\s*"(?P<title>(?:[^"\\]|\\.)*)"\s*,\s*"(?P<group>[^"]+)"',
    re.DOTALL,
)


def load_catalog(path: Path) -> dict:
    return json.loads(path.read_text())


def iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def seconds_between(start: str | None, end: str | None) -> float | None:
    a, b = iso_dt(start), iso_dt(end)
    if a is None or b is None:
        return None
    return max(0.0, (b - a).total_seconds())


def surface_from_result(data: dict) -> str:
    cfg = data.get("config") or {}
    env = (cfg.get("environment") or {}).get("env") or {}
    raw = str(env.get("PB1_SURFACE") or "").strip().lower()
    if raw in {"skills", "skill"}:
        return "skills"
    if raw in {"none", "off"}:
        return "none"
    if raw in {"mcp", "on"}:
        return "mcp"
    agent = cfg.get("agent") or {}
    if agent.get("skills"):
        return "skills"
    mcp = str(env.get("PB1_MCP") or "on").strip().lower()
    if mcp in MCP_OFF:
        return "none"
    return "mcp"


def mode_from_result(data: dict) -> str:
    cfg = data.get("config") or {}
    env = (cfg.get("environment") or {}).get("env") or {}
    raw = str(env.get("PB1_MODE") or "").strip().lower()
    if raw in {"low", "high"}:
        return raw
    agent = cfg.get("agent") or {}
    model = str(agent.get("model_name") or "").strip().lower()
    if any(token in model for token in ("grok-4.6", "claude-fable-5", "gpt-5.6-sol")):
        return "high"
    return "low"


def mcp_from_result(data: dict) -> str:
    """Legacy on/off axis. Prefer surface_from_result."""
    surface = surface_from_result(data)
    if surface == "none":
        return "off"
    if surface == "mcp":
        return "on"
    return surface


def normalize_run_surface(run: dict) -> str:
    raw = str(run.get("surface") or "").strip().lower()
    if raw in {"none", "mcp", "skills"}:
        return raw
    mcp = str(run.get("mcp") or "").strip().lower()
    if mcp in {"off", "none"}:
        return "none"
    if mcp in {"skills", "skill"}:
        return "skills"
    return "mcp"


def folder_from_result(data: dict) -> str | None:
    path = (
        ((data.get("task_id") or {}).get("path"))
        or ((data.get("config") or {}).get("task") or {}).get("path")
        or ""
    )
    path = str(path).rstrip("/")
    name = Path(path).name
    if name:
        return name
    m = FOLDER_RE.search(path)
    return m.group(1) if m else None


def last_agent_message(trial_dir: Path) -> str:
    traj = trial_dir / "agent" / "trajectory.json"
    if not traj.is_file():
        return ""
    try:
        payload = json.loads(traj.read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    last = ""
    for step in payload.get("steps") or []:
        if step.get("source") == "agent" and step.get("message"):
            last = str(step["message"])
    return last


def score_checks(trial_dir: Path) -> tuple[int, int, list[dict]]:
    path = trial_dir / "verifier" / "checks.json"
    if not path.is_file():
        return 0, 0, []
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return 0, 0, []
    passed = 0
    applicable = 0
    failed: list[dict] = []
    for item in payload.get("checks") or []:
        status = str(item.get("status") or "").lower()
        if status == "skipped":
            continue
        applicable += 1
        ok = bool(item.get("passed"))
        if ok:
            passed += 1
        else:
            failed.append(
                {
                    "id": item.get("name") or "",
                    "title": "",
                    "notes": item.get("notes") or "",
                }
            )
    return passed, applicable, failed


def family_of(check_id: str) -> str:
    if check_id.startswith("CQ-G"):
        return "Source · app skeleton"
    if check_id.startswith("CQ-P"):
        return "Source · product wiring"
    if check_id.startswith("CQ"):
        return "Source"
    if check_id.startswith("AR"):
        return "App run · install / build / HTTP"
    if check_id.startswith("BR"):
        return "Browser · Playwright"
    if check_id.startswith("WF-D"):
        return "Workflow · discovery (docs / MCP / skills)"
    if check_id.startswith("WF-S"):
        return "Workflow · scaffold (assistant-ui create)"
    if check_id.startswith("WF-E"):
        return "Workflow · errors during the agent run"
    if check_id.startswith("WF-T"):
        return "Workflow · agent started and tested the app"
    if check_id.startswith("WF"):
        return "Workflow"
    return ""


def load_check_meta(task_dir: Path) -> dict[str, dict[str, str]]:
    """Parse Check(...) from checks.py. Do not exec — dataclass import fails here."""
    path = task_dir / "tests" / "checks.py"
    if not path.is_file():
        return {}
    out: dict[str, dict[str, str]] = {}
    for match in CHECK_RE.finditer(path.read_text()):
        cid = match.group("id")
        out[cid] = {
            "title": match.group("title"),
            "group": match.group("group"),
            "family": family_of(cid),
        }
    return out


def describe_check(check_id: str, meta: dict[str, dict[str, str]]) -> dict[str, str]:
    row = meta.get(check_id) or {}
    title = row.get("title") or check_id
    return {
        "id": check_id,
        "title": title,
        "family": row.get("family") or family_of(check_id),
        "group": row.get("group") or "",
    }


def prompt_for(task_dir: Path) -> str:
    inst = task_dir / "instruction.md"
    if inst.is_file():
        return inst.read_text().strip()
    return ""


def iter_trials(jobs_dir: Path, include: set[str] | None):
    if not jobs_dir.is_dir():
        return
    for job in sorted(jobs_dir.iterdir()):
        if not job.is_dir() or job.name.startswith("."):
            continue
        if include is not None and job.name not in include:
            continue
        for child in sorted(job.iterdir()):
            result = child / "result.json"
            if result.is_file():
                yield job, child, result


def short_model(model: str) -> str:
    return model.split("/", 1)[-1]


def harness_record(agent: dict) -> dict:
    modes = {}
    for name, spec in (agent.get("modes") or {}).items():
        if name not in {"low", "high"}:
            continue
        model = str((spec or {}).get("model") or agent.get("model") or "")
        modes[name] = {
            "model": short_model(model),
            "model_id": model,
            "tier": (spec or {}).get("tier") or agent.get("tier"),
        }
    if "low" not in modes and agent.get("model"):
        modes["low"] = {
            "model": short_model(agent["model"]),
            "model_id": agent["model"],
            "tier": agent.get("tier"),
        }
    low = modes.get("low") or {}
    return {
        "id": agent["id"],
        "name": agent["name"],
        "model": low.get("model") or short_model(str(agent.get("model") or "")),
        "model_id": low.get("model_id") or agent.get("model"),
        "tier": low.get("tier") or agent.get("tier"),
        "modes": modes,
    }


def trial_record(result_path: Path, folder_to_case: dict[str, dict]) -> dict | None:
    try:
        data = json.loads(result_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    folder = folder_from_result(data)
    if folder not in folder_to_case:
        return None
    agent = ((data.get("config") or {}).get("agent") or {}).get("name") or ""
    if not agent:
        agent = (data.get("agent_info") or {}).get("name") or ""
    reward = ((data.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    if reward is None:
        reward_file = result_path.parent / "verifier" / "reward.txt"
        if reward_file.is_file():
            try:
                reward = float(reward_file.read_text().strip())
            except ValueError:
                reward = None
    finished = data.get("finished_at") or ""
    exe = data.get("agent_execution") or {}
    agent_sec = seconds_between(exe.get("started_at"), exe.get("finished_at"))
    cost = (data.get("agent_result") or {}).get("cost_usd")
    passed, applicable, failed = score_checks(result_path.parent)
    return {
        "folder": folder,
        "caseId": folder_to_case[folder]["id"],
        "agent": agent,
        "surface": surface_from_result(data),
        "mode": mode_from_result(data),
        "mcp": mcp_from_result(data),
        "reward": reward,
        "finished_at": finished,
        "agentSec": agent_sec,
        "cost": cost,
        "passed": passed,
        "applicable": applicable,
        "failed": failed,
        "lastMessage": last_agent_message(result_path.parent),
        "trial": str(result_path.parent),
        "job": result_path.parent.parent.name,
    }


def newer(a: dict, b: dict) -> bool:
    ta, tb = iso_dt(a.get("finished_at")), iso_dt(b.get("finished_at"))
    if ta and tb:
        return ta >= tb
    return True


def build_report(
    *,
    catalog: dict,
    tasks_dir: Path,
    jobs_dirs: list[Path],
    existing: dict | None,
    include_jobs: set[str] | None,
) -> dict:
    folder_to_case = {c["folder"]: c for c in catalog["cases"]}
    meta: dict[str, dict[str, str]] = {}
    cases_out = []
    for case in catalog["cases"]:
        task_dir = tasks_dir / case["folder"]
        meta.update(load_check_meta(task_dir))
        cases_out.append(
            {
                "id": case["id"],
                "folder": case["folder"],
                "name": case["name"],
                "prompt": prompt_for(task_dir),
                "verifier": None,
            }
        )

    agent_cells: dict[tuple[str, str, str], dict] = {}
    oracles: dict[str, dict] = {}

    if existing:
        for run in existing.get("runs") or []:
            run = {
                **run,
                "surface": normalize_run_surface(run),
                "mode": run.get("mode") if run.get("mode") in {"low", "high"} else "low",
            }
            key = (run["caseId"], run["harness"], run["surface"], run["mode"])
            agent_cells[key] = run
        for case in existing.get("cases") or []:
            if case.get("verifier"):
                oracles[case["id"]] = case["verifier"]

    for jobs_dir in jobs_dirs:
        for _job, _trial, result in iter_trials(jobs_dir, include_jobs):
            rec = trial_record(result, folder_to_case)
            if rec is None or rec["reward"] is None:
                continue
            for fail in rec["failed"]:
                info = describe_check(fail["id"], meta)
                fail["title"] = info["title"]
                fail["family"] = info["family"]
            if rec["agent"] == "oracle":
                prev = oracles.get(rec["caseId"])
                if prev is None or newer(rec, {"finished_at": prev.get("finished_at")}):
                    oracles[rec["caseId"]] = {
                        "reward": rec["reward"],
                        "job": rec["job"],
                        "trial": rec["trial"],
                        "finished_at": rec["finished_at"],
                    }
                continue
            key = (rec["caseId"], rec["agent"], rec["surface"], rec["mode"])
            run = {
                "caseId": rec["caseId"],
                "harness": rec["agent"],
                "surface": rec["surface"],
                "mode": rec["mode"],
                "mcp": rec["mcp"],
                "reward": rec["reward"],
                "passed": rec["passed"],
                "applicable": rec["applicable"],
                "agentSec": rec["agentSec"],
                "cost": rec["cost"],
                "failed": [f["id"] for f in rec["failed"]],
                "failedDetail": rec["failed"],
                "lastMessage": rec["lastMessage"],
                "trial": rec["trial"],
                "job": rec["job"],
                "finished_at": rec["finished_at"],
            }
            prev = agent_cells.get(key)
            if prev is None or newer(run, prev):
                agent_cells[key] = run

    for run in agent_cells.values():
        details = []
        for fail in run.get("failedDetail") or []:
            info = describe_check(fail.get("id") or "", meta)
            details.append({**fail, "title": info["title"], "family": info["family"]})
        run["failedDetail"] = details

    fail_titles = {
        cid: {
            "title": row["title"],
            "family": row["family"],
            "group": row["group"],
            "notes": "",
        }
        for cid, row in meta.items()
    }
    for case in cases_out:
        case["verifier"] = oracles.get(case["id"])

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cases": cases_out,
        "harnesses": [harness_record(a) for a in catalog["agents"]],
        "fail_titles": fail_titles,
        "runs": list(agent_cells.values()),
    }


def write_report(report_dir: Path, payload: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    latest = report_dir / "latest.json"
    latest.write_text(json.dumps(payload, indent=2) + "\n")
    data_js = report_dir / "data.js"
    data_js.write_text("window.REPORT = " + json.dumps(payload) + ";\n")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--jobs-dir", action="append", default=[], help="Harbor jobs root. Repeatable.")
    p.add_argument("--catalog", default=str(ROOT / "catalog.yaml"))
    p.add_argument("--tasks-dir", default=str(ROOT / "tasks"))
    p.add_argument("--report-dir", default=str(ROOT / "report"))
    p.add_argument("--include-job", action="append", default=[], help="Only these job folder names. Repeatable.")
    p.add_argument("--merge-existing", action="store_true")
    args = p.parse_args()
    catalog = load_catalog(Path(args.catalog))
    report_dir = Path(args.report_dir)
    existing = None
    latest = report_dir / "latest.json"
    if args.merge_existing and latest.is_file():
        existing = json.loads(latest.read_text())
    jobs_dirs = [Path(p) for p in args.jobs_dir] or [ROOT / "jobs"]
    include = set(args.include_job) or None
    payload = build_report(
        catalog=catalog,
        tasks_dir=Path(args.tasks_dir),
        jobs_dirs=jobs_dirs,
        existing=existing,
        include_jobs=include,
    )
    write_report(report_dir, payload)
    n_runs = len(payload["runs"])
    n_oracles = sum(1 for c in payload["cases"] if c.get("verifier"))
    print(f"Wrote {report_dir / 'latest.json'} ({n_runs} agent cells, {n_oracles} oracle badges)")


if __name__ == "__main__":
    main()
