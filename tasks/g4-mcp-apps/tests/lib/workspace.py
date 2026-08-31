#!/usr/bin/env python3
"""Find the generated app under /workspace and grep packages/source."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

WORKSPACE = Path(os.environ.get("EVAL_WORKSPACE", "/workspace"))
SKIP_DIR_NAMES = frozenset(
    {"node_modules", ".git", ".next", "dist", "coverage", ".agents"}
)
SOURCE_SUFFIXES = (".ts", ".tsx", ".js", ".jsx")
CHAT_USER_TEXT = "Show the sample MCP app"
CHAT_SERVER_NAME = "Extra MCP"
AI_SDK_PROVIDERS_PREFIX = "@ai-sdk/"


def iter_package_jsons(root: Path) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        if "package.json" in filenames:
            found.append(Path(dirpath) / "package.json")
    return found


def _pkg_data(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _deps(data: dict) -> dict[str, str]:
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies"):
        value = data.get(key) or {}
        if isinstance(value, dict):
            deps.update({str(name): str(ver) for name, ver in value.items()})
    return deps


def find_app_root(workspace: Path | None = None) -> Path | None:
    root = workspace or WORKSPACE
    candidates: list[tuple[int, int, Path]] = []
    for pkg in iter_package_jsons(root):
        data = _pkg_data(pkg)
        deps = _deps(data)
        scripts = data.get("scripts") or {}
        if not isinstance(scripts, dict) or not scripts:
            continue
        score = 0
        if "@assistant-ui/react" in deps:
            score += 10
        if "dev" in scripts or "start" in scripts or "build" in scripts:
            score += 1
        candidates.append((score, -len(pkg.parent.parts), pkg.parent))
    if not candidates:
        fallback = root / "package.json"
        return root if fallback.is_file() else None
    candidates.sort(reverse=True)
    return candidates[0][2]


def package_has(app_root: Path, name: str) -> bool:
    return name in _deps(_pkg_data(app_root / "package.json"))


def has_ai_sdk_provider(app_root: Path) -> bool:
    return any(
        name.startswith(AI_SDK_PROVIDERS_PREFIX)
        for name in _deps(_pkg_data(app_root / "package.json"))
    )


def source_has(app_root: Path, marker: str) -> bool:
    for dirpath, dirnames, filenames in os.walk(app_root):
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
        for filename in filenames:
            if not filename.endswith(SOURCE_SUFFIXES):
                continue
            path = Path(dirpath) / filename
            try:
                if marker in path.read_text(errors="replace"):
                    return True
            except OSError:
                continue
    return False


def text_files_mention(app_root: Path, marker: str, names: tuple[str, ...]) -> bool:
    for name in names:
        path = app_root / name
        if path.is_file() and marker in path.read_text(errors="replace"):
            return True
    return False


SK_TOKEN_RE = re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]+")
PLACEHOLDER_SK_RE = re.compile(
    r"your|placeholder|example|changeme|insert|replace|\bhere\b",
    re.I,
)


def _is_placeholder_sk(token: str) -> bool:
    if PLACEHOLDER_SK_RE.search(token):
        return True
    body = token[3:]
    if body.lower().startswith("proj-"):
        body = body[5:]
    compact = re.sub(r"[-_]", "", body)
    if len(compact) < 20:
        return True
    letters = set(compact.lower())
    return len(letters) <= 1 or letters <= set("x0")


def env_has_live_secret(app_root: Path) -> bool:
    for name in (".env", ".env.local"):
        path = app_root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for token in SK_TOKEN_RE.findall(stripped):
                if not _is_placeholder_sk(token):
                    return True
    return False


def checks_profile() -> str:
    explicit = os.environ.get("CHECKS_PROFILE", "").strip()
    if explicit:
        return explicit
    if (WORKSPACE / "gold-app").is_dir():
        return "gold"
    return "pb1"


def main() -> None:
    if len(sys.argv) >= 2 and sys.argv[1] == "--print-root":
        found = find_app_root()
        if found is None:
            print("", end="")
            sys.exit(1)
        print(found)
        return
    if len(sys.argv) >= 2 and sys.argv[1] == "--print-profile":
        print(checks_profile())
        return
    sys.exit("usage: workspace.py --print-root | --print-profile")


if __name__ == "__main__":
    main()
