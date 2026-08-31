"""Offline parser / helper checks. Not scored. Not run by Harbor test.sh."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from checks import mcp_enabled
from lib.transcript import (
    SPILLED_MARKER,
    adapt_transcript,
    compact_transcript_from_atif,
    estimate_tokens,
    parse_atif,
    parse_tool_content,
    parse_trajectory,
    serialize_transcript,
    strip_controls,
)
from lib.workspace import env_has_live_secret, find_app_root, package_has, source_has
from report import main as report_main
from report import write_results
from test_workflow import (
    ALLOWED_EXAMPLES,
    build_attempted,
    create_attempted,
    docs_before_scaffold_or_write,
    error_judge_skips,
    listed_example_create,
    successful_create,
    used_assistant_ui_mcp,
    used_web_docs,
    is_web_doc_read,
    web_docs_before_scaffold_or_write,
)

PHASE_B_ATIF = Path(__file__).resolve().parent / "phase-b-trajectory.json"
CURSOR_CLI_ATIF = (
    Path(__file__).resolve().parents[7]
    / "jobs"
    / "2026-08-20__18-03-22"
    / "pb-1__SK5cmoX"
    / "agent"
    / "trajectory.json"
)
CLAUDE_ATIF = (
    Path(__file__).resolve().parents[7]
    / "jobs"
    / "2026-08-20__19-12-19"
    / "pb-1__yKxLwQV"
    / "agent"
    / "trajectory.json"
)
CODEX_ATIF = (
    Path(__file__).resolve().parents[7]
    / "jobs"
    / "2026-08-20__19-12-44"
    / "pb-1__v9kH7U9"
    / "agent"
    / "trajectory.json"
)
CLAUDE_CREATE_ATIF = (
    Path(__file__).resolve().parents[7]
    / "jobs"
    / "2026-08-20__20-19-03"
    / "pb-1__D35oTjB"
    / "agent"
    / "trajectory.json"
)
APIFY_ATIF_DIR = (
    Path(__file__).resolve().parents[7]
    / "evals"
    / "docs"
    / "workstreams"
    / "assistant-ui-agent-evals"
    / "modules"
    / "m0-discovery"
    / "m0.3-traces-at-runtime"
    / "fixtures"
)


def _step(
    step_id: int,
    source: str,
    message: str = "",
    tool_calls: list[dict] | None = None,
    results: list[dict] | None = None,
) -> dict:
    step: dict = {"step_id": step_id, "source": source, "message": message}
    if tool_calls:
        step["tool_calls"] = tool_calls
        step["observation"] = {"results": results or []}
    return step


def _shell_result(call_id: str, command: str, exit_code: int, stdout: str) -> dict:
    kind = "success" if exit_code == 0 else "failure"
    return {
        "source_call_id": call_id,
        "content": json.dumps(
            {
                kind: {
                    "command": command,
                    "exitCode": exit_code,
                    "stdout": stdout,
                    "stderr": "",
                    "interleavedOutput": stdout,
                }
            }
        ),
    }


def _mini_atif() -> dict:
    ansi_out = "ok \x1b[31mred\x1b[0m done"
    large = "A" * 1500 + "MIDDLE" + "B" * 1500
    return {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "cursor-cli"},
        "steps": [
            _step(1, "user", "Build me a chat app."),
            _step(2, "thinking", "secret plan"),
            _step(
                3,
                "agent",
                "Checking docs.",
                [
                    {
                        "tool_call_id": "c-mcp",
                        "function_name": "mcpToolCall",
                        "arguments": {
                            "toolName": "assistantUIExamples",
                            "serverIdentifier": "assistant-ui",
                            "toolCallId": "drop-me",
                        },
                    }
                ],
                [
                    {
                        "source_call_id": "c-mcp",
                        "content": json.dumps(
                            {
                                "success": {
                                    "content": [
                                        {"text": {"text": "examples: with-ai-sdk-v7"}}
                                    ]
                                }
                            }
                        ),
                    }
                ],
            ),
            _step(
                4,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "c-fail",
                        "function_name": "shellToolCall",
                        "arguments": {
                            "command": (
                                "cd /workspace && npx assistant-ui@latest create . "
                                "--example with-ai-sdk-v7 --yes 2>&1"
                            )
                        },
                    }
                ],
                [
                    _shell_result(
                        "c-fail",
                        "cd /workspace && npx assistant-ui@latest create . --example with-ai-sdk-v7 --yes 2>&1",
                        1,
                        "error: unknown option '--yes'\n",
                    )
                ],
            ),
            _step(
                5,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "c-ok",
                        "function_name": "shellToolCall",
                        "arguments": {
                            "command": (
                                "cd /workspace && npx assistant-ui@latest create . "
                                "--example with-ai-sdk-v7 2>&1"
                            )
                        },
                    }
                ],
                [
                    _shell_result(
                        "c-ok",
                        "cd /workspace && npx assistant-ui@latest create . --example with-ai-sdk-v7 2>&1",
                        0,
                        ansi_out,
                    )
                ],
            ),
            _step(
                6,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "c-big",
                        "function_name": "shellToolCall",
                        "arguments": {"command": "echo big 2>&1"},
                    }
                ],
                [_shell_result("c-big", "echo big 2>&1", 0, large)],
            ),
            _step(
                7,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "c-unknown",
                        "function_name": "readLintsToolCall",
                        "arguments": {"paths": ["/workspace"]},
                    }
                ],
                [{"source_call_id": "c-unknown", "content": "no lints"}],
            ),
            _step(
                8,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "c-spill",
                        "function_name": "shellToolCall",
                        "arguments": {"command": "cat huge"},
                    }
                ],
                [
                    {
                        "source_call_id": "c-spill",
                        "content": json.dumps(
                            {"outputLocation": "/tmp/agent-tools/out.txt"}
                        ),
                    }
                ],
            ),
            _step(9, "agent", "Done. OPENAI_API_KEY=sk-secretvalue"),
        ],
    }


def test_find_app_root_prefers_assistant_ui(tmp_path: Path) -> None:
    nested = tmp_path / "apps" / "chat"
    nested.mkdir(parents=True)
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "root", "scripts": {"dev": "echo"}})
    )
    (nested / "package.json").write_text(
        json.dumps(
            {
                "name": "chat",
                "scripts": {"dev": "next", "build": "next build"},
                "dependencies": {"@assistant-ui/react": "0.0.0"},
            }
        )
    )
    (nested / "node_modules" / "pkg").mkdir(parents=True)
    (nested / "node_modules" / "pkg" / "package.json").write_text(
        json.dumps({"name": "pkg", "scripts": {"dev": "x"}})
    )
    assert find_app_root(tmp_path) == nested


def test_package_and_source_markers(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "name": "gold",
                "scripts": {"dev": "next"},
                "dependencies": {"@assistant-ui/react": "1.0.0"},
            }
        )
    )
    src = tmp_path / "app" / "page.tsx"
    src.parent.mkdir()
    src.write_text('import { AssistantRuntimeProvider } from "@assistant-ui/react";\n')
    assert package_has(tmp_path, "@assistant-ui/react")
    assert source_has(tmp_path, "AssistantRuntimeProvider")
    assert not source_has(tmp_path, "AssistantCloud")
    persist = tmp_path / "lib" / "history.ts"
    persist.parent.mkdir()
    persist.write_text("window.localStorage.setItem('k', 'v');\n")
    assert source_has(tmp_path, "localStorage")
    agents = tmp_path / ".agents" / "skills" / "x.ts"
    agents.parent.mkdir(parents=True)
    agents.write_text("AssistantCloud\n")
    assert not source_has(tmp_path, "AssistantCloud")


def test_env_placeholder_sk_is_not_a_live_secret(tmp_path: Path) -> None:
    (tmp_path / ".env.local").write_text(
        "OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n"
    )
    assert not env_has_live_secret(tmp_path)
    (tmp_path / ".env.local").write_text("OPENAI_API_KEY=sk-your-key-here\n")
    assert not env_has_live_secret(tmp_path)
    (tmp_path / ".env.local").write_text(
        "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n"
    )
    assert env_has_live_secret(tmp_path)


def test_parse_mini_atif_maps_tools() -> None:
    events = parse_atif(_mini_atif())
    kinds = [event.kind for event in events]
    assert "thinking" in kinds
    names = [
        (event.tool_name, event.original_name)
        for event in events
        if event.kind == "tool_call"
    ]
    assert ("tool_use", "assistantUIExamples") in names
    assert ("shell", "shellToolCall") in names
    assert ("unknown", "readLintsToolCall") in names
    create = next(
        event
        for event in events
        if event.kind == "tool_call" and event.command and "--yes" in event.command
    )
    assert create.command == (
        "npx assistant-ui@latest create . --example with-ai-sdk-v7 --yes"
    )
    assert "toolCallId" not in create.input


def test_adapt_pairs_and_drops_thinking() -> None:
    adapted = adapt_transcript(parse_atif(_mini_atif()))
    assert all(part.kind != "thinking" for part in adapted.parts)
    shells = [record for record in adapted.tool_calls if record.name == "shell"]
    assert shells[0].exit_code == 1 and shells[0].success is False
    assert shells[1].exit_code == 0 and shells[1].success is True
    assert used_assistant_ui_mcp(adapted.tool_calls)
    assert docs_before_scaffold_or_write(adapted.tool_calls)
    created = successful_create(adapted.tool_calls)
    assert created is not None
    assert listed_example_create(adapted.tool_calls) is not None
    assert "with-ai-sdk-v7" in ALLOWED_EXAMPLES


def test_serialize_truncates_strips_and_wraps() -> None:
    compact = compact_transcript_from_atif(_mini_atif())
    assert "secret plan" not in compact
    assert "UNTRUSTED" in compact
    assert "\x1b" not in compact
    assert "sk-secretvalue" not in compact
    assert "[REDACTED]" in compact
    assert "characters omitted" in compact
    assert SPILLED_MARKER in compact
    assert "evt-" in compact
    assert estimate_tokens(compact) < 70_000


def test_strip_controls_keeps_newlines() -> None:
    assert strip_controls("a\x1b[31mb\nc") == "ab\nc"


def test_write_before_docs_fails_discovery() -> None:
    atif = {
        "schema_version": "ATIF-v1.7",
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "w1",
                        "function_name": "editToolCall",
                        "arguments": {"path": "/workspace/app/page.tsx"},
                    }
                ],
                [
                    {
                        "source_call_id": "w1",
                        "content": json.dumps(
                            {"success": {"path": "/workspace/app/page.tsx"}}
                        ),
                    }
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_atif(atif)).tool_calls
    assert not used_assistant_ui_mcp(records)
    assert not docs_before_scaffold_or_write(records)
    assert successful_create(records) is None
    assert error_judge_skips(records) == {
        "WF-E-01": "no assistant-ui create command in the transcript",
        "WF-E-02": "no TypeScript or package build command in the transcript",
    }


def _help_then_example_atif(*, include_example: bool) -> dict:
    steps = [
        _step(1, "user", "go"),
        _step(
            2,
            "agent",
            "",
            [
                {
                    "tool_call_id": "help",
                    "function_name": "shellToolCall",
                    "arguments": {
                        "command": "npx assistant-ui@latest create --help"
                    },
                }
            ],
            [
                _shell_result(
                    "help",
                    "npx assistant-ui@latest create --help",
                    0,
                    "Usage: assistant-ui create [options]\n",
                )
            ],
        ),
    ]
    if include_example:
        command = (
            "npx assistant-ui@latest create . "
            "--example with-custom-thread-list --use-npm --no-skills"
        )
        steps.append(
            _step(
                3,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "create",
                        "function_name": "shellToolCall",
                        "arguments": {"command": command},
                    }
                ],
                [_shell_result("create", command, 0, "Scaffolded.\n")],
            )
        )
    return {"schema_version": "ATIF-v1.7", "steps": steps}


def test_help_create_does_not_count_as_scaffold() -> None:
    records = adapt_transcript(
        parse_atif(_help_then_example_atif(include_example=False))
    ).tool_calls
    assert successful_create(records) is None
    assert listed_example_create(records) is None
    assert not create_attempted(records)
    assert error_judge_skips(records)["WF-E-01"].startswith("no assistant-ui create")


def test_help_then_listed_example_passes_scaffold() -> None:
    records = adapt_transcript(
        parse_atif(_help_then_example_atif(include_example=True))
    ).tool_calls
    created = successful_create(records)
    listed = listed_example_create(records)
    assert created is not None and created.exit_code == 0
    assert listed is not None
    assert "with-custom-thread-list" in (listed.command or "")
    assert "--help" not in (created.command or "")
    assert "WF-E-01" not in error_judge_skips(records)


def test_create_assistant_ui_template_counts_as_scaffold() -> None:
    records = adapt_transcript(
        parse_atif(
            _shell_atif(
                "npx create-assistant-ui@latest -t eve .",
                0,
                "Creating project from template: Eve\n",
            )
        )
    ).tool_calls
    created = successful_create(records)
    listed = listed_example_create(records)
    assert created is not None and created.exit_code == 0
    assert listed is not None
    assert "WF-E-01" not in error_judge_skips(records)


def test_short_e_example_flag_counts_as_listed() -> None:
    records = adapt_transcript(
        parse_atif(
            _shell_atif(
                "npx assistant-ui@latest create html-canvas-chat -e with-artifacts --use-npm",
                0,
                "Project created successfully!\n",
            )
        )
    ).tool_calls
    listed = listed_example_create(records)
    assert successful_create(records) is not None
    assert listed is not None
    assert "with-artifacts" in (listed.command or "")


def _shell_atif(command: str, exit_code: int, stdout: str = "") -> dict:
    return {
        "schema_version": "ATIF-v1.7",
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "c1",
                        "function_name": "shellToolCall",
                        "arguments": {"command": command},
                    }
                ],
                [_shell_result("c1", command, exit_code, stdout)],
            ),
        ],
    }


def test_failed_create_still_applies_wf_e_01() -> None:
    records = adapt_transcript(
        parse_atif(
            _shell_atif(
                "npx assistant-ui@latest create . --example with-ai-sdk-v7 --yes",
                1,
                "error: unknown option '--yes'\n",
            )
        )
    ).tool_calls
    assert create_attempted(records)
    assert successful_create(records) is None
    assert "WF-E-01" not in error_judge_skips(records)
    assert "WF-E-02" in error_judge_skips(records)


def test_build_attempt_applies_wf_e_02() -> None:
    records = adapt_transcript(
        parse_atif(_shell_atif("npm install assistant-stream && npm run build", 1, "TS2322"))
    ).tool_calls
    assert build_attempted(records)
    assert "WF-E-02" not in error_judge_skips(records)
    assert "WF-E-01" in error_judge_skips(records)


def _claude_bash_result(
    call_id: str, stdout: str, *, is_error: bool = False, interrupted: bool = False
) -> dict:
    return {
        "source_call_id": call_id,
        "content": stdout,
        "extra": {
            "tool_result_metadata": {
                "tool_use_result": {
                    "stdout": stdout,
                    "stderr": "",
                    "interrupted": interrupted,
                    "isImage": False,
                    "noOutputExpected": False,
                },
                "raw_tool_result": {
                    "tool_use_id": call_id,
                    "type": "tool_result",
                    "content": stdout,
                    "is_error": is_error,
                },
            },
            "tool_result_is_error": is_error,
        },
    }


def _codex_exec_js(call_id: str, js: str) -> dict:
    return {
        "tool_call_id": call_id,
        "function_name": "exec",
        "arguments": {"input": js},
    }


def _codex_chunk_result(call_id: str, payload: dict) -> dict:
    return {
        "source_call_id": call_id,
        "content": repr(
            [
                {
                    "type": "input_text",
                    "text": "Script completed\nWall time 0.1 seconds\nOutput:\n",
                },
                {"type": "input_text", "text": json.dumps(payload)},
            ]
        ),
    }


def test_codex_wrapped_create_counts_as_attempt() -> None:
    cmd = "npx assistant-ui@latest create . --example with-ai-sdk-v7"
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "codex"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [_codex_exec_js("e1", f'const r = await tools.exec_command({{cmd:"{cmd}"}});')],
                [_shell_result("e1", cmd, 0, "Project created successfully.\n")],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    assert records[0].command == cmd
    assert create_attempted(records)
    created = successful_create(records)
    assert created is not None and created.exit_code == 0
    listed = listed_example_create(records)
    assert listed is not None
    assert "with-ai-sdk-v7" in (listed.command or "")
    assert "WF-E-01" not in error_judge_skips(records)


def test_codex_python_repr_result_exit_code() -> None:
    content = repr(
        [
            {"type": "input_text", "text": "Script completed\nOutput:\n"},
            {
                "type": "input_text",
                "text": json.dumps(
                    {"chunk_id": "x", "exit_code": 0, "output": "up to date\n"}
                ),
            },
        ]
    )
    success, exit_code, output = parse_tool_content(content)
    assert success is True
    assert exit_code == 0
    assert "up to date" in output


def test_codex_tty_create_pairs_write_stdin_exit() -> None:
    cmd = "npx assistant-ui@latest create . --example with-ai-sdk-v7"
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "codex"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    _codex_exec_js(
                        "e1",
                        'const r = await tools.exec_command({cmd:"'
                        + cmd
                        + '",workdir:"/workspace",yield_time_ms:1000,tty:true});',
                    )
                ],
                [
                    _codex_chunk_result(
                        "e1",
                        {
                            "chunk_id": "a",
                            "session_id": 7824,
                            "output": "Need to install the following packages:\n",
                        },
                    )
                ],
            ),
            _step(
                3,
                "agent",
                "",
                [
                    _codex_exec_js(
                        "e2",
                        'const r = await tools.write_stdin({session_id:7824,chars:"",yield_time_ms:1000});',
                    )
                ],
                [
                    _codex_chunk_result(
                        "e2",
                        {
                            "chunk_id": "b",
                            "exit_code": 0,
                            "output": "Project created successfully!\n",
                        },
                    )
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    created = successful_create(records)
    listed = listed_example_create(records)
    assert created is not None and created.exit_code == 0
    assert created.command == cmd
    assert "Project created successfully" in (created.output or "")
    assert listed is not None
    assert "with-ai-sdk-v7" in (listed.command or "")
    assert "WF-E-01" not in error_judge_skips(records)


def test_codex_web_search_is_not_a_create() -> None:
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "codex"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    _codex_exec_js(
                        "e1",
                        'const r = await tools.web__run({search_query:[{q:"assistant-ui '
                        'CLI create thread component assistant-ui create command"}]});',
                    )
                ],
                [
                    _codex_chunk_result(
                        "e1",
                        {"chunk_id": "w", "output": "search hits\n"},
                    )
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    assert records[0].name == "web_search"
    assert records[0].original_name == "web__run"
    assert records[0].command is None
    assert not create_attempted(records)
    assert "WF-E-01" in error_judge_skips(records)
    assert not used_web_docs(records)
    assert not is_web_doc_read(records[0])


def test_codex_web_open_docs_page_is_a_read() -> None:
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "codex"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    _codex_exec_js(
                        "o1",
                        'const r = await tools.web__run({open:[{ref_id:"turn0search3"}],'
                        'response_length:"long"}); text(r);',
                    )
                ],
                [
                    _codex_chunk_result(
                        "o1",
                        {
                            "chunk_id": "w",
                            "output": (
                                "AI SDK v7 — assistant-ui "
                                "(https://www.assistant-ui.com/docs/runtimes/ai-sdk/v7.md)\n"
                                "For AI agents: a documentation index is available at llms.txt\n"
                            ),
                        },
                    )
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    assert records[0].name == "web_fetch"
    assert records[0].original_name == "web__run"
    assert used_web_docs(records)
    assert is_web_doc_read(records[0])
    assert web_docs_before_scaffold_or_write(records)


def test_claude_webfetch_llms_txt_is_a_read() -> None:
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "claude-code"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "f1",
                        "function_name": "WebFetch",
                        "arguments": {
                            "url": "https://www.assistant-ui.com/llms.txt",
                        },
                    }
                ],
                [
                    {
                        "source_call_id": "f1",
                        "content": "# assistant-ui docs index\n",
                    }
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    assert records[0].name == "web_fetch"
    assert records[0].url == "https://www.assistant-ui.com/llms.txt"
    assert used_web_docs(records)
    assert is_web_doc_read(records[0])


def test_docs_curl_counts_as_web_read() -> None:
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "cursor-cli"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "c1",
                        "function_name": "shellToolCall",
                        "arguments": {
                            "command": "curl -sL https://www.assistant-ui.com/llms.txt",
                        },
                    }
                ],
                [
                    _shell_result(
                        "c1",
                        "curl -sL https://www.assistant-ui.com/llms.txt",
                        0,
                        "# index",
                    )
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    assert used_web_docs(records)
    assert is_web_doc_read(records[0])


@pytest.mark.skipif(not CODEX_ATIF.is_file(), reason="codex job ATIF not on disk")
def test_codex_job_web_docs_would_pass_mcp_off() -> None:
    records = adapt_transcript(parse_trajectory(CODEX_ATIF)).tool_calls
    assert any(record.name == "web_search" for record in records)
    assert any(record.name == "web_fetch" for record in records)
    assert used_web_docs(records)
    assert web_docs_before_scaffold_or_write(records)
    assert not used_assistant_ui_mcp(records)


def test_claude_bash_create_uses_is_error_extra() -> None:
    cmd = (
        "npx --yes assistant-ui@latest create . -t default --use-npm "
        "--skip-install 2>&1 | tail -60"
    )
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "claude-code"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "b1",
                        "function_name": "Bash",
                        "arguments": {"command": cmd},
                    }
                ],
                [
                    _claude_bash_result(
                        "b1",
                        "✓ Project created successfully!\n",
                        is_error=False,
                    )
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    created = successful_create(records)
    assert created is not None and created.exit_code == 0
    assert created.command is not None and " create " in created.command
    assert listed_example_create(records) is None


def test_claude_bash_failed_create_is_not_successful() -> None:
    cmd = "npx assistant-ui@latest create . --example with-ai-sdk-v7 --yes"
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "claude-code"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "b1",
                        "function_name": "Bash",
                        "arguments": {"command": cmd},
                    }
                ],
                [
                    _claude_bash_result(
                        "b1",
                        "error: unknown option '--yes'\n",
                        is_error=True,
                    )
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    assert create_attempted(records)
    assert successful_create(records) is None
    assert records[0].exit_code == 1
    assert records[0].success is False


def test_cq_g_01_does_not_skip_error_checks() -> None:
    from checks import SKIP_AFTER_FAIL

    skipped = SKIP_AFTER_FAIL["CQ-G-01"]
    assert "WF-E-01" not in skipped
    assert "WF-E-02" not in skipped
    assert "WF-D-01" in skipped


@pytest.mark.skipif(not CLAUDE_ATIF.is_file(), reason="claude-code job ATIF not on disk")
def test_claude_job_skips_vacuous_error_checks() -> None:
    records = adapt_transcript(parse_trajectory(CLAUDE_ATIF)).tool_calls
    assert error_judge_skips(records) == {
        "WF-E-01": "no assistant-ui create command in the transcript",
        "WF-E-02": "no TypeScript or package build command in the transcript",
    }


@pytest.mark.skipif(
    not CLAUDE_CREATE_ATIF.is_file(), reason="claude-code create job ATIF not on disk"
)
def test_claude_create_job_wf_s_01() -> None:
    records = adapt_transcript(parse_trajectory(CLAUDE_CREATE_ATIF)).tool_calls
    created = successful_create(records)
    assert created is not None and created.exit_code == 0
    assert created.command is not None
    assert "assistant-ui" in created.command and " create" in created.command
    assert listed_example_create(records) is None


@pytest.mark.skipif(not CODEX_ATIF.is_file(), reason="codex job ATIF not on disk")
def test_codex_job_tty_create_succeeds() -> None:
    records = adapt_transcript(parse_trajectory(CODEX_ATIF)).tool_calls
    created = successful_create(records)
    listed = listed_example_create(records)
    assert created is not None and created.exit_code == 0
    assert created.command is not None
    assert "assistant-ui" in created.command and " create" in created.command
    assert listed is not None
    assert "with-ai-sdk-v7" in (listed.command or "")


@pytest.mark.skipif(not CURSOR_CLI_ATIF.is_file(), reason="cursor-cli job ATIF not on disk")
def test_cursor_cli_job_trajectory_wf_s() -> None:
    records = adapt_transcript(parse_atif(CURSOR_CLI_ATIF)).tool_calls
    created = successful_create(records)
    listed = listed_example_create(records)
    assert created is not None and created.exit_code == 0
    assert "--help" not in (created.command or "")
    assert listed is not None
    assert "with-custom-thread-list" in (listed.command or "")


def test_phase_b_atif_roundtrip() -> None:
    assert PHASE_B_ATIF.is_file()
    adapted = adapt_transcript(parse_atif(PHASE_B_ATIF))
    assert used_assistant_ui_mcp(adapted.tool_calls)
    assert docs_before_scaffold_or_write(adapted.tool_calls)
    created = successful_create(adapted.tool_calls)
    assert created is not None and created.exit_code == 0
    failed = next(
        record
        for record in adapted.tool_calls
        if record.command and "--yes" in record.command
    )
    assert failed.exit_code == 1
    assert "WF-E-01" not in error_judge_skips(adapted.tool_calls)
    assert "WF-E-02" not in error_judge_skips(adapted.tool_calls)
    compact = serialize_transcript(adapted.parts)
    assert "unknown option '--yes'" in compact
    assert estimate_tokens(compact) <= 70_000
    assert "[user]" in compact
    assert "[assistant]" in compact


def test_pass_rate_reward(tmp_path: Path) -> None:
    checks_path = tmp_path / "checks.json"
    reward_path = tmp_path / "reward.txt"
    write_results(
        checks_path,
        reward_path,
        [
            {"name": "CQ-G-01", "passed": True},
            {
                "name": "WF-D-01",
                "passed": True,
                "status": "skipped",
                "notes": "gold skips workflow",
            },
            {"name": "BR-06", "passed": False},
        ],
    )
    assert reward_path.read_text() == "0.5000\n"
    write_results(
        checks_path,
        reward_path,
        [
            {"name": "CQ-G-01", "passed": True},
            {
                "name": "AR-04",
                "passed": True,
                "status": "skipped",
                "notes": "skipped because AR-03 failed",
            },
            {
                "name": "BR-07",
                "passed": True,
                "status": "skipped",
                "notes": "no submit control (interactables-without-submit path)",
            },
        ],
    )
    assert reward_path.read_text() == "0.3333\n"
    write_results(
        checks_path,
        reward_path,
        [
            {"name": "CQ-G-01", "passed": True},
            {"name": "AR-01", "passed": True},
            {
                "name": "WF-D-01",
                "passed": True,
                "status": "skipped",
                "notes": "gold skips workflow",
            },
        ],
    )
    assert reward_path.read_text() == "1.0000\n"
    write_results(
        checks_path,
        reward_path,
        [
            {"name": "WF-E-01", "passed": False, "status": "error", "notes": "no key"},
        ],
    )
    assert not reward_path.exists()


def test_mcp_enabled_defaults_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PB1_MCP", raising=False)
    assert mcp_enabled() is True
    monkeypatch.setenv("PB1_MCP", "on")
    assert mcp_enabled() is True
    monkeypatch.setenv("PB1_MCP", "OFF")
    assert mcp_enabled() is False
    monkeypatch.setenv("PB1_MCP", "0")
    assert mcp_enabled() is False
    monkeypatch.setenv("PB1_MCP", "false")
    assert mcp_enabled() is False


def test_report_scores_discovery_when_mcp_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PB1_MCP", "off")
    checks_path = tmp_path / "checks.json"
    reward_path = tmp_path / "reward.txt"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "report.py",
            "--checks",
            str(checks_path),
            "--reward",
            str(reward_path),
            "--profile",
            "pb1",
        ],
    )
    report_main()
    rows = {row["name"]: row for row in json.loads(checks_path.read_text())["checks"]}
    assert rows["WF-D-01"].get("status") != "skipped"
    assert rows["WF-D-02"].get("status") != "skipped"
    assert rows["WF-D-01"]["passed"] is False


def test_report_scores_discovery_when_mcp_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PB1_MCP", "on")
    checks_path = tmp_path / "checks.json"
    reward_path = tmp_path / "reward.txt"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "report.py",
            "--checks",
            str(checks_path),
            "--reward",
            str(reward_path),
            "--profile",
            "pb1",
        ],
    )
    report_main()
    rows = {row["name"]: row for row in json.loads(checks_path.read_text())["checks"]}
    assert rows["WF-D-01"].get("status") != "skipped"
    assert rows["WF-D-01"]["passed"] is False


def _apify_atif(name: str) -> Path:
    path = APIFY_ATIF_DIR / name
    if not path.is_file():
        pytest.skip(f"apify fixture missing: {path}")
    return path


def test_apify_tools_probe_claude_parses() -> None:
    events = parse_trajectory(_apify_atif("apify-tools-probe-claude-code.json"))
    adapted = adapt_transcript(events)
    names = {(record.name, record.original_name, record.server) for record in adapted.tool_calls}
    assert ("tool_use", "search-actors", "apify") in names
    assert any(record.name == "unknown" and record.original_name == "WaitForMcpServers" for record in adapted.tool_calls)
    compact = serialize_transcript(adapted.parts)
    assert "search-actors" in compact


def test_apify_tools_probe_cursor_parses() -> None:
    events = parse_trajectory(_apify_atif("apify-tools-probe-cursor-cli.json"))
    adapted = adapt_transcript(events)
    originals = {record.original_name for record in adapted.tool_calls if record.name == "tool_use"}
    assert "search-actors" in originals


def test_apify_tools_probe_codex_parses() -> None:
    events = parse_trajectory(_apify_atif("apify-tools-probe-codex.json"))
    adapted = adapt_transcript(events)
    assert any(record.name == "shell" for record in adapted.tool_calls)
    mcp = [
        record
        for record in adapted.tool_calls
        if record.name == "tool_use" and record.server == "apify"
    ]
    assert mcp
    assert any("search_actors" in (record.original_name or "") for record in mcp)


def test_apify_stdio_probe_claude_bash() -> None:
    events = parse_trajectory(_apify_atif("apify-stdio-probe-claude-code.json"))
    adapted = adapt_transcript(events)
    shells = [record for record in adapted.tool_calls if record.name == "shell"]
    assert shells
    assert any(record.command and "claude" in record.command for record in shells)


def test_apify_stdio_probe_codex_wait_unknown() -> None:
    events = parse_trajectory(_apify_atif("apify-stdio-probe-codex.json"))
    adapted = adapt_transcript(events)
    assert any(record.name == "shell" for record in adapted.tool_calls)
    assert any(
        record.name == "unknown" and record.original_name == "wait"
        for record in adapted.tool_calls
    )


def test_claude_assistant_ui_mcp_maps_for_wf_d() -> None:
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "claude-code"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "d1",
                        "function_name": "mcp__assistant-ui__assistantUIExamples",
                        "arguments": {},
                    }
                ],
                [{"source_call_id": "d1", "content": "ok"}],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    assert used_assistant_ui_mcp(records)
    assert records[0].server == "assistant-ui"
    assert records[0].original_name == "assistantUIExamples"


def test_codex_assistant_ui_mcp_from_exec() -> None:
    atif = {
        "schema_version": "ATIF-v1.7",
        "agent": {"name": "codex"},
        "steps": [
            _step(1, "user", "go"),
            _step(
                2,
                "agent",
                "",
                [
                    {
                        "tool_call_id": "e1",
                        "function_name": "exec",
                        "arguments": {
                            "input": (
                                "await tools.mcp__assistant-ui__assistantUIDocs"
                                "({query: 'create'});"
                            )
                        },
                    }
                ],
                [
                    _shell_result(
                        "e1",
                        "await tools.mcp__assistant-ui__assistantUIDocs({query: 'create'});",
                        0,
                        "ok",
                    )
                ],
            ),
        ],
    }
    records = adapt_transcript(parse_trajectory(atif)).tool_calls
    assert used_assistant_ui_mcp(records)
    assert any(
        record.name == "tool_use"
        and record.server == "assistant-ui"
        and record.original_name == "assistantUIDocs"
        for record in records
    )
