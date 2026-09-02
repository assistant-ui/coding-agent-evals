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


DEFAULT_SKILLS_SOURCE = (
    "https://github.com/assistant-ui/skills/tree/main/assistant-ui/skills"
)
SURFACES = ("none", "mcp", "skills")
SURFACE_ALIASES = {"on": "mcp", "off": "none", "skill": "skills"}
MODES = ("low", "high")


def env_for_surface(surface: str | None, mode: str | None) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if surface == "none":
        pairs.extend([("PB1_MCP", "off"), ("PB1_SURFACE", "none")])
    elif surface == "skills":
        pairs.extend([("PB1_MCP", "off"), ("PB1_SURFACE", "skills")])
    elif surface == "mcp":
        pairs.append(("PB1_SURFACE", "mcp"))
    if mode in MODES:
        pairs.append(("PB1_MODE", mode))
    return pairs


def emit_env_block(lines: list[str], pairs: list[tuple[str, str]]) -> None:
    if not pairs:
        return
    lines.append("  env:")
    for key, value in pairs:
        lines.append(f"    {key}: {json.dumps(value)}")


def emit_job(
    *,
    catalog: dict,
    cases: list[dict],
    agents: list[dict] | None,
    oracle: bool,
    surface: str | None,
    mode: str | None,
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

    env_pairs = env_for_surface(surface, mode)
    lines.append("environment:")
    lines.append(f"  type: {yaml_quote(env_type)}")
    lines.append("  force_build: false")
    lines.append("  delete: true")
    emit_env_block(lines, env_pairs)
    if env_kwargs:
        lines.append("  kwargs:")
        for k, v in env_kwargs.items():
            lines.append(f"    {k}: {v if str(v).isdigit() else yaml_quote(str(v))}")

    lines.append("verifier:")
    lines.append("  include_logs:")
    lines.append('    - "*"')
    lines.append('    - "**/*"')
    emit_env_block(lines, env_pairs)

    skills_source = str(catalog.get("skills_source") or DEFAULT_SKILLS_SOURCE)
    lines.append("agents:")
    if oracle:
        lines.append("  - name: oracle")
    else:
        assert agents is not None
        for agent in agents:
            lines.append(f"  - name: {yaml_quote(agent['id'])}")
            lines.append(f"    model_name: {yaml_quote(agent['model'])}")
            if surface == "skills":
                lines.append("    skills:")
                lines.append(f"      - {yaml_quote(skills_source)}")

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


def apply_mode(agents: list[dict], mode: str) -> list[dict]:
    if mode not in MODES:
        die(f"--mode must be low or high, got {mode!r}")
    out = []
    for agent in agents:
        spec = (agent.get("modes") or {}).get(mode) or {}
        model = spec.get("model") or agent.get("model")
        tier = spec.get("tier") or agent.get("tier")
        if not model:
            die(f"agent {agent.get('id')!r} has no model for mode {mode}")
        out.append({**agent, "model": model, "tier": tier, "mode": mode})
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


def parse_surfaces(value: str) -> list[str]:
    if value.strip().lower() == "all":
        return list(SURFACES)
    out: list[str] = []
    for raw in parse_csv(value):
        name = SURFACE_ALIASES.get(raw.lower(), raw.lower())
        if name not in SURFACES:
            die(f"unknown surface {raw!r}. Use none, mcp, skills, or all.")
        if name not in out:
            out.append(name)
    if not out:
        die("--surface needs none, mcp, skills, or all")
    return out


def surface_jobs(
    surface_flag: str | None,
    mcp_flag: str | None,
    command: str,
) -> list[str | None]:
    if command == "check-env-codeverifiers":
        return [None]
    if surface_flag:
        return parse_surfaces(surface_flag)
    if command == "full-eval":
        return list(SURFACES)
    if mcp_flag == "off":
        return ["none"]
    if mcp_flag == "both":
        return ["mcp", "none"]
    if mcp_flag in (None, "on"):
        return ["mcp"]
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
    if print_config or dry_run:
        sys.stdout.write(yaml_text)
        return cfg
    cfg.write_text(yaml_text)
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
    p.add_argument(
        "--surface",
        help="none, mcp, skills (csv) or all. full-eval defaults to all three.",
    )
    p.add_argument(
        "--mcp",
        choices=["on", "off", "both"],
        help="Alias: on=mcp, off=none, both=mcp+none. Ignored if --surface is set.",
    )
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
    p.add_argument(
        "--mode",
        choices=list(MODES),
        default=None,
        help="low = cheap models (Composer 2.5, Sonnet 5, Luna). high = Grok 4.6, Fable 5.1, Sol.",
    )
    p.add_argument(
        "--concurrent",
        type=int,
        default=None,
        help="Max Harbor trials in flight (sandbox concurrency). Default from catalog.",
    )
    p.add_argument("--print-config", action="store_true", help="Print generated YAML and exit.")
    p.add_argument("--dry-run", action="store_true", help="Write YAML, do not call Harbor.")
    p.add_argument("--no-ingest", action="store_true")
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    catalog = load_catalog()
    check_harbor(str(catalog["harbor_version"]))
    env_type = args.env_type or catalog["default_env"]
    concurrent = args.concurrent if args.concurrent is not None else int(catalog["n_concurrent_trials"])
    if concurrent < 1:
        die("--concurrent must be >= 1")
    mode = args.mode or str(catalog.get("default_mode") or "low")
    if mode not in MODES:
        die(f"--mode must be low or high, got {mode!r}")
    case_ids = parse_csv(args.cases)
    agent_ids = parse_csv(args.agents)
    cases = resolve_cases(catalog, case_ids or None)
    kwargs = env_kwargs_for(catalog, env_type, args.environment_kwarg)

    oracle = args.command == "check-env-codeverifiers"
    if args.command == "custom":
        if not case_ids or not agent_ids:
            die("custom requires --cases and --agents")
        agents = apply_mode(resolve_agents(catalog, agent_ids), mode)
    elif oracle:
        agents = None
    else:
        agents = apply_mode(resolve_agents(catalog, agent_ids or None), mode)

    jobs = surface_jobs(args.surface, args.mcp, args.command)
    for i, surface in enumerate(jobs):
        yaml_text = emit_job(
            catalog=catalog,
            cases=cases,
            agents=agents,
            oracle=oracle,
            surface=surface,
            mode=mode if not oracle else None,
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
        if args.print_config and i < len(jobs) - 1:
            sys.stdout.write("---\n")

    if args.dry_run or args.no_ingest or args.print_config:
        return
    ingest_latest(ROOT)


if __name__ == "__main__":
    main()
