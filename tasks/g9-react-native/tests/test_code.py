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


def test_cq_g_02_react_native_package(app_root: Path) -> None:
    """CQ-G-02 Depends on @assistant-ui/react-native."""
    assert package_has(app_root, "@assistant-ui/react-native")


def test_cq_g_03_expo_package(app_root: Path) -> None:
    """CQ-G-03 Depends on expo."""
    assert package_has(app_root, "expo")


def test_cq_g_04_not_next_app(app_root: Path) -> None:
    """CQ-G-04 Expo / React Native app, not Next.js."""
    assert not package_has(app_root, "next")
    assert package_has(app_root, "expo")
    assert package_has(app_root, "react-native") or package_has(
        app_root, "expo-router"
    )


def test_cq_g_05_runtime_provider(app_root: Path) -> None:
    """CQ-G-05 AssistantRuntimeProvider in source."""
    assert source_has(app_root, "AssistantRuntimeProvider")


def test_cq_g_06_thread(app_root: Path) -> None:
    """CQ-G-06 Thread in source."""
    assert source_has(app_root, "assistant-ui/thread") or source_has(app_root, "<Thread")


def test_cq_p_01_define_toolkit(app_root: Path) -> None:
    """CQ-P-01 defineToolkit in source."""
    assert source_has(app_root, "defineToolkit")


def test_cq_p_02_use_generative(app_root: Path) -> None:
    """CQ-P-02 \"use generative\" toolkit."""
    assert source_has(app_root, '"use generative"') or source_has(
        app_root, "'use generative'"
    )


def test_cq_p_03_tool_render(app_root: Path) -> None:
    """CQ-P-03 Tool render (generative UI)."""
    assert (
        source_has(app_root, "render:")
        or source_has(app_root, "WeatherToolUI")
        or source_has(app_root, "GeocodeToolUI")
    )


def test_cq_p_04_weather_or_geocode_tool(app_root: Path) -> None:
    """CQ-P-04 weather_search or geocode_location tool."""
    assert source_has(app_root, "weather_search") or source_has(
        app_root, "geocode_location"
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
