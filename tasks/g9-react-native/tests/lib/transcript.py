"""Cursor ATIF → supabase-named events → tool records + compact transcript."""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAX_KEEP_CHARS = 2000
HEAD_CHARS = 1000
TAIL_CHARS = 1000
MAX_TRANSCRIPT_TOKENS = 70_000
CHARS_PER_TOKEN = 4

TOOL_KEY_MAP: dict[str, str] = {
    "readToolCall": "file_read",
    "writeToolCall": "file_write",
    "editToolCall": "file_edit",
    "applyPatchToolCall": "file_edit",
    "shellToolCall": "shell",
    "bashToolCall": "shell",
    "webFetchToolCall": "web_fetch",
    "webSearchToolCall": "web_search",
    "globToolCall": "glob",
    "grepToolCall": "grep",
    "listDirToolCall": "list_dir",
    "lsToolCall": "list_dir",
    "taskToolCall": "agent_task",
    "mcpToolCall": "tool_use",
    "getMcpToolsToolCall": "tool_use",
    # Claude Code Harbor ATIF
    "Read": "file_read",
    "Write": "file_write",
    "Edit": "file_edit",
    "MultiEdit": "file_edit",
    "NotebookEdit": "file_edit",
    "Bash": "shell",
    "BashOutput": "shell",
    "KillShell": "shell",
    "WebFetch": "web_fetch",
    "WebSearch": "web_search",
    "Glob": "glob",
    "Grep": "grep",
    "LS": "list_dir",
    "Task": "agent_task",
    "TodoWrite": "agent_task",
    # Codex Harbor ATIF
    "exec": "shell",
    "command_execution": "shell",
    "exec_command": "shell",
    "local_shell_call": "shell",
    "file_change": "file_write",
    "apply_patch": "file_write",
    "web_search": "web_search",
    "mcp_tool_call": "tool_use",
}

KNOWN_AGENTS = frozenset({"cursor-cli", "claude-code", "codex"})
CLAUDE_MCP_RE = re.compile(
    r"^mcp__(?P<server>[A-Za-z0-9_-]+)__(?P<tool>[A-Za-z0-9_-]+)$"
)
CODEX_MCP_RE = re.compile(
    r"tools\.mcp__(?P<server>[A-Za-z0-9_-]+)__(?P<tool>[A-Za-z0-9_-]+)\s*\("
)
CODEX_WEB_RE = re.compile(r"tools\.web__run\s*\(")
HTTP_URL_RE = re.compile(r"https?://[^\s\"'<>\\]+")
# Harbor unified_exec wraps the real shell in tools.exec_command({cmd:"..."}).
CODEX_EXEC_CMD_RE = re.compile(
    r"""tools\.exec_command\(\s*\{[\s\S]*?\bcmd\s*:\s*(?:"""
    r""""((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)')""",
    re.I,
)
CODEX_WRITE_STDIN_SESSION_RE = re.compile(
    r"tools\.write_stdin\(\s*\{[\s\S]*?\bsession_id\s*:\s*(?P<sid>\d+)",
    re.I,
)
CODEX_SESSION_ID_RE = re.compile(r'"session_id"\s*:\s*(?P<sid>\d+)')
CODEX_EXIT_CODE_RE = re.compile(r'"exit_code"\s*:\s*(?P<code>-?\d+)')
SHELL_FUNCTIONS = frozenset(
    {
        "shellToolCall",
        "bashToolCall",
        "Bash",
        "exec",
        "command_execution",
        "exec_command",
        "local_shell_call",
    }
)

DROP_ARG_KEYS = frozenset(
    {
        "toolCallId",
        "hookAdditionalContexts",
        "startedAtMs",
        "completedAtMs",
        "smartModeApprovalOnly",
        "skipApproval",
    }
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]+|bearer\s+\S+|OPENAI_API_KEY\s*=\s*\S+)",
    re.I,
)
LEADING_CD_RE = re.compile(r"^cd\s+\S+\s+&&\s+")
SPILLED_MARKER = "[outputLocation present; not loaded]"


