from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from lib.workspace import CHAT_SERVER_NAME, CHAT_USER_TEXT

ADD = re.compile(r"add( server)?", re.I)
MCP_OR_SERVERS = re.compile(r"mcp|server", re.I)
REMOVE = re.compile(r"remove", re.I)


def _composer(page: Page):
    return page.get_by_role("textbox", name="Message input").or_(
        page.get_by_placeholder("Send a message...")
    )


def _send(page: Page):
    return page.get_by_role("button", name="Send message")


def _mcp_trigger(page: Page):
    return page.locator(".aui-mcp-config-trigger").or_(
        page.get_by_role("button", name=MCP_OR_SERVERS)
    )


def _goto_composer(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(_composer(page).first).to_be_visible(timeout=15_000)


def _open_mcp_dialog(page: Page) -> None:
    trigger = _mcp_trigger(page).first
    expect(trigger).to_be_attached(timeout=10_000)
    trigger.click(force=True)
    expect(page.get_by_text(ADD).first).to_be_visible(timeout=10_000)


def _send_prompt(page: Page) -> None:
    composer = _composer(page).first
    composer.click()
    composer.press_sequentially(CHAT_USER_TEXT, delay=20)
    expect(_send(page).first).to_be_enabled()
    _send(page).first.click()


def test_br_01_composer_visible(page: Page, base_url: str) -> None:
    """BR-01 Composer (message input) is visible."""
    _goto_composer(page, base_url)


def test_br_02_no_pageerror_on_load(page: Page, base_url: str) -> None:
    """BR-02 No critical pageerror on load."""
    errors: list[str] = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    _goto_composer(page, base_url)
    assert not errors, f"pageerror before composer visible: {errors}"


def test_br_03_type_and_send(page: Page, base_url: str) -> None:
    """BR-03 Type the show-app prompt, send enables, send."""
    _goto_composer(page, base_url)
    _send_prompt(page)


def test_br_04_user_message_visible(page: Page, base_url: str) -> None:
    """BR-04 User message appears in the thread."""
    _goto_composer(page, base_url)
    _send_prompt(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)


def test_br_05_mcp_servers_dialog(page: Page, base_url: str) -> None:
    """BR-05 Add/remove MCP servers UI opens from the chat."""
    _goto_composer(page, base_url)
    _open_mcp_dialog(page)
    expect(page.get_by_text(ADD).first).to_be_visible()


def test_br_06_add_then_remove_server(page: Page, base_url: str) -> None:
    """BR-06 Add a server from the UI, then remove it."""
    _goto_composer(page, base_url)
    _open_mcp_dialog(page)
    page.get_by_role("button", name=ADD).first.click()
    name = page.get_by_placeholder("My MCP server").or_(
        page.get_by_label(re.compile(r"^name$", re.I))
    )
    url = page.get_by_placeholder("https://example.com/mcp").or_(
        page.get_by_label(re.compile(r"^url$", re.I))
    )
    expect(name.first).to_be_visible(timeout=10_000)
    name.first.fill(CHAT_SERVER_NAME)
    url.first.fill("http://127.0.0.1:8787/mcp")
    page.get_by_role("button", name=re.compile(r"^add server$", re.I)).last.click()
    expect(page.get_by_text(CHAT_SERVER_NAME, exact=True).first).to_be_visible(
        timeout=10_000
    )
    page.get_by_role("button", name=REMOVE).last.click()
    expect(page.get_by_text(CHAT_SERVER_NAME, exact=True)).to_have_count(0)


def test_br_07_mcp_app_widget(page: Page, base_url: str) -> None:
    """BR-07 MCP App widget / iframe appears in the thread."""
    _goto_composer(page, base_url)
    _send_prompt(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)
    widget = page.locator("[data-mcp-app-resource]").or_(page.locator("iframe"))
    expect(widget.first).to_be_visible(timeout=20_000)
    page.screenshot(path="/logs/verifier/after-send.png", full_page=True)
