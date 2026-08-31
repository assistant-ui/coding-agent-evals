#!/usr/bin/env python3
"""Write named Harbor checks and equal-1 pass-rate reward from gates + pytest."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from checks import CHECKS, id_from_pytest_name

# Planned N/A only. Runtime skips (cascade, "no submit") count as fails.
_PLANNED_NA_PREFIXES = (
    "gold skips workflow",
    "no assistant-ui create command",
    "no TypeScript or package build command",
)


def is_planned_na(check: dict[str, object]) -> bool:
    if check.get("status") != "skipped":
        return False
    notes = str(check.get("notes") or "")
    return notes.startswith(_PLANNED_NA_PREFIXES)


def normalize_runtime_skips(
    checks: list[dict[str, object]],
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for check in checks:
        if check.get("status") == "skipped" and not is_planned_na(check):
            row = dict(check)
            row["passed"] = False
            row["status"] = "failed"
            out.append(row)
            continue
        out.append(check)
    return out


def write_results(
    checks_path: Path, reward_path: Path, checks: list[dict[str, object]]
) -> None:
    checks = normalize_runtime_skips(checks)
    checks_path.write_text(json.dumps({"checks": checks}, indent=2) + "\n")
    if any(check.get("status") == "error" for check in checks):
        if reward_path.exists():
            reward_path.unlink()
        return
    applicable = [check for check in checks if not is_planned_na(check)]
    if not applicable:
        reward_path.write_text("0.0000\n")
        return
    n_passed = sum(1 for check in applicable if check.get("passed"))
    reward_path.write_text(f"{n_passed / len(applicable):.4f}\n")


def _junit_rows(path: Path) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    if not path.is_file():
        return rows
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    for suite in suites:
        for case in suite.findall("testcase"):
            raw_name = case.get("name") or "unnamed"
            check_id = id_from_pytest_name(raw_name)
            if check_id is None:
                continue
            skipped = case.find("skipped")
            failure = case.find("failure")
            error = case.find("error")
            problem = failure if failure is not None else error
            if skipped is not None:
                rows[check_id] = {
                    "name": check_id,
                    "passed": True,
                    "status": "skipped",
                    "notes": skipped.get("message") or "skipped",
                }
            elif problem is not None:
                rows[check_id] = {
                    "name": check_id,
                    "passed": False,
                    "notes": problem.get("message") or "failed",
                }
            else:
                rows[check_id] = {"name": check_id, "passed": True}
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checks", type=Path, required=True)
    parser.add_argument("--reward", type=Path, required=True)
    parser.add_argument("--gates", type=Path)
    parser.add_argument("--junit", type=Path, action="append", default=[])
    parser.add_argument("--profile", default="pb1")
    args = parser.parse_args()

    results: dict[str, dict[str, object]] = {}
    for junit in args.junit:
        results.update(_junit_rows(junit))
    if args.gates and args.gates.is_file():
        for check_id, row in json.loads(args.gates.read_text()).items():
            out = {"name": check_id, "passed": bool(row.get("passed"))}
            if row.get("status"):
                out["status"] = row["status"]
            if row.get("notes"):
                out["notes"] = row["notes"]
            results[check_id] = out

    checks: list[dict[str, object]] = []
    for spec in CHECKS:
        if not spec.implemented:
            if args.profile == "gold" or spec.skip_on_gold:
                continue
            continue
        if spec.id in results:
            checks.append(results[spec.id])
            continue
        if spec.skip_on_gold and args.profile == "gold":
            checks.append(
                {
                    "name": spec.id,
                    "passed": True,
                    "status": "skipped",
                    "notes": "gold skips workflow",
                }
            )
            continue
        checks.append(
            {
                "name": spec.id,
                "passed": False,
                "notes": "not run",
            }
        )
    write_results(args.checks, args.reward, checks)


if __name__ == "__main__":
    main()