@dataclass
class TranscriptEvent:
    id: str
    kind: str
    role: str | None = None
    text: str | None = None
    tool_name: str | None = None
    original_name: str | None = None
    call_id: str | None = None
    input: dict[str, Any] = field(default_factory=dict)
    command: str | None = None
    path: str | None = None
    url: str | None = None
    server: str | None = None
    success: bool | None = None
    exit_code: int | None = None
    output: str | None = None


@dataclass
class ToolCallRecord:
    seq: int
    event_id: str
    name: str
    original_name: str
    call_id: str
    input: dict[str, Any] = field(default_factory=dict)
    command: str | None = None
    path: str | None = None
    url: str | None = None
    server: str | None = None
    success: bool | None = None
    exit_code: int | None = None
    output: str | None = None
    result_event_id: str | None = None


@dataclass
class TranscriptPart:
    id: str
    kind: str
    role: str | None = None
    text: str | None = None
    tool_name: str | None = None
    original_name: str | None = None
    command: str | None = None
    path: str | None = None
    url: str | None = None
    input: dict[str, Any] = field(default_factory=dict)
    success: bool | None = None
    exit_code: int | None = None
    output: str | None = None
    total_truncated: bool = False


@dataclass
class AdaptedTranscript:
    parts: list[TranscriptPart]
    tool_calls: list[ToolCallRecord]


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN) if text else 0


def strip_controls(text: str) -> str:
    return CONTROL_RE.sub("", ANSI_RE.sub("", text))


def redact_secrets(text: str) -> str:
    return SECRET_RE.sub("[REDACTED]", text)


def normalize_shell_command(command: str) -> str:
    text = command.strip()
    match = LEADING_CD_RE.match(text)
    if match:
        text = text[match.end() :]
    if text.endswith(" 2>&1"):
        text = text[:-5].rstrip()
    return text


