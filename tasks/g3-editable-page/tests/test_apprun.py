from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def test_ar_04_chat_route_post() -> None:
    """AR-04 POST /api/chat is a chat route."""
    base = os.environ.get("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    payload = json.dumps(
        {
            "id": "eval-ar-04",
            "messages": [
                {
                    "id": "u1",
                    "role": "user",
                    "parts": [{"type": "text", "text": "ping"}],
                }
            ],
        }
    ).encode()
    request = urllib.request.Request(
        f"{base}/api/chat",
        data=payload,
        method="POST",
        headers={
            "content-type": "application/json",
            "accept": "text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            content_type = response.headers.get("content-type", "")
            stream_header = response.headers.get("x-vercel-ai-ui-message-stream", "")
            body = response.read(4000)
    except urllib.error.HTTPError as error:
        status = error.code
        content_type = error.headers.get("content-type", "") if error.headers else ""
        stream_header = (
            error.headers.get("x-vercel-ai-ui-message-stream", "") if error.headers else ""
        )
        body = error.read(4000) if error.fp else b""

    assert status != 404
    lowered = content_type.lower()
    text = body.decode("utf-8", errors="replace")
    is_stream = "text/event-stream" in lowered or stream_header == "v1"
    is_chat_error = (
        status >= 400
        and "text/html" not in lowered
        and ("json" in lowered or "text/plain" in lowered or "error" in text.lower())
    )
    assert is_stream or is_chat_error, (
        f"POST /api/chat was not a chat route: status={status} type={content_type!r}"
    )
