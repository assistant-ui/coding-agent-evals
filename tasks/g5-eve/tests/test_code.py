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


def test_cq_g_03_eve_packages(app_root: Path) -> None:
    """CQ-G-03 Depends on @assistant-ui/eve and eve."""
    assert package_has(app_root, "@assistant-ui/eve")
    assert package_has(app_root, "eve")


def test_cq_g_04_provider_package(app_root: Path) -> None:
    """CQ-G-04 Eve package is the runtime provider (not @ai-sdk/*)."""
    assert package_has(app_root, "eve")


def test_cq_g_05_runtime_provider(app_root: Path) -> None:
    """CQ-G-05 AssistantRuntimeProvider in source."""
    assert source_has(app_root, "AssistantRuntimeProvider")


def test_cq_g_06_thread(app_root: Path) -> None:
    """CQ-G-06 Thread in source."""
    assert source_has(app_root, "assistant-ui/thread") or source_has(app_root, "<Thread")


def test_cq_p_01_eve_runtime(app_root: Path) -> None:
    """CQ-P-01 useEveAgentRuntime in source."""
    assert source_has(app_root, "useEveAgentRuntime")


def test_cq_p_02_with_eve(app_root: Path) -> None:
    """CQ-P-02 Next config mounts Eve with withEve."""
    assert source_has(app_root, "withEve")


def test_cq_p_03_define_agent(app_root: Path) -> None:
    """CQ-P-03 Eve defineAgent in source."""
    assert source_has(app_root, "defineAgent")


def test_cq_p_04_eve_channel(app_root: Path) -> None:
    """CQ-P-04 Eve HTTP channel (eveChannel or /eve/v1)."""
    assert (
        source_has(app_root, "eveChannel")
        or source_has(app_root, "/eve/v1")
        or source_has(app_root, "from \"eve/next\"")
        or source_has(app_root, "from 'eve/next'")
    )


def test_cq_p_05_gateway_key_docs(app_root: Path) -> None:
    """CQ-P-05 AI_GATEWAY_API_KEY documented; no live secrets."""
    documented = text_files_mention(
        app_root,
        "AI_GATEWAY_API_KEY",
        (".env.example", "README.md", "README"),
    )
    assert documented
    assert not env_has_live_secret(app_root)
