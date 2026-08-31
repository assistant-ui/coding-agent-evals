#!/usr/bin/env python3
"""Walk Harbor jobs/ into report/latest.json + report/data.js."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_OFF = frozenset({"off", "0", "false", "no", "disabled"})
FOLDER_RE = re.compile(r"(?:^|/)(pb-1|pb-2|g\d[\w-]*)(?:/|$)")


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


def mcp_from_result(data: dict) -> str:
    cfg = data.get("config") or {}
    env = (cfg.get("environment") or {}).get("env") or {}
    raw = str(env.get("PB1_MCP") or "on").strip().lower()
    if raw in MCP_OFF:
        return "off"
    return "on"


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


def load_check_titles(task_dir: Path) -> dict[str, str]:
    path = task_dir / "tests" / "checks.py"
    if not path.is_file():
        return {}
    spec = importlib.util.spec_from_file_location(f"checks_{task_dir.name}", path)
    if spec is None or spec.loader is None:
        return {}
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return {}
    titles = {}
    for check in getattr(mod, "CHECKS", ()):
        titles[check.id] = check.title
    return titles


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
    titles: dict[str, str] = {}
    cases_out = []
    for case in catalog["cases"]:
        task_dir = tasks_dir / case["folder"]
        titles.update(load_check_titles(task_dir))
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
            key = (run["caseId"], run["harness"], run["mcp"])
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
                if not fail["title"]:
                    fail["title"] = titles.get(fail["id"], fail["id"])
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
            key = (rec["caseId"], rec["agent"], rec["mcp"])
            run = {
                "caseId": rec["caseId"],
                "harness": rec["agent"],
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

    fail_titles = {cid: {"title": title, "notes": ""} for cid, title in titles.items()}
    for case in cases_out:
        case["verifier"] = oracles.get(case["id"])

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cases": cases_out,
        "harnesses": [
            {
                "id": a["id"],
                "name": a["name"],
                "model": a["model"].split("/", 1)[-1],
                "model_id": a["model"],
                "tier": a["tier"],
            }
            for a in catalog["agents"]
        ],
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
