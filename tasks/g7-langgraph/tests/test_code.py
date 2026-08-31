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


def test_cq_g_03_langchain_runtime_package(app_root: Path) -> None:
    """CQ-G-03 Depends on an assistant-ui LangGraph/LangChain runtime."""
    assert package_has(app_root, "@assistant-ui/react-langchain") or package_has(
        app_root, "@assistant-ui/react-langgraph"
    )


def test_cq_g_04_langgraph_sdk(app_root: Path) -> None:
    """CQ-G-04 Depends on @langchain/langgraph-sdk or @langchain/react."""
    assert package_has(app_root, "@langchain/langgraph-sdk") or package_has(
        app_root, "@langchain/react"
    )


def test_cq_g_05_runtime_provider(app_root: Path) -> None:
    """CQ-G-05 AssistantRuntimeProvider in source."""
    assert source_has(app_root, "AssistantRuntimeProvider")


def test_cq_g_06_thread(app_root: Path) -> None:
    """CQ-G-06 Thread in source."""
    assert source_has(app_root, "assistant-ui/thread") or source_has(app_root, "<Thread")


def test_cq_p_01_langgraph_runtime(app_root: Path) -> None:
    """CQ-P-01 useStreamRuntime or useLangGraphRuntime in source."""
    assert source_has(app_root, "useStreamRuntime") or source_has(
        app_root, "useLangGraphRuntime"
    )


def test_cq_p_02_langgraph_client(app_root: Path) -> None:
    """CQ-P-02 LangGraph runtime, SDK client, or threads.create."""
    if source_has(app_root, "useStreamRuntime") or source_has(
        app_root, "useLangGraphRuntime"
    ):
        return
    assert (
        source_has(app_root, "@langchain/langgraph-sdk")
        or source_has(app_root, "threads.create")
        or source_has(app_root, 'from "@langchain/react"')
        or source_has(app_root, "from '@langchain/react'")
    )


def test_cq_p_03_hitl_purchase_stock(app_root: Path) -> None:
    """CQ-P-03 Confirm / approval UI in source."""
    confirm = (
        source_has(app_root, "confirm")
        or source_has(app_root, "Confirm")
        or source_has(app_root, "addResult")
    )
    assert confirm


def test_cq_p_04_toolkit_or_interrupt(app_root: Path) -> None:
    """CQ-P-04 Toolkit / interrupt wiring for the approval step."""
    assert (
        source_has(app_root, "defineToolkit")
        or source_has(app_root, "externalTool")
        or source_has(app_root, "useLangChainInterrupt")
        or source_has(app_root, "interrupt")
    )


def test_cq_p_05_langgraph_key_docs(app_root: Path) -> None:
    """CQ-P-05 LANGCHAIN_API_KEY or LANGGRAPH_API_URL documented; no live secrets."""
    documented = text_files_mention(
        app_root,
        "LANGCHAIN_API_KEY",
        (".env.example", "README.md", "README"),
    ) or text_files_mention(
        app_root,
        "LANGGRAPH_API_URL",
        (".env.example", "README.md", "README"),
    )
    assert documented
    assert not env_has_live_secret(app_root)
