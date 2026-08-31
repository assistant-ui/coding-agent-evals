from __future__ import annotations

from playwright.sync_api import Page, expect

from lib.workspace import CHAT_USER_TEXT


def _composer(page: Page):
    return page.get_by_role("textbox", name="Message input").or_(
        page.get_by_placeholder("Send a message...")
    )


def _send(page: Page):
    return page.get_by_role("button", name="Send message")


def _goto_composer(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(_composer(page).first).to_be_visible(timeout=15_000)


def _send_user_text(page: Page) -> None:
    composer = _composer(page).first
    composer.fill(CHAT_USER_TEXT)
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
    """BR-03 Type the PB-1 text, send enables, send."""
    _goto_composer(page, base_url)
    _send_user_text(page)


def test_br_04_user_message_visible(page: Page, base_url: str) -> None:
    """BR-04 User message appears in the thread."""
    _goto_composer(page, base_url)
    _send_user_text(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)


def test_br_05_assistant_working_or_error(page: Page, base_url: str) -> None:
    """BR-05 Assistant message, or working, or error/stub."""
    _goto_composer(page, base_url)
    _send_user_text(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)
    assistant = page.locator('[data-role="assistant"]')
    working = page.get_by_label("Assistant is working")
    error = page.locator(".aui-message-error-message")
    expect(assistant.or_(working).or_(error).first).to_be_visible(timeout=20_000)
    page.screenshot(path="/logs/verifier/after-send.png", full_page=True)


def test_br_06_user_message_survives_reload(page: Page, base_url: str) -> None:
    """BR-06 After reload, the same user text is still visible."""
    _goto_composer(page, base_url)
    _send_user_text(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)
    # History is written when the run finishes (Stop → Send). Do not wait for
    # a localStorage key: SQLite / API adapters persist without one.
    expect(page.get_by_role("button", name="Stop generating")).to_be_visible(
        timeout=15_000
    )
    expect(_send(page).first).to_be_visible(timeout=30_000)
    page.reload()
    expect(_composer(page).first).to_be_visible(timeout=15_000)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=15_000)
    page.screenshot(path="/logs/verifier/after-reload.png", full_page=True)
