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


def test_cq_g_03_vite_package(app_root: Path) -> None:
    """CQ-G-03 Depends on vite."""
    assert package_has(app_root, "vite")


def test_cq_g_04_not_next_app(app_root: Path) -> None:
    """CQ-G-04 Vite app, not Next.js."""
    assert not package_has(app_root, "next")


def test_cq_g_05_runtime_provider(app_root: Path) -> None:
    """CQ-G-05 AssistantRuntimeProvider in source."""
    assert source_has(app_root, "AssistantRuntimeProvider")


def test_cq_g_06_thread(app_root: Path) -> None:
    """CQ-G-06 Thread in source."""
    assert source_has(app_root, "assistant-ui/thread") or source_has(app_root, "<Thread")


def test_cq_p_01_external_store_or_chat_runtime(app_root: Path) -> None:
    """CQ-P-01 useExternalStoreRuntime or useChatRuntime in source."""
    assert source_has(app_root, "useExternalStoreRuntime") or source_has(
        app_root, "useChatRuntime"
    )


def test_cq_p_02_vite_or_tanstack_router(app_root: Path) -> None:
    """CQ-P-02 Vite config is present."""
    assert (app_root / "vite.config.ts").is_file() or (
        app_root / "vite.config.js"
    ).is_file()


def test_cq_p_03_chat_server_fn(app_root: Path) -> None:
    """CQ-P-03 Chat server function or route."""
    assert (
        source_has(app_root, "chatStream")
        or source_has(app_root, "createServerFn")
        or source_has(app_root, "createUIMessageStream")
        or source_has(app_root, "/api/chat")
    )


def test_cq_p_04_vite_define_config(app_root: Path) -> None:
    """CQ-P-04 vite defineConfig in source."""
    assert source_has(app_root, "defineConfig")
    assert source_has(app_root, 'from "vite"') or source_has(app_root, "from 'vite'")


def test_cq_p_05_openai_key_docs(app_root: Path) -> None:
    """CQ-P-05 OPENAI_API_KEY documented; no live secrets."""
    documented = text_files_mention(
        app_root,
        "OPENAI_API_KEY",
        (".env.example", "README.md", "README"),
    )
    assert documented
    assert not env_has_live_secret(app_root)
