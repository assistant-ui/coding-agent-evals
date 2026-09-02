"""WF-D / WF-S over ToolCallRecord[]. Skip on gold (test.sh)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from checks import mcp_enabled, skills_enabled
from lib.transcript import (
    KNOWN_AGENTS,
    ToolCallRecord,
    adapt_transcript,
    agent_name_from_atif,
    parse_trajectory,
)

TRAJECTORY_PATH = Path(os.environ.get("TRAJECTORY_PATH", "/logs/agent/trajectory.json"))

ALLOWED_EXAMPLES = frozenset(
    {
        "waterfall",
        "with-a2a",
        "with-ag-ui",
        "with-ai-sdk-v7",
        "with-artifacts",
        "with-assistant-transport",
        "with-browser-extension",
        "with-chain-of-thought",
        "with-cloud",
        "with-cloud-standalone",
        "with-custom-thread-list",
        "with-elevenlabs-conversational",
        "with-elevenlabs-scribe",
        "with-eve",
        "with-expo",
        "with-external-store",
        "with-ffmpeg",
        "with-generative-ui",
        "with-google-adk",
        "with-heat-graph",
        "with-image-generation",
        "with-interactables",
        "with-langchain",
        "with-langgraph",
        "with-livekit",
        "with-mcp",
        "with-opencode",
        "with-pi",
        "with-react-hook-form",
        "with-react-ink",
        "with-react-ink-web",
        "with-react-router",
        "with-resumable-stream",
        "with-store",
        "with-tanstack",
        "with-tap-runtime",
        "with-virtualized-thread",
        "with-openui",
    }
)
ALLOWED_TEMPLATES = frozenset(
    {
        "cloud",
        "cloud-clerk",
        "default",
        "eve",
        "langchain",
        "mcp",
        "minimal",
    }
)

DOC_MCP_NAMES = frozenset(
    {
        "assistantUIExamples",
        "assistantUISearch",
        "assistantUITemplates",
        "assistantUIDocs",
    }
)

CREATE_RE = re.compile(
    r"(?:^|[\s;|&])(?:npx(?:\s+--yes)?\s+)?"
    r"(?:assistant-ui(?:@\S+)?\s+create\b|create-assistant-ui(?:@\S+)?\b)",
    re.I,
)
BUILD_RE = re.compile(
    r"(?:npx(?:\s+--yes)?\s+)?(?:tsc\b|next\s+build\b|(?:npm|pnpm|yarn|bun)(?:\s+run)?\s+build\b)",
    re.I,
)
HELP_FLAG_RE = re.compile(r"(?:^|\s)(?:--help|-h)(?=\s|$)")
EXAMPLE_RE = re.compile(r"(?:--example|-e)(?:=|\s+)([A-Za-z0-9_-]+)")
TEMPLATE_RE = re.compile(r"(?:--template|-t)(?:=|\s+)([A-Za-z0-9_-]+)")
# Official docs index or markdown/HTML docs pages (Codex web__run output
# cites https://www.assistant-ui.com/docs/... and llms.txt).
WEB_DOCS_RE = re.compile(
    r"llms\.txt|assistant-ui\.com[^\s\"']*/docs/|assistant-ui\.com[^\s\"']*\.md(?:x)?(?:[?#\s\"']|$)",
    re.I,
)
DOCS_CURL_RE = re.compile(
    r"\b(?:curl|wget)\b[\s\S]{0,300}(?:llms\.txt|assistant-ui\.com[^\s\"']*/docs/)",
    re.I,
)

# Harbor copies skills to each agent's native dir (and /harbor/skills).
SKILL_DIR_RE = re.compile(
    r"(?:^|/)(?:\.cursor/skills|\.claude/skills|\.agents/skills|harbor/skills)/",
    re.I,
)
SKILL_FILE_RE = re.compile(
    r"(?:^|/)(?:\.cursor/skills|\.claude/skills|\.agents/skills|harbor/skills)/"
    r"[^/\s\"']+/(?:SKILL\.md|references/)",
    re.I,
)


def used_assistant_ui_mcp(records: list[ToolCallRecord]) -> bool:
    for record in records:
        if record.name != "tool_use":
            continue
        server = (record.server or "").lower().replace("_", "-")
        original = record.original_name or ""
        if server == "assistant-ui":
            return True
        if original.startswith("assistantUI") or original == "getMcpToolsToolCall":
            return True
    return False


def is_doc_read(record: ToolCallRecord) -> bool:
    if record.name != "tool_use":
        return False
    original = record.original_name or ""
    return original in DOC_MCP_NAMES or (
        original.startswith("assistantUI") and original != "getMcpToolsToolCall"
    )


def _record_blob(record: ToolCallRecord) -> str:
    parts = [record.url or "", record.command or "", record.output or ""]
    if record.input:
        try:
            parts.append(json.dumps(record.input, default=str))
        except TypeError:
            parts.append(str(record.input))
    return "\n".join(parts)


def is_web_docs_target(record: ToolCallRecord) -> bool:
    return bool(WEB_DOCS_RE.search(_record_blob(record)))


def used_web_docs(records: list[ToolCallRecord]) -> bool:
    """MCP-off D-01: called the web tool against assistant-ui docs."""
    for record in records:
        if record.name in {"web_search", "web_fetch"} and is_web_docs_target(record):
            return True
        if record.name == "shell" and record.command and DOCS_CURL_RE.search(record.command):
            return True
    return False


def is_web_doc_read(record: ToolCallRecord) -> bool:
    """Fetch/open/curl of llms.txt or markdown docs pages — not search hits."""
    if record.name == "web_fetch" and is_web_docs_target(record):
        return True
    return bool(
        record.name == "shell"
        and record.command
        and DOCS_CURL_RE.search(record.command)
    )


def _skill_blob(record: ToolCallRecord) -> str:
    parts = [record.path or "", record.command or ""]
    skill = record.input.get("skill") if record.input else None
    if skill:
        parts.append(str(skill))
    return "\n".join(parts)


def is_skill_read(record: ToolCallRecord) -> bool:
    """Read an injected assistant-ui skill (SKILL.md, reference, or Skill tool)."""
    if record.name == "skill_use" or (record.original_name or "") == "Skill":
        return bool(str((record.input or {}).get("skill") or "").strip())
    if record.name == "file_read" and record.path and SKILL_DIR_RE.search(record.path):
        return True
    if record.name == "shell" and record.command and SKILL_FILE_RE.search(record.command):
        return True
    return bool(SKILL_FILE_RE.search(_skill_blob(record)))


def used_assistant_ui_skill(records: list[ToolCallRecord]) -> bool:
    return any(is_skill_read(record) for record in records)


def skills_or_web_docs_before_scaffold_or_write(records: list[ToolCallRecord]) -> bool:
    return _docs_before_change(
        records, lambda rec: is_skill_read(rec) or is_web_doc_read(rec)
    )


def is_workspace_write(record: ToolCallRecord) -> bool:
    if record.name not in {"file_write", "file_edit"}:
        return False
    path = record.path or ""
    return (not path) or path.startswith("/workspace") or "workspace" in path


def is_scaffold_create(command: str | None) -> bool:
    if not command or not CREATE_RE.search(command):
        return False
    return HELP_FLAG_RE.search(command) is None


def create_commands(records: list[ToolCallRecord]) -> list[ToolCallRecord]:
    return [
        record
        for record in records
        if record.name == "shell" and is_scaffold_create(record.command)
    ]


def create_attempted(records: list[ToolCallRecord]) -> bool:
    return bool(create_commands(records))


def is_build_command(command: str | None) -> bool:
    return bool(command) and BUILD_RE.search(command) is not None


def build_attempted(records: list[ToolCallRecord]) -> bool:
    return any(
        record.name == "shell" and is_build_command(record.command)
        for record in records
    )


def error_judge_skips(records: list[ToolCallRecord]) -> dict[str, str]:
    """WF-E-* are N/A unless the agent actually ran the relevant command."""
    skips: dict[str, str] = {}
    if not create_attempted(records):
        skips["WF-E-01"] = "no assistant-ui create command in the transcript"
    if not build_attempted(records):
        skips["WF-E-02"] = "no TypeScript or package build command in the transcript"
    return skips


def successful_creates(records: list[ToolCallRecord]) -> list[ToolCallRecord]:
    return [record for record in create_commands(records) if record.exit_code == 0]


def successful_create(records: list[ToolCallRecord]) -> ToolCallRecord | None:
    found = successful_creates(records)
    return found[0] if found else None


def listed_example_create(records: list[ToolCallRecord]) -> ToolCallRecord | None:
    for record in successful_creates(records):
        command = record.command or ""
        example = example_id_from_command(command)
        if example is not None and example in ALLOWED_EXAMPLES:
            return record
        template = template_id_from_command(command)
        if template is not None and template in ALLOWED_TEMPLATES:
            return record
    return None


def docs_before_scaffold_or_write(records: list[ToolCallRecord]) -> bool:
    return _docs_before_change(records, is_doc_read)


def web_docs_before_scaffold_or_write(records: list[ToolCallRecord]) -> bool:
    return _docs_before_change(records, is_web_doc_read)


def _docs_before_change(
    records: list[ToolCallRecord],
    is_read,
) -> bool:
    first_doc: int | None = None
    first_change: int | None = None
    for record in records:
        if first_doc is None and is_read(record):
            first_doc = record.seq
        is_create = record.name == "shell" and is_scaffold_create(record.command)
        if first_change is None and (is_create or is_workspace_write(record)):
            first_change = record.seq
    if first_change is None:
        return True
    return first_doc is not None and first_doc < first_change


def example_id_from_command(command: str) -> str | None:
    match = EXAMPLE_RE.search(command)
    return match.group(1) if match else None


def template_id_from_command(command: str) -> str | None:
    match = TEMPLATE_RE.search(command)
    return match.group(1) if match else None


@pytest.fixture(scope="module")
def records() -> list[ToolCallRecord]:
    if not TRAJECTORY_PATH.is_file():
        pytest.fail(f"trajectory not found: {TRAJECTORY_PATH}")
    name = agent_name_from_atif(TRAJECTORY_PATH)
    if name and name not in KNOWN_AGENTS:
        pytest.skip(f"no adapter for {name}")
    return adapt_transcript(parse_trajectory(TRAJECTORY_PATH)).tool_calls


def test_wf_d_01_used_mcp(records: list[ToolCallRecord]) -> None:
    """WF-D-01 Used assistant-ui MCP, skills, or web docs (per surface)."""
    if mcp_enabled():
        assert used_assistant_ui_mcp(records)
        return
    if skills_enabled():
        assert used_assistant_ui_skill(records) or used_web_docs(records)
        return
    assert used_web_docs(records)


def test_wf_d_02_docs_before_write(records: list[ToolCallRecord]) -> None:
    """WF-D-02 Read docs / skills / examples before first scaffold or write."""
    if mcp_enabled():
        assert docs_before_scaffold_or_write(records)
        return
    if skills_enabled():
        assert skills_or_web_docs_before_scaffold_or_write(records)
        return
    assert web_docs_before_scaffold_or_write(records)


def test_wf_s_01_cli_create(records: list[ToolCallRecord]) -> None:
    """WF-S-01 Scaffolded with assistant-ui CLI create."""
    assert successful_create(records) is not None


def test_wf_s_02_listed_example(records: list[ToolCallRecord]) -> None:
    """WF-S-02 create used a listed --example or --template id."""
    if successful_create(records) is None:
        pytest.skip("skipped because WF-S-01 failed")
    assert listed_example_create(records) is not None
