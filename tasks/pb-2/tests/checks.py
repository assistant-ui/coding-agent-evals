"""Check catalog. Report.py maps pytest / gates onto these IDs."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

# Job YAML: set on both environment.env and verifier.env. Harbor does not
# copy sandbox env into the verifier. Default on (omit or any value except off).
MCP_ENV_KEY = "PB1_MCP"
_MCP_OFF = frozenset({"off", "0", "false", "no", "disabled"})

PYTEST_ID_RE = re.compile(
    r"^test_(?P<body>.+?)(?:\[.*\])?$",
)


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    group: str
    implemented: bool = True
    skip_on_gold: bool = False
    skip_on_mcp_off: bool = False


CHECKS: tuple[Check, ...] = (
    Check("CQ-G-01", "App package.json exists under /workspace", "code"),
    Check("CQ-G-02", "Depends on @assistant-ui/react", "code"),
    Check("CQ-G-03", "Depends on an assistant-ui AI SDK package and ai", "code"),
    Check("CQ-G-04", "Provider package present", "code"),
    Check("CQ-G-05", "AssistantRuntimeProvider in source", "code"),
    Check("CQ-G-06", "Thread in source", "code"),
    Check("CQ-P-01", "useChatRuntime in source", "code"),
    Check("CQ-P-02", "Chat route streams UI messages", "code"),
    Check("CQ-P-03", "Sandboxed iframe srcDoc preview", "code"),
    Check("CQ-P-04", "Artifact interactable tool is registered", "code"),
    Check("CQ-P-05", "OPENAI_API_KEY documented; no live secrets", "code"),
    Check("CQ-P-06", "Side canvas / preview surface in source", "code"),
    Check("AR-01", "Dependencies install", "apprun"),
    Check("AR-02", "npm run build", "apprun"),
    Check("AR-03", "Verifier starts Next and GET / succeeds", "apprun"),
    Check("AR-04", "POST /api/chat is a chat route", "apprun"),
    Check("BR-01", "Composer and canvas are visible", "browser"),
    Check("BR-02", "No critical pageerror on load", "browser"),
    Check("BR-03", "Type HTML-card prompt and send", "browser"),
    Check("BR-04", "User message appears in the thread", "browser"),
    Check("BR-05", "Canvas iframe renders the HTML card", "browser"),
    Check("BR-06", "Follow-up updates the canvas iframe content", "browser"),
    Check(
        "WF-D-01",
        "Used assistant-ui MCP or web docs (per PB1_MCP)",
        "workflow",
        True,
        True,
    ),
    Check(
        "WF-D-02",
        "Docs before first scaffold or write",
        "workflow",
        True,
        True,
    ),
    Check("WF-S-01", "Scaffolded with assistant-ui CLI create", "workflow", True, True),
    Check("WF-S-02", "create used a listed --example id", "workflow", True, True),
    Check("WF-E-01", "Did not face assistant-ui create CLI errors", "workflow", True, True),
    Check("WF-E-02", "Did not face TypeScript/build errors in the agent run", "workflow", True, True),
    Check("WF-T-01", "Agent started the app", "workflow", True, True),
    Check("WF-T-02", "Agent tested the running app", "workflow", True, True),
)

BY_ID = {check.id: check for check in CHECKS}


def mcp_enabled() -> bool:
    """True unless PB1_MCP is an explicit off value (default on)."""
    raw = os.environ.get(MCP_ENV_KEY, "on").strip().lower()
    if not raw:
        return True
    return raw not in _MCP_OFF


# WF-E-* skip on missing create/build attempt in judge/run.py, not on no app.
_CQ_G_01_KEEP = frozenset({"CQ-G-01", "WF-E-01", "WF-E-02"})

SKIP_AFTER_FAIL: dict[str, tuple[str, ...]] = {
    "CQ-G-01": tuple(
        check.id
        for check in CHECKS
        if check.id not in _CQ_G_01_KEEP and check.implemented
    ),
    "AR-01": ("AR-02", "AR-03", "AR-04", "BR-01", "BR-02", "BR-03", "BR-04", "BR-05", "BR-06"),
    "AR-02": ("AR-03", "AR-04", "BR-01", "BR-02", "BR-03", "BR-04", "BR-05", "BR-06"),
    "AR-03": ("AR-04", "BR-01", "BR-02", "BR-03", "BR-04", "BR-05", "BR-06"),
    "BR-01": ("BR-03", "BR-04", "BR-05", "BR-06"),
    "BR-03": ("BR-04", "BR-05", "BR-06"),
    "BR-04": ("BR-05", "BR-06"),
    "WF-S-01": ("WF-S-02",),
}


def id_from_pytest_name(name: str) -> str | None:
    match = PYTEST_ID_RE.match(name)
    if match is None:
        return None
    parts = match.group("body").split("_")
    if len(parts) >= 3 and parts[0] in {"wf", "cq"}:
        candidate = f"{parts[0].upper()}-{parts[1].upper()}-{parts[2]}"
        return candidate if candidate in BY_ID else None
    if len(parts) >= 2 and parts[0] in {"ar", "br"}:
        candidate = f"{parts[0].upper()}-{parts[1]}"
        return candidate if candidate in BY_ID else None
    return None


def set_gate(path: Path, check_id: str, passed: bool, notes: str = "") -> None:
    data: dict[str, dict[str, object]] = {}
    if path.is_file():
        data = json.loads(path.read_text())
    row: dict[str, object] = {"passed": passed, "status": "passed" if passed else "failed"}
    if notes:
        row["notes"] = notes
    data[check_id] = row
    if not passed:
        for dependent in SKIP_AFTER_FAIL.get(check_id, ()):
            if dependent not in data:
                data[dependent] = {
                    "passed": True,
                    "status": "skipped",
                    "notes": f"skipped because {check_id} failed",
                }
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    import sys

    if len(sys.argv) >= 4 and sys.argv[1] == "--set-gate":
        path = Path(sys.argv[2])
        check_id = sys.argv[3]
        passed = sys.argv[4] == "pass"
        notes = sys.argv[5] if len(sys.argv) > 5 else ""
        set_gate(path, check_id, passed, notes)
        return
    raise SystemExit("usage: checks.py --set-gate FILE ID pass|fail [notes]")


if __name__ == "__main__":
    main()
