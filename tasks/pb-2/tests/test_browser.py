from __future__ import annotations

import re
import time

from playwright.sync_api import Page, expect

from lib.workspace import CHAT_FOLLOW_UP, CHAT_USER_TEXT


def _composer(page: Page):
    return page.get_by_role("textbox", name="Message input").or_(
        page.get_by_placeholder("Send a message...")
    )


def _send(page: Page):
    return page.get_by_role("button", name="Send message")


def _side_canvas(page: Page):
    return (
        page.locator("aside")
        .or_(page.get_by_role("complementary"))
        .or_(
            page.get_by_role(
                "heading", name=re.compile(r"canvas|preview|artifact", re.I)
            )
        )
        .or_(page.locator("iframe"))
    )


def _preview_iframe(page: Page):
    return page.get_by_test_id("artifact-preview").or_(page.locator("iframe"))


def _iframe_body_text(page: Page) -> str:
    """Read canvas HTML. Sandboxed srcDoc iframes block parent contentDocument."""
    iframe = _preview_iframe(page).first
    srcdoc = iframe.get_attribute("srcdoc") or ""
    if srcdoc.strip():
        return srcdoc
    try:
        # Playwright 1.62: content_frame is a FrameLocator, not a method.
        text = iframe.content_frame.locator("body").inner_text(timeout=1_000)
        if text.strip():
            return text
    except Exception:
        pass
    return iframe.evaluate(
        "el => (el.contentDocument && el.contentDocument.body && el.contentDocument.body.innerText) || ''"
    )


def _wait_iframe_body(
    page: Page,
    *,
    nonempty: bool = False,
    not_equal: str | None = None,
    timeout_ms: int = 20_000,
) -> str:
    """Poll iframe text. Avoid expect.poll — verifier Playwright has no poll."""
    deadline = time.monotonic() + timeout_ms / 1000
    last = ""
    while time.monotonic() < deadline:
        last = _iframe_body_text(page)
        if nonempty and last.strip():
            return last
        if not_equal is not None and last != not_equal:
            return last
        page.wait_for_timeout(250)
    if nonempty:
        raise AssertionError(f"iframe body stayed empty; last={last!r}")
    raise AssertionError(f"iframe body did not change; last={last!r}")


def _goto_composer(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(_composer(page).first).to_be_visible(timeout=15_000)


def _send_text(page: Page, text: str) -> None:
    composer = _composer(page).first
    composer.fill(text)
    expect(_send(page).first).to_be_enabled()
    _send(page).first.click()


def test_br_01_composer_and_canvas_visible(page: Page, base_url: str) -> None:
    """BR-01 Composer and a side canvas / preview are visible."""
    _goto_composer(page, base_url)
    expect(_side_canvas(page).first).to_be_visible()


def test_br_02_no_pageerror_on_load(page: Page, base_url: str) -> None:
    """BR-02 No critical pageerror on load."""
    errors: list[str] = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    _goto_composer(page, base_url)
    assert not errors, f"pageerror before composer visible: {errors}"


def test_br_03_type_and_send(page: Page, base_url: str) -> None:
    """BR-03 Type the HTML-card prompt, send enables, send."""
    _goto_composer(page, base_url)
    _send_text(page, CHAT_USER_TEXT)


def test_br_04_user_message_visible(page: Page, base_url: str) -> None:
    """BR-04 User message appears in the thread."""
    _goto_composer(page, base_url)
    _send_text(page, CHAT_USER_TEXT)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)


def test_br_05_canvas_renders_html_card(page: Page, base_url: str) -> None:
    """BR-05 Canvas iframe renders HTML after send."""
    _goto_composer(page, base_url)
    _send_text(page, CHAT_USER_TEXT)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)
    iframe = _preview_iframe(page)
    expect(iframe.first).to_be_visible(timeout=20_000)
    _wait_iframe_body(page, nonempty=True)
    page.screenshot(path="/logs/verifier/after-send.png", full_page=True)


def test_br_06_follow_up_updates_canvas(page: Page, base_url: str) -> None:
    """BR-06 Follow-up changes the canvas iframe content."""
    _goto_composer(page, base_url)
    _send_text(page, CHAT_USER_TEXT)
    expect(_preview_iframe(page).first).to_be_visible(timeout=20_000)
    before = _wait_iframe_body(page, nonempty=True)
    _send_text(page, CHAT_FOLLOW_UP)
    expect(page.get_by_text(CHAT_FOLLOW_UP).first).to_be_visible(timeout=10_000)
    _wait_iframe_body(page, not_equal=before)
