from __future__ import annotations

from playwright.sync_api import Page, expect

from lib.workspace import CHAT_USER_TEXT

STUB_REPLY = "You said: Hello"


def _composer(page: Page):
    return page.get_by_role("textbox", name="Message input").or_(
        page.get_by_placeholder("Send a message...")
    )


def _send(page: Page):
    return page.get_by_role("button", name="Send message")


def _goto_composer(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(_composer(page).first).to_be_visible(timeout=15_000)


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
    """BR-03 Type Hello, send enables, send."""
    _goto_composer(page, base_url)
    _send_prompt(page)


def test_br_04_user_message_visible(page: Page, base_url: str) -> None:
    """BR-04 User message appears in the thread."""
    _goto_composer(page, base_url)
    _send_prompt(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)


def test_br_05_vite_reply_or_error(page: Page, base_url: str) -> None:
    """BR-05 Vite chat reply or error after send."""
    _goto_composer(page, base_url)
    _send_prompt(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)
    outcome = (
        page.get_by_text(STUB_REPLY)
        .or_(page.get_by_text("Sorry, an error occurred"))
        .or_(page.get_by_text("OPENAI_API_KEY"))
        .or_(page.get_by_role("alert"))
    )
    expect(outcome.first).to_be_visible(timeout=20_000)
    page.screenshot(path="/logs/verifier/after-send.png", full_page=True)
