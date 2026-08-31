from __future__ import annotations

import re
import time

from playwright.sync_api import Page, expect

from lib.workspace import (
    CHAT_FOLLOW_UP,
    CHAT_USER_TEXT,
    THREAD_A_TEXT,
    THREAD_B_TEXT,
)

NEW_THREAD = re.compile(r"new\s*(thread|chat)", re.I)


def _composer(page: Page):
    return page.get_by_role("textbox", name="Message input").or_(
        page.get_by_placeholder("Send a message...")
    )


def _send(page: Page):
    return page.get_by_role("button", name="Send message")


def _new_thread(page: Page):
    return page.get_by_role("button", name=NEW_THREAD).or_(
        page.get_by_text(NEW_THREAD)
    )


def _preview_iframe(page: Page):
    return (
        page.get_by_test_id("artifact-surface")
        .locator("iframe")
        .or_(page.get_by_test_id("artifact-preview"))
        .or_(page.locator("iframe"))
    )


def _iframe_body_text(page: Page) -> str:
    iframe = _preview_iframe(page).first
    srcdoc = iframe.get_attribute("srcdoc") or ""
    if srcdoc.strip():
        return srcdoc
    try:
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
    contains: str | None = None,
    timeout_ms: int = 20_000,
) -> str:
    deadline = time.monotonic() + timeout_ms / 1000
    last = ""
    while time.monotonic() < deadline:
        last = _iframe_body_text(page)
        if contains is not None and contains in last:
            return last
        if nonempty and last.strip():
            return last
        if not_equal is not None and last != not_equal:
            return last
        page.wait_for_timeout(250)
    if contains is not None:
        raise AssertionError(f"iframe missing {contains!r}; last={last!r}")
    if nonempty:
        raise AssertionError(f"iframe body stayed empty; last={last!r}")
    raise AssertionError(f"iframe body did not change; last={last!r}")


def _goto_shell(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(_composer(page).first).to_be_visible(timeout=15_000)


def _send_text(page: Page, text: str) -> None:
    composer = _composer(page).first
    composer.click()
    composer.fill(text)
    expect(_send(page).first).to_be_enabled()
    _send(page).first.click()


def _open_canvas(page: Page) -> None:
    iframe = _preview_iframe(page)
    try:
        expect(iframe.first).to_be_visible(timeout=8_000)
        return
    except Exception:
        pass
    opener = (
        page.get_by_test_id("artifact-trigger")
        .or_(page.get_by_role("button", name=re.compile(r"workbench|preview", re.I)))
        .or_(page.get_by_text(re.compile(r"open workbench|open preview", re.I)))
    )
    expect(opener.first).to_be_visible(timeout=15_000)
    opener.first.click()
    expect(_preview_iframe(page).first).to_be_visible(timeout=15_000)


def _wait_user_and_artifact(page: Page, user_text: str) -> None:
    expect(page.get_by_text(user_text).first).to_be_visible(timeout=10_000)
    cue = (
        page.get_by_text(
            re.compile(r"rendered the html|html artifact|welcome card", re.I)
        )
        .or_(page.get_by_test_id("artifact-trigger"))
        .or_(page.get_by_role("button", name=re.compile(r"workbench|preview", re.I)))
        .or_(page.get_by_role("button", name=re.compile(r"^Copy$", re.I)))
        .or_(_preview_iframe(page))
        .or_(page.get_by_test_id("artifact-surface"))
    )
    expect(cue.first).to_be_visible(timeout=20_000)


def test_br_01_claude_shell_visible(page: Page, base_url: str) -> None:
    """BR-01 Claude shell visible (composer, sidebar)."""
    _goto_shell(page, base_url)
    expect(_composer(page).first).to_be_visible()
    expect(_new_thread(page).first).to_be_visible(timeout=10_000)


def test_br_02_no_pageerror_on_load(page: Page, base_url: str) -> None:
    """BR-02 No critical pageerror on load."""
    errors: list[str] = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    _goto_shell(page, base_url)
    expect(_composer(page).first).to_be_visible()
    assert not errors, f"pageerror before shell visible: {errors}"


def test_br_03_send_card_prompt(page: Page, base_url: str) -> None:
    """BR-03 Send HTML-card prompt."""
    _goto_shell(page, base_url)
    _send_text(page, CHAT_USER_TEXT)


def test_br_04_user_and_ack(page: Page, base_url: str) -> None:
    """BR-04 User message and artifact activity visible."""
    _goto_shell(page, base_url)
    _send_text(page, CHAT_USER_TEXT)
    _wait_user_and_artifact(page, CHAT_USER_TEXT)


def test_br_05_canvas_renders_html(page: Page, base_url: str) -> None:
    """BR-05 Canvas iframe renders the HTML card."""
    _goto_shell(page, base_url)
    _send_text(page, CHAT_USER_TEXT)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)
    _open_canvas(page)
    _wait_iframe_body(page, contains="Welcome")
    page.screenshot(path="/logs/verifier/after-send.png", full_page=True)


def test_br_06_follow_up_updates_canvas(page: Page, base_url: str) -> None:
    """BR-06 Follow-up updates the canvas iframe content."""
    _goto_shell(page, base_url)
    _send_text(page, CHAT_USER_TEXT)
    _open_canvas(page)
    before = _wait_iframe_body(page, nonempty=True)
    _send_text(page, CHAT_FOLLOW_UP)
    expect(page.get_by_text(CHAT_FOLLOW_UP).first).to_be_visible(timeout=10_000)
    after = _wait_iframe_body(page, not_equal=before)
    assert "Launch" in after or "launch" in after.lower()


def test_br_07_thread_switch(page: Page, base_url: str) -> None:
    """BR-07 New Thread, thread B, switch back to A."""
    _goto_shell(page, base_url)
    _send_text(page, THREAD_A_TEXT)
    expect(page.get_by_text(THREAD_A_TEXT).first).to_be_visible(timeout=10_000)

    _new_thread(page).first.click()
    expect(_composer(page).first).to_be_visible(timeout=10_000)
    _send_text(page, THREAD_B_TEXT)
    expect(page.get_by_text(THREAD_B_TEXT).first).to_be_visible(timeout=10_000)

    triggers = page.locator('[data-slot="aui_thread-list-item-trigger"]')
    expect(triggers.first).to_be_visible(timeout=10_000)
    assert triggers.count() >= 2, f"expected ≥2 threads, got {triggers.count()}"

    inactive = page.locator(
        '[data-slot="aui_thread-list-item"]:not([data-active]) '
        '[data-slot="aui_thread-list-item-trigger"]'
    )
    target = inactive.first if inactive.count() else triggers.nth(triggers.count() - 1)
    target.click(force=True)

    expect(page.get_by_text(THREAD_A_TEXT).first).to_be_visible(timeout=10_000)
    expect(page.get_by_text(THREAD_B_TEXT)).to_have_count(0)
    page.screenshot(path="/logs/verifier/after-switch-a.png", full_page=True)
