from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from lib.workspace import (
    CHAT_USER_TEXT,
    EMAIL_AFTER_ASSISTANT,
    EMAIL_AFTER_USER_EDIT,
    FIRST_NAME_AFTER_ASSISTANT,
)


def _composer(page: Page):
    return page.get_by_role("textbox", name="Message input").or_(
        page.get_by_placeholder("Send a message...")
    )


def _send(page: Page):
    return page.get_by_role("button", name="Send message")


def _first_name(page: Page):
    return page.get_by_label("First name").or_(
        page.get_by_role("textbox", name=re.compile(r"^(first )?name$", re.I))
    )


def _email(page: Page):
    return page.get_by_label("Email").or_(
        page.get_by_role("textbox", name=re.compile(r"email", re.I))
    )


def _submit(page: Page):
    return page.get_by_role("button", name=re.compile(r"^submit$", re.I))


def _goto_composer(page: Page, base_url: str) -> None:
    page.goto(base_url)
    expect(_composer(page).first).to_be_visible(timeout=15_000)


def _send_fill_prompt(page: Page) -> None:
    composer = _composer(page).first
    composer.fill(CHAT_USER_TEXT)
    expect(_send(page).first).to_be_enabled()
    _send(page).first.click()


def test_br_01_composer_and_fields_visible(page: Page, base_url: str) -> None:
    """BR-01 Composer and editable fields are visible."""
    _goto_composer(page, base_url)
    expect(_first_name(page).first).to_be_visible()
    expect(_email(page).first).to_be_visible()


def test_br_02_no_pageerror_on_load(page: Page, base_url: str) -> None:
    """BR-02 No critical pageerror on load."""
    errors: list[str] = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    _goto_composer(page, base_url)
    assert not errors, f"pageerror before composer visible: {errors}"


def test_br_03_type_and_send(page: Page, base_url: str) -> None:
    """BR-03 Type the fill prompt, send enables, send."""
    _goto_composer(page, base_url)
    _send_fill_prompt(page)


def test_br_04_user_message_visible(page: Page, base_url: str) -> None:
    """BR-04 User message appears in the thread."""
    _goto_composer(page, base_url)
    _send_fill_prompt(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)


def test_br_05_assistant_updates_fields(page: Page, base_url: str) -> None:
    """BR-05 Assistant updates the same on-page name and email fields."""
    _goto_composer(page, base_url)
    _send_fill_prompt(page)
    expect(page.get_by_text(CHAT_USER_TEXT).first).to_be_visible(timeout=10_000)
    expect(_email(page).first).to_have_value(EMAIL_AFTER_ASSISTANT, timeout=20_000)
    first_value = _first_name(page).first.input_value()
    last_value = ""
    last_name = page.get_by_label("Last name")
    if last_name.count():
        last_value = last_name.first.input_value()
    assert FIRST_NAME_AFTER_ASSISTANT in first_value or FIRST_NAME_AFTER_ASSISTANT in (
        first_value + " " + last_value
    ), f"name fields did not include {FIRST_NAME_AFTER_ASSISTANT!r}: {first_value!r} {last_value!r}"
    page.screenshot(path="/logs/verifier/after-send.png", full_page=True)


def test_br_06_user_edit_keeps_value(page: Page, base_url: str) -> None:
    """BR-06 After a user edit, the email field keeps the new value."""
    _goto_composer(page, base_url)
    _send_fill_prompt(page)
    expect(_email(page).first).to_have_value(EMAIL_AFTER_ASSISTANT, timeout=20_000)
    _email(page).first.fill(EMAIL_AFTER_USER_EDIT)
    expect(_email(page).first).to_have_value(EMAIL_AFTER_USER_EDIT)
    page.wait_for_timeout(500)
    expect(_email(page).first).to_have_value(EMAIL_AFTER_USER_EDIT)


def test_br_07_submit_feedback(page: Page, base_url: str) -> None:
    """BR-07 Submit control shows visible success or submitting feedback."""
    _goto_composer(page, base_url)
    _send_fill_prompt(page)
    expect(_email(page).first).to_have_value(EMAIL_AFTER_ASSISTANT, timeout=20_000)
    submit = _submit(page)
    if submit.count() == 0:
        pytest.skip("no submit control (interactables-without-submit path)")
    submit.first.click()
    feedback = (
        page.get_by_role("alert")
        .or_(page.get_by_role("status"))
        .or_(
            page.get_by_text(
                re.compile(r"submit|success|signed|done|thank", re.I)
            )
        )
    )
    expect(feedback.first).to_be_visible(timeout=20_000)
