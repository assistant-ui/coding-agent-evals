from __future__ import annotations

import os
from pathlib import Path

import pytest

from lib.workspace import (
    env_has_live_secret,
    find_app_root,
    package_has,
    source_has,
    text_files_mention,
)

APP_ROOT = Path(os.environ.get("APP_ROOT", ""))


@pytest.fixture(scope="module")
def app_root() -> Path:
    root = APP_ROOT if APP_ROOT else find_app_root()
    if root is None or not (root / "package.json").is_file():
        pytest.fail("app root with package.json was not found under /workspace")
    return root


def test_cq_g_01_app_package_json(app_root: Path) -> None:
    """CQ-G-01 App package.json exists under /workspace."""
    assert (app_root / "package.json").is_file()


def test_cq_g_02_react_package(app_root: Path) -> None:
    """CQ-G-02 Depends on @assistant-ui/react."""
    assert package_has(app_root, "@assistant-ui/react")


def test_cq_g_03_ai_sdk_packages(app_root: Path) -> None:
    """CQ-G-03 Depends on an assistant-ui AI SDK package and ai."""
    assert package_has(app_root, "@assistant-ui/react-ai-sdk") or package_has(
        app_root, "@assistant-ui/ai-sdk"
    )
    assert package_has(app_root, "ai")


def test_cq_g_04_mastra_packages(app_root: Path) -> None:
    """CQ-G-04 Depends on @mastra/core and @mastra/ai-sdk."""
    assert package_has(app_root, "@mastra/core")
    assert package_has(app_root, "@mastra/ai-sdk")


def test_cq_g_05_runtime_provider(app_root: Path) -> None:
    """CQ-G-05 AssistantRuntimeProvider in source."""
    assert source_has(app_root, "AssistantRuntimeProvider")


def test_cq_g_06_thread(app_root: Path) -> None:
    """CQ-G-06 Thread in source."""
    assert source_has(app_root, "assistant-ui/thread") or source_has(app_root, "<Thread")


def test_cq_p_01_use_chat_runtime(app_root: Path) -> None:
    """CQ-P-01 useChatRuntime in source."""
    assert source_has(app_root, "useChatRuntime")


def test_cq_p_02_mastra_agent_lookup(app_root: Path) -> None:
    """CQ-P-02 Chat route looks up a Mastra agent."""
    assert (
        source_has(app_root, "handleChatStream")
        or source_has(app_root, "agentId")
        or source_has(app_root, "getAgent(")
        or source_has(app_root, "getAgentById")
        or source_has(app_root, "mastra.getAgent")
    )


def test_cq_p_03_to_ai_sdk_stream(app_root: Path) -> None:
    """CQ-P-03 Route adapts Mastra to an AI SDK UI stream."""
    assert source_has(app_root, "handleChatStream") or source_has(
        app_root, "toAISdkStream"
    )


def test_cq_p_04_mastra_agent(app_root: Path) -> None:
    """CQ-P-04 Mastra Agent from @mastra/core/agent."""
    assert source_has(app_root, "@mastra/core/agent") or source_has(
        app_root, '@mastra/core/agent'
    )


def test_cq_p_05_openai_key_docs(app_root: Path) -> None:
    """CQ-P-05 OPENAI_API_KEY documented; no live secrets."""
    documented = text_files_mention(
        app_root,
        "OPENAI_API_KEY",
        (".env.example", "README.md", "README"),
    )
    assert documented
    assert not env_has_live_secret(app_root)