def truncate_text(text: str, head: int = HEAD_CHARS, tail: int = TAIL_CHARS) -> str:
    if len(text) <= MAX_KEEP_CHARS:
        return text
    omitted = len(text) - head - tail
    return f"{text[:head]}\n\n... {omitted} characters omitted ...\n\n{text[-tail:]}"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_args(args: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in args.items():
        if key in DROP_ARG_KEYS:
            continue
        if key == "outputLocation":
            continue
        cleaned[key] = value
    return cleaned


def _mcp_from_function_name(function_name: str) -> tuple[str, str] | None:
    match = CLAUDE_MCP_RE.match(function_name)
    if not match:
        return None
    return match.group("server"), match.group("tool")


def _map_tool(function_name: str, args: dict[str, Any]) -> tuple[str, str, str | None]:
    mcp = _mcp_from_function_name(function_name)
    if mcp:
        server, tool = mcp
        return "tool_use", tool, server
    name = TOOL_KEY_MAP.get(function_name, "unknown")
    if function_name == "mcpToolCall":
        original = str(args.get("toolName") or args.get("name") or function_name)
        server = str(
            args.get("serverIdentifier") or args.get("providerIdentifier") or ""
        )
        return name, original, server or None
    if function_name == "getMcpToolsToolCall":
        server = str(args.get("server") or args.get("serverIdentifier") or "")
        return name, "getMcpToolsToolCall", server or None
    if function_name == "mcp_tool_call":
        original = str(args.get("tool") or args.get("name") or function_name)
        server = str(args.get("server") or args.get("serverIdentifier") or "")
        return name, original, server or None
    return name, function_name, None


def _path_from_args(args: dict[str, Any]) -> str | None:
    for key in ("path", "file_path", "targetDirectory"):
        value = args.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _url_from_text(text: str) -> str | None:
    match = HTTP_URL_RE.search(text)
    if match is None:
        return None
    return match.group(0).rstrip(").,];")


def _url_from_args(args: dict[str, Any]) -> str | None:
    for key in ("url", "uri", "href"):
        value = args.get(key)
        if isinstance(value, str) and value:
            return value
    raw = args.get("input")
    if isinstance(raw, str):
        return _url_from_text(raw)
    return None


def _codex_web_kind(raw: str) -> str | None:
    """Harbor Codex wraps search/open in exec JS: tools.web__run({...})."""
    if not CODEX_WEB_RE.search(raw):
        return None
    if re.search(r"\b(?:open|url)\s*:", raw):
        return "web_fetch"
    return "web_search"


def _unescape_js_string(body: str, quote: str) -> str:
    if quote == '"':
        try:
            parsed = json.loads(f'"{body}"')
        except json.JSONDecodeError:
            return body.replace(r"\"", '"').replace(r"\\", "\\")
        return parsed if isinstance(parsed, str) else body
    return (
        body.replace(r"\'", "'")
        .replace(r"\n", "\n")
        .replace(r"\t", "\t")
        .replace(r"\\", "\\")
    )


def _codex_exec_cmd(raw: str) -> str | None:
    match = CODEX_EXEC_CMD_RE.search(raw)
    if match is None:
        return None
    if match.group(1) is not None:
        return _unescape_js_string(match.group(1), '"')
    return _unescape_js_string(match.group(2), "'")


def _command_from_args(function_name: str, args: dict[str, Any]) -> str | None:
    if function_name not in SHELL_FUNCTIONS:
        return None
    raw = args.get("command")
    if not isinstance(raw, str):
        raw = args.get("input")
    if not isinstance(raw, str):
        return None
    if function_name == "exec":
        cmd = _codex_exec_cmd(raw)
        if cmd is not None:
            return normalize_shell_command(cmd)
        # web__run / write_stdin / apply_patch JS is not a shell command.
        if "tools." in raw:
            return None
        return normalize_shell_command(raw)
    return normalize_shell_command(raw)


def _tool_emissions(
    function_name: str, args: dict[str, Any]
) -> list[dict[str, Any]]:
    tool_name, original_name, server = _map_tool(function_name, args)
    emissions: list[dict[str, Any]] = [
        {
            "tool_name": tool_name,
            "original_name": original_name,
            "server": server,
            "command": _command_from_args(function_name, args),
            "input": _clean_args(args),
        }
    ]
    if function_name != "exec":
        return emissions
    raw = args.get("input")
    if not isinstance(raw, str):
        return emissions
    web_kind = _codex_web_kind(raw)
    if web_kind is not None:
        emissions[0] = {
            "tool_name": web_kind,
            "original_name": "web__run",
            "server": None,
            "command": None,
            "input": {"input": raw},
            "url": _url_from_text(raw),
        }
        return emissions
    for match in CODEX_MCP_RE.finditer(raw):
        emissions.append(
            {
                "tool_name": "tool_use",
                "original_name": match.group("tool"),
                "server": match.group("server"),
                "command": None,
                "input": {"mcp_call": match.group(0)},
            }
        )
    return emissions


def _flatten_mcp_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return json.dumps(content) if content is not None else ""
    chunks: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            chunks.append(str(item))
            continue
        text = item.get("text")
        if isinstance(text, dict) and isinstance(text.get("text"), str):
            chunks.append(text["text"])
        elif isinstance(text, str):
            chunks.append(text)
        else:
            chunks.append(json.dumps(item))
    return "\n".join(chunks)


def _extract_body_output(body: dict[str, Any]) -> str:
    if body.get("outputLocation") and not body.get("stdout") and not body.get(
        "interleavedOutput"
    ):
        return SPILLED_MARKER
    if body.get("interleavedOutput"):
        return str(body["interleavedOutput"])
    chunks: list[str] = []
    if body.get("stdout"):
        chunks.append(str(body["stdout"]))
    if body.get("stderr"):
        chunks.append(str(body["stderr"]))
    if not chunks and "content" in body:
        chunks.append(_flatten_mcp_content(body["content"]))
    if not chunks and body.get("diffString"):
        chunks.append(str(body["diffString"]))
    return "\n".join(chunks)


def _decode_tool_content(content: Any) -> Any:
    if not isinstance(content, str):
        return content
    stripped = content.strip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return content
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    try:
        return ast.literal_eval(stripped)
    except (ValueError, SyntaxError, MemoryError):
        return content


def _codex_input_texts(obj: Any) -> list[str] | None:
    if not isinstance(obj, list) or not obj:
        return None
    texts: list[str] = []
    for item in obj:
        if not isinstance(item, dict):
            return None
        text = item.get("text")
        if not isinstance(text, str):
            return None
        texts.append(text)
    return texts


def _exit_code_from_text(text: str) -> int | None:
    code: int | None = None
    for match in CODEX_EXIT_CODE_RE.finditer(text):
        code = int(match.group("code"))
    return code


def _session_id_from_text(text: str | None) -> int | None:
    if not text:
        return None
    match = CODEX_SESSION_ID_RE.search(text)
    if match is not None:
        return int(match.group("sid"))
    match = CODEX_WRITE_STDIN_SESSION_RE.search(text)
    if match is not None:
        return int(match.group("sid"))
    return None


def parse_tool_content(content: Any) -> tuple[bool | None, int | None, str]:
    if content is None:
        return None, None, ""
    obj: Any = _decode_tool_content(content)
    texts = _codex_input_texts(obj)
    if texts is not None:
        joined = "".join(texts)
        exit_code = _exit_code_from_text(joined)
        cleaned = strip_controls(joined)
        if exit_code is None:
            return None, None, cleaned
        return exit_code == 0, exit_code, cleaned
    if isinstance(content, str) and obj is content:
        return True, None, strip_controls(content)
    if not isinstance(obj, dict):
        return True, None, strip_controls(str(obj))
    if obj.get("outputLocation") and "success" not in obj and "failure" not in obj:
        return None, None, SPILLED_MARKER
    if "failure" in obj:
        body = _as_dict(obj.get("failure"))
        exit_code = body.get("exitCode")
        return False, int(exit_code) if isinstance(exit_code, int) else None, strip_controls(
            _extract_body_output(body)
        )
    if "success" in obj:
        body = _as_dict(obj.get("success"))
        exit_code = body.get("exitCode")
        parsed_exit = int(exit_code) if isinstance(exit_code, int) else None
        success = parsed_exit in (None, 0)
        return success, parsed_exit, strip_controls(_extract_body_output(body))
    if obj.get("isError") is True:
        return False, None, strip_controls(_extract_body_output(obj) or json.dumps(obj))
    return True, None, strip_controls(_extract_body_output(obj) or json.dumps(obj))


def _apply_claude_shell_exit(
    result: dict[str, Any],
    success: bool | None,
    exit_code: int | None,
) -> tuple[bool | None, int | None]:
    """Harbor Claude Bash stores is_error in result.extra, not exitCode."""
    if exit_code is not None:
        return success, exit_code
    extra = _as_dict(result.get("extra"))
    meta = _as_dict(extra.get("tool_result_metadata"))
    raw = _as_dict(meta.get("raw_tool_result"))
    use = _as_dict(meta.get("tool_use_result"))
    is_error = extra.get("tool_result_is_error")
    if is_error is None:
        is_error = raw.get("is_error")
    if use.get("interrupted") is True or is_error is True:
        return False, 1
    if is_error is False:
        return True, 0
    return success, exit_code


def _load_atif(source: Path | str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(source, dict):
        return source
    path = Path(source)
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("ATIF root must be an object")
    return data


def parse_atif(source: Path | str | dict[str, Any]) -> list[TranscriptEvent]:
    data = _load_atif(source)
    events: list[TranscriptEvent] = []
    next_id = 1

    def take_id() -> str:
        nonlocal next_id
        event_id = f"evt-{next_id}"
        next_id += 1
        return event_id

    for step in data.get("steps") or []:
        if not isinstance(step, dict):
            continue
        source_role = str(step.get("source") or "")
        message = step.get("message")
        if isinstance(message, str) and message.strip():
            if source_role == "thinking":
                events.append(
                    TranscriptEvent(id=take_id(), kind="thinking", text=message)
                )
            elif source_role == "user":
                events.append(
                    TranscriptEvent(
                        id=take_id(), kind="message", role="user", text=message
                    )
                )
            else:
                events.append(
                    TranscriptEvent(
                        id=take_id(),
                        kind="message",
                        role="assistant",
                        text=message,
                    )
                )
        results_by_id: dict[str, dict[str, Any]] = {}
        observation = _as_dict(step.get("observation"))
        for result in observation.get("results") or []:
            if not isinstance(result, dict):
                continue
            call_id = result.get("source_call_id")
            if isinstance(call_id, str):
                results_by_id[call_id] = result
        for tool_call in step.get("tool_calls") or []:
            if not isinstance(tool_call, dict):
                continue
            args = _as_dict(tool_call.get("arguments"))
            function_name = str(tool_call.get("function_name") or "unknown")
            call_id = str(tool_call.get("tool_call_id") or take_id())
            result = results_by_id.get(call_id) or {}
            success, exit_code, output = parse_tool_content(result.get("content"))
            success, exit_code = _apply_claude_shell_exit(result, success, exit_code)
            for index, emission in enumerate(_tool_emissions(function_name, args)):
                emit_id = call_id if index == 0 else f"{call_id}:mcp:{index}"
                events.append(
                    TranscriptEvent(
                        id=take_id(),
                        kind="tool_call",
                        tool_name=str(emission["tool_name"]),
                        original_name=str(emission["original_name"]),
                        call_id=emit_id,
                        input=_as_dict(emission.get("input")),
                        command=emission.get("command")
                        if isinstance(emission.get("command"), str)
                        else None,
                        path=_path_from_args(args),
                        url=(
                            emission.get("url")
                            if isinstance(emission.get("url"), str)
                            else _url_from_args(args)
                        ),
                        server=emission.get("server")
                        if isinstance(emission.get("server"), str)
                        else None,
                    )
                )
                events.append(
                    TranscriptEvent(
                        id=take_id(),
                        kind="tool_result",
                        tool_name=str(emission["tool_name"]),
                        original_name=str(emission["original_name"]),
                        call_id=emit_id,
                        success=success,
                        exit_code=exit_code,
                        output=output,
                    )
                )
    _apply_codex_session_exits(events)
    return events


def _apply_codex_session_exits(events: list[TranscriptEvent]) -> None:
    """TTY exec_command yields a session_id with no exit; later write_stdin has it."""
    pending: dict[int, TranscriptEvent] = {}
    calls: dict[str, TranscriptEvent] = {}
    for event in events:
        if event.kind == "tool_call" and event.call_id:
            calls[event.call_id] = event
            continue
        if event.kind != "tool_result":
            continue
        call = calls.get(event.call_id or "")
        blob = ""
        if call is not None and isinstance(call.input.get("input"), str):
            blob = str(call.input["input"])
        if "tools.exec_command(" in blob and event.exit_code is None:
            session_id = _session_id_from_text(event.output)
            if session_id is not None:
                pending[session_id] = event
            continue
        stdin_session = _session_id_from_text(blob)
        if stdin_session is None or event.exit_code is None:
            continue
        starter = pending.get(stdin_session)
        if starter is None:
            continue
        starter.exit_code = event.exit_code
        starter.success = event.exit_code == 0
        extra = event.output or ""
        if extra:
            starter.output = ((starter.output or "") + "\n" + extra).strip()
        pending.pop(stdin_session, None)


def agent_name_from_atif(source: Path | str | dict[str, Any]) -> str:
    data = _load_atif(source)
    agent = data.get("agent") if isinstance(data.get("agent"), dict) else {}
    return str(agent.get("name") or "")


def parse_claude(source: Path | str | dict[str, Any]) -> list[TranscriptEvent]:
    return parse_atif(source)


def parse_codex(source: Path | str | dict[str, Any]) -> list[TranscriptEvent]:
    return parse_atif(source)


def parse_trajectory(source: Path | str | dict[str, Any]) -> list[TranscriptEvent]:
    data = _load_atif(source)
    name = agent_name_from_atif(data)
    if name == "claude-code":
        return parse_claude(data)
    if name == "codex":
        return parse_codex(data)
    return parse_atif(data)


def adapt_transcript(events: list[TranscriptEvent]) -> AdaptedTranscript:
    parts: list[TranscriptPart] = []
    records: list[ToolCallRecord] = []
    pending: dict[str, ToolCallRecord] = {}
    seq = 0
    for event in events:
        if event.kind == "thinking":
            continue
        if event.kind == "message":
            parts.append(
                TranscriptPart(
                    id=event.id, kind="message", role=event.role, text=event.text or ""
                )
            )
            continue
        if event.kind == "error":
            parts.append(
                TranscriptPart(id=event.id, kind="error", text=event.text or "")
            )
            continue
        if event.kind == "tool_call":
            seq += 1
            record = ToolCallRecord(
                seq=seq,
                event_id=event.id,
                name=event.tool_name or "unknown",
                original_name=event.original_name or event.tool_name or "unknown",
                call_id=event.call_id or event.id,
                input=event.input,
                command=event.command,
                path=event.path,
                url=event.url,
                server=event.server,
            )
            pending[record.call_id] = record
            records.append(record)
            parts.append(
                TranscriptPart(
                    id=event.id,
                    kind="tool_call",
                    tool_name=record.name,
                    original_name=record.original_name,
                    command=record.command,
                    path=record.path,
                    url=record.url,
                    input=record.input,
                )
            )
            continue
        if event.kind == "tool_result":
            record = pending.get(event.call_id or "")
            if record is not None:
                record.success = event.success
                record.exit_code = event.exit_code
                record.output = event.output
                record.result_event_id = event.id
            parts.append(
                TranscriptPart(
                    id=event.id,
                    kind="tool_result",
                    tool_name=event.tool_name,
                    original_name=event.original_name,
                    success=event.success,
                    exit_code=event.exit_code,
                    output=event.output or "",
                )
            )
    return AdaptedTranscript(parts=parts, tool_calls=records)


def _format_input(payload: dict[str, Any]) -> str:
    compact: dict[str, Any] = {}
    for key, value in payload.items():
        if key in {"streamContent", "contents", "new_string", "old_string"} and isinstance(
            value, str
        ):
            compact[key] = truncate_text(strip_controls(value))
        else:
            compact[key] = value
    try:
        return json.dumps(compact, ensure_ascii=False)
    except TypeError:
        return str(compact)


def _wrap_output(text: str, head: int, tail: int) -> str:
    cleaned = redact_secrets(truncate_text(text, head=head, tail=tail))
    return f"UNTRUSTED\n{cleaned}" if cleaned else "UNTRUSTED"


def serialize_transcript(
    parts: list[TranscriptPart],
    *,
    max_tokens: int = MAX_TRANSCRIPT_TOKENS,
) -> str:
    head, tail = HEAD_CHARS, TAIL_CHARS
    while True:
        blocks: list[str] = []
        for part in parts:
            if part.kind == "message":
                role = part.role or "assistant"
                body = redact_secrets(part.text or "")
                blocks.append(f"{part.id} [{role}]\n{body}")
            elif part.kind == "tool_call":
                header = (
                    f"{part.id} [tool_call] {part.tool_name} "
                    f"originalName={part.original_name}"
                )
                lines = [header]
                if part.command:
                    lines.append(f"command: {part.command}")
                if part.path:
                    lines.append(f"path: {part.path}")
                if part.url:
                    lines.append(f"url: {part.url}")
                if part.input:
                    lines.append(f"input: {_format_input(part.input)}")
                blocks.append("\n".join(lines))
            elif part.kind == "tool_result":
                status = "unknown" if part.success is None else (
                    "success" if part.success else "failure"
                )
                header = f"{part.id} [tool_result] {status}"
                if part.exit_code is not None:
                    header += f" exit={part.exit_code}"
                blocks.append(f"{header}\n{_wrap_output(part.output or '', head, tail)}")
            else:
                blocks.append(f"{part.id} [{part.kind}]\n{redact_secrets(part.text or '')}")
        text = "\n\n".join(blocks)
        if estimate_tokens(text) <= max_tokens or (head == 0 and tail == 0):
            return text
        if head > 200:
            head = max(0, head // 2)
            tail = max(0, tail // 2)
        else:
            head, tail = 0, 0


def compact_transcript_from_atif(source: Path | str | dict[str, Any]) -> str:
    adapted = adapt_transcript(parse_trajectory(source))
    return serialize_transcript(adapted.parts)


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2 or args[0] != "--atif":
        raise SystemExit(
            "usage: transcript.py --atif PATH [--compact OUT] [--print-compact]"
        )
    atif = Path(args[1])
    adapted = adapt_transcript(parse_trajectory(atif))
    compact = serialize_transcript(adapted.parts)
    if "--print-compact" in args:
        print(compact)
        return
    if "--compact" in args:
        out = Path(args[args.index("--compact") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(compact)
        return
    raise SystemExit("usage: transcript.py --atif PATH [--compact OUT] [--print-compact]")


if __name__ == "__main__":
    main()
