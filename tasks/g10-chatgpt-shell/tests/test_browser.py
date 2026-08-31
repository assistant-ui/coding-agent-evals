from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from lib.workspace import THREAD_A_TEXT, THREAD_B_TEXT, MODEL_PROBE_TEXT

NEW_THREAD = re.compile(r"new\s*(thread|chat)", re.I)
COPY = re.compile(r"^Copy$", re.I)


def _composer(page: Page):
    return page.get_by_placeholder("Ask anything").or_(
        page.get_by_role("textbox", name="Message input")
    ).or_(page.get_by_placeholder("Send a message..."))


def _send(page: Page):
    return page.get_by_role("button", name="Send message")


def _new_thread(page: Page):
    return page.get_by_role("button", name=NEW_THREAD).or_(
        page.get_by_text(NEW_THREAD)
    )


def _model_trigger(page: Page):
    return page.get_by_test_id("g10-model-selector").get_by_role("combobox").or_(
        page.get_by_role("combobox")
    )


def _goto_shell(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(_composer(page).first).to_be_visible(timeout=15_000)


def _send_text(page: Page, text: str) -> None:
    composer = _composer(page).first
    composer.click()
    composer.fill(text)
    expect(_send(page).first).to_be_enabled()
    _send(page).first.click()


def _wait_user_and_reply(page: Page, user_text: str) -> None:
    expect(page.get_by_text(user_text).first).to_be_visible(timeout=10_000)
    reply = (
        page.get_by_text(re.compile(r"Using model:", re.I))
        .or_(page.get_by_text(re.compile(r"you said:", re.I)))
        .or_(page.get_by_role("button", name=COPY))
    )
    expect(reply.first).to_be_visible(timeout=20_000)


def test_br_01_chatgpt_shell_visible(page: Page, base_url: str) -> None:
    """BR-01 ChatGPT shell visible (composer, sidebar, model)."""
    _goto_shell(page, base_url)
    expect(_composer(page).first).to_be_visible()
    expect(_new_thread(page).first).to_be_visible(timeout=10_000)
    expect(_model_trigger(page).first).to_be_visible(timeout=10_000)


def test_br_02_no_pageerror_on_load(page: Page, base_url: str) -> None:
    """BR-02 No critical pageerror on load."""
    errors: list[str] = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    _goto_shell(page, base_url)
    expect(_composer(page).first).to_be_visible()
    assert not errors, f"pageerror before shell visible: {errors}"


def test_br_03_send_thread_a(page: Page, base_url: str) -> None:
    """BR-03 Send thread A message."""
    _goto_shell(page, base_url)
    _send_text(page, THREAD_A_TEXT)


def test_br_04_thread_a_visible(page: Page, base_url: str) -> None:
    """BR-04 Thread A user message and a reply visible."""
    _goto_shell(page, base_url)
    _send_text(page, THREAD_A_TEXT)
    _wait_user_and_reply(page, THREAD_A_TEXT)


def test_br_05_new_thread_then_b(page: Page, base_url: str) -> None:
    """BR-05 New Thread then send thread B."""
    _goto_shell(page, base_url)
    _send_text(page, THREAD_A_TEXT)
    _wait_user_and_reply(page, THREAD_A_TEXT)
    _new_thread(page).first.click()
    expect(_composer(page).first).to_be_visible(timeout=10_000)
    _send_text(page, THREAD_B_TEXT)
    _wait_user_and_reply(page, THREAD_B_TEXT)
    expect(page.get_by_text(THREAD_B_TEXT).first).to_be_visible()


def test_br_06_switch_back_to_a(page: Page, base_url: str) -> None:
    """BR-06 Switch back to thread A."""
    _goto_shell(page, base_url)
    _send_text(page, THREAD_A_TEXT)
    _wait_user_and_reply(page, THREAD_A_TEXT)
    _new_thread(page).first.click()
    _send_text(page, THREAD_B_TEXT)
    _wait_user_and_reply(page, THREAD_B_TEXT)

    # In-memory thread list titles stay "New Chat" unless generateTitle is
    # wired — switch via inactive list item, not by message text.
    triggers = page.locator('[data-slot="aui_thread-list-item-trigger"]')
    expect(triggers.first).to_be_visible(timeout=10_000)
    assert triggers.count() >= 2, f"expected ≥2 threads, got {triggers.count()}"

    inactive = page.locator(
        '[data-slot="aui_thread-list-item"]:not([data-active]) '
        '[data-slot="aui_thread-list-item-trigger"]'
    )
    if inactive.count() == 0:
        inactive = triggers.nth(triggers.count() - 1)
    else:
        inactive = inactive.first
    inactive.click(force=True)

    expect(page.get_by_text(THREAD_A_TEXT).first).to_be_visible(timeout=10_000)
    expect(page.get_by_text(THREAD_B_TEXT)).to_have_count(0)
    page.screenshot(path="/logs/verifier/after-switch-a.png", full_page=True)


def test_br_07_model_selector_wires(page: Page, base_url: str) -> None:
    """BR-07 Model selector changes the selected model."""
    _goto_shell(page, base_url)
    trigger = _model_trigger(page).first
    expect(trigger).to_be_visible(timeout=10_000)
    before = (trigger.inner_text() or "").strip()
    trigger.click(force=True)

    items = page.locator('[data-slot="model-selector-item"]')
    expect(items.first).to_be_visible(timeout=10_000)
    chosen_id = None
    count = items.count()
    for i in range(count):
        item = items.nth(i)
        value = item.get_attribute("data-value") or ""
        label = (item.inner_text() or "").strip()
        if value and value.lower() not in before.lower() and label not in before:
            chosen_id = value
            item.click(force=True)
            break
        if not value and label and label not in before:
            chosen_id = label
            item.click(force=True)
            break
    if chosen_id is None:
        option_b = page.get_by_role(
            "option", name=re.compile(r"Stub B|gpt-stub-b", re.I)
        )
        expect(option_b.first).to_be_visible(timeout=5_000)
        chosen_id = "gpt-stub-b"
        option_b.first.click(force=True)

    after_label = (trigger.inner_text() or "").strip()
    _send_text(page, MODEL_PROBE_TEXT)
    expect(page.get_by_text(MODEL_PROBE_TEXT).first).to_be_visible(timeout=10_000)
    body = page.locator("body").inner_text()
    chosen = (chosen_id or "").lower()
    wired = bool(chosen) and (
        chosen in body.lower()
        or chosen in after_label.lower()
        or (after_label and after_label != before)
    )
    assert wired, (
        f"picking model {chosen_id!r} did not show in the picker or the reply "
        f"(before={before!r} after={after_label!r})"
    )
    page.screenshot(path="/logs/verifier/after-model.png", full_page=True)
