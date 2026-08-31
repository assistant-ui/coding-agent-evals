#!/usr/bin/env python3
"""Generate a Harbor 0.20 job and run it. Do not hand-write YAML."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "catalog.yaml"


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text())


def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def check_harbor(expected: str) -> str:
    try:
        out = subprocess.check_output(["harbor", "--version"], text=True).strip()
    except FileNotFoundError:
        die("harbor is not on PATH. Run ./scripts/setup.sh")
    ver = out.split()[-1] if out else ""
    if not ver.startswith(expected):
        die(f"Harbor {ver or out!r} is not supported. Pin {expected}.")
    return ver


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [p.strip() for p in value.split(",") if p.strip()]


def yaml_quote(s: str) -> str:
    if s == "" or any(c in s for c in ":#{}[],&*?|>!%@`'\" \t"):
        return json.dumps(s)
    return s


def emit_job(
    *,
    catalog: dict,
    cases: list[dict],
    agents: list[dict] | None,
    oracle: bool,
    mcp: str | None,
    env_type: str,
    env_kwargs: dict[str, str],
    concurrent: int,
) -> str:
    lines: list[str] = [
        "jobs_dir: jobs",
        "n_attempts: 1",
        f"n_concurrent_trials: {concurrent}",
    ]
    if not oracle:
        lines.append("extra_instruction_paths:")
        lines.append("  - scripts/detach-dev-server.md")

    lines.append("environment:")
    lines.append(f"  type: {yaml_quote(env_type)}")
    lines.append("  force_build: false")
    lines.append("  delete: true")
    if mcp == "off":
        lines.append("  env:")
        lines.append('    PB1_MCP: "off"')
    if env_kwargs:
        lines.append("  kwargs:")
        for k, v in env_kwargs.items():
            lines.append(f"    {k}: {v if str(v).isdigit() else yaml_quote(str(v))}")

    lines.append("verifier:")
    lines.append("  include_logs:")
    lines.append('    - "*"')
    lines.append('    - "**/*"')
    if mcp == "off":
        lines.append("  env:")
        lines.append('    PB1_MCP: "off"')

    lines.append("agents:")
    if oracle:
        lines.append("  - name: oracle")
    else:
        assert agents is not None
        for agent in agents:
            lines.append(f"  - name: {yaml_quote(agent['id'])}")
            lines.append(f"    model_name: {yaml_quote(agent['model'])}")

    lines.append("tasks:")
    for case in cases:
        lines.append(f"  - path: tasks/{case['folder']}")
    return "\n".join(lines) + "\n"


def resolve_cases(catalog: dict, ids: list[str] | None) -> list[dict]:
    by_id = {c["id"]: c for c in catalog["cases"]}
    if not ids:
        return list(catalog["cases"])
    out = []
    for cid in ids:
        if cid not in by_id:
            die(f"unknown case {cid!r}. Known: {', '.join(by_id)}")
        out.append(by_id[cid])
    return out


def resolve_agents(catalog: dict, ids: list[str] | None) -> list[dict]:
    by_id = {a["id"]: a for a in catalog["agents"]}
    if not ids:
        return list(catalog["agents"])
    out = []
    for aid in ids:
        if aid not in by_id:
            die(f"unknown agent {aid!r}. Known: {', '.join(by_id)}")
        out.append(by_id[aid])
    return out


def env_kwargs_for(catalog: dict, env_type: str, extra: list[str]) -> dict[str, str]:
    kwargs: dict[str, str] = {}
    if env_type == "blaxel":
        bl = catalog.get("blaxel") or {}
        if "region" in bl:
            kwargs["region"] = str(bl["region"])
        if "deployment_timeout_sec" in bl:
            kwargs["deployment_timeout_sec"] = str(bl["deployment_timeout_sec"])
    for item in extra:
        if "=" not in item:
            die(f"--environment-kwarg needs KEY=VALUE, got {item!r}")
        k, v = item.split("=", 1)
        kwargs[k] = v
    return kwargs


def mcp_jobs(mcp_flag: str | None, command: str) -> list[str | None]:
    if command == "full-eval":
        return ["on", "off"]
    if mcp_flag in (None, "on"):
        return [None if command == "check-env-codeverifiers" else "on"]
    if mcp_flag == "off":
        return ["off"]
    if mcp_flag == "both":
        return ["on", "off"]
    die("--mcp must be on, off, or both")


def write_and_maybe_run(
    yaml_text: str,
    *,
    print_config: bool,
    dry_run: bool,
    root: Path,
) -> Path | None:
    run_dir = root / ".run"
    run_dir.mkdir(exist_ok=True)
    cfg = run_dir / "job.yaml"
    cfg.write_text(yaml_text)
    if print_config or dry_run:
        sys.stdout.write(yaml_text)
        return cfg
    env_file = root / ".env"
    cmd = ["harbor", "run", "--config", str(cfg), "-y"]
    if env_file.exists():
        cmd.extend(["--env-file", str(env_file)])
    print("+", " ".join(cmd), file=sys.stderr)
    subprocess.check_call(cmd, cwd=root)
    return cfg


def ingest_latest(root: Path) -> None:
    ingest = root / "scripts" / "ingest.py"
    subprocess.check_call(
        [
            sys.executable,
            str(ingest),
            "--jobs-dir",
            str(root / "jobs"),
            "--merge-existing",
        ],
        cwd=root,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Wrap Harbor 0.20 for coding-agent-evals.")
    p.add_argument(
        "command",
        choices=["check-env-codeverifiers", "full-eval", "custom"],
    )
    p.add_argument("--cases", help="Comma-separated case ids (g1,g2). Default: all.")
    p.add_argument("--agents", help="Comma-separated agent ids. Default: all (not for oracle).")
    p.add_argument("--mcp", choices=["on", "off", "both"], help="MCP surface. full-eval always both.")
    p.add_argument(
        "--env",
        dest="env_type",
        default=None,
        help="Harbor environment type (default: blaxel).",
    )
    p.add_argument(
        "--environment-kwarg",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Passed into environment.kwargs. Repeatable.",
    )
    p.add_argument("--concurrent", type=int, default=None)
    p.add_argument("--print-config", action="store_true", help="Print generated YAML and exit.")
    p.add_argument("--dry-run", action="store_true", help="Write YAML, do not call Harbor.")
    p.add_argument("--no-ingest", action="store_true")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    catalog = load_catalog()
    check_harbor(str(catalog["harbor_version"]))
    env_type = args.env_type or catalog["default_env"]
    concurrent = args.concurrent or int(catalog["n_concurrent_trials"])
    case_ids = parse_csv(args.cases)
    agent_ids = parse_csv(args.agents)
    cases = resolve_cases(catalog, case_ids or None)
    kwargs = env_kwargs_for(catalog, env_type, args.environment_kwarg)

    oracle = args.command == "check-env-codeverifiers"
    if args.command == "custom":
        if not case_ids or not agent_ids:
            die("custom requires --cases and --agents")
        agents = resolve_agents(catalog, agent_ids)
    elif oracle:
        agents = None
    else:
        agents = resolve_agents(catalog, agent_ids or None)

    for mcp in mcp_jobs(args.mcp, args.command):
        yaml_text = emit_job(
            catalog=catalog,
            cases=cases,
            agents=agents,
            oracle=oracle,
            mcp=mcp,
            env_type=env_type,
            env_kwargs=kwargs,
            concurrent=concurrent,
        )
        write_and_maybe_run(
            yaml_text,
            print_config=args.print_config,
            dry_run=args.dry_run,
            root=ROOT,
        )
        if args.print_config and mcp != mcp_jobs(args.mcp, args.command)[-1]:
            sys.stdout.write("---\n")

    if args.dry_run or args.no_ingest or args.print_config:
        return
    ingest_latest(ROOT)


if __name__ == "__main__":
    main()
