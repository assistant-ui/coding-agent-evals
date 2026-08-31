from __future__ import annotations

import os
from pathlib import Path

import pytest

from lib.workspace import (
    env_has_live_secret,
    find_app_root,
    has_ai_sdk_provider,
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


def test_cq_g_04_provider_package(app_root: Path) -> None:
    """CQ-G-04 Provider package present."""
    if source_has(app_root, "AssistantCloud") and not has_ai_sdk_provider(app_root):
        pytest.skip("Cloud-only provider; no @ai-sdk/* required")
    assert has_ai_sdk_provider(app_root)


def test_cq_g_05_runtime_provider(app_root: Path) -> None:
    """CQ-G-05 AssistantRuntimeProvider in source."""
    assert source_has(app_root, "AssistantRuntimeProvider")


def test_cq_g_06_thread(app_root: Path) -> None:
    """CQ-G-06 Thread in source."""
    assert source_has(app_root, "assistant-ui/thread") or source_has(app_root, "<Thread")


def test_cq_p_01_use_chat_runtime(app_root: Path) -> None:
    """CQ-P-01 useChatRuntime in source."""
    assert source_has(app_root, "useChatRuntime")


def test_cq_p_02_chat_stream(app_root: Path) -> None:
    """CQ-P-02 Chat route streams UI messages."""
    assert source_has(app_root, "createUIMessageStream") or source_has(
        app_root, "streamText"
    )


def test_cq_p_03_thread_list_sidebar(app_root: Path) -> None:
    """CQ-P-03 Conversation sidebar / thread-list in source."""
    assert (
        source_has(app_root, "ThreadListSidebar")
        or source_has(app_root, "ThreadListPrimitive")
        or source_has(app_root, "threadlist-sidebar")
        or source_has(app_root, "thread-list")
    )


def test_cq_p_04_model_selector(app_root: Path) -> None:
    """CQ-P-04 ModelSelector wired to config.modelName."""
    has_selector = source_has(app_root, "ModelSelector") or source_has(
        app_root, "model-selector"
    )
    has_model_name = source_has(app_root, "modelName") or source_has(
        app_root, "config.modelName"
    )
    assert has_selector and has_model_name


def test_cq_p_05_openai_key_docs(app_root: Path) -> None:
    """CQ-P-05 OPENAI_API_KEY documented; no live secrets."""
    documented = text_files_mention(
        app_root,
        "OPENAI_API_KEY",
        (".env.example", "README.md", "README"),
    )
    assert documented
    assert not env_has_live_secret(app_root)
