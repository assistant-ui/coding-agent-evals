from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def test_ar_04_langgraph_threads_route() -> None:
    """AR-04 POST /api/threads is a LangGraph thread route."""
    base = os.environ.get("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    payload = json.dumps({"metadata": {}}).encode()
    request = urllib.request.Request(
        f"{base}/api/threads",
        data=payload,
        method="POST",
        headers={"content-type": "application/json", "accept": "application/json"},
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
    is_thread = "thread_id" in text or "json" in lowered
    is_api_error = (
        status >= 400
        and "text/html" not in lowered
        and ("json" in lowered or "error" in text.lower())
    )
    assert is_thread or is_api_error, (
        f"POST /api/threads was not a LangGraph route: status={status} type={content_type!r}"
    )
