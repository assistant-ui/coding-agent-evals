from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def test_ar_04_eve_health() -> None:
    """AR-04 GET /eve/v1/health is the Eve HTTP channel."""
    base = os.environ.get("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    request = urllib.request.Request(
        f"{base}/eve/v1/health",
        method="GET",
        headers={"accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            content_type = response.headers.get("content-type", "")
            body = response.read(4000)
    except urllib.error.HTTPError as error:
        status = error.code
        content_type = error.headers.get("content-type", "") if error.headers else ""
        body = error.read(4000) if error.fp else b""

    assert status != 404
    text = body.decode("utf-8", errors="replace")
    lowered = content_type.lower()
    is_json = "json" in lowered
    payload: dict = {}
    if is_json:
        try:
            parsed = json.loads(text)
            payload = parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            payload = {}
    assert status == 200 and is_json and payload.get("ok") is True, (
        f"GET /eve/v1/health was not Eve ready: status={status} type={content_type!r} body={text[:400]!r}"
    )
