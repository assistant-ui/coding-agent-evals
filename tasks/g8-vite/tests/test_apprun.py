from __future__ import annotations

import os
import urllib.error
import urllib.request


def test_ar_04_vite_html_not_next() -> None:
    """AR-04 GET / is a Vite app, not Next.js."""
    base = os.environ.get("BASE_URL", "http://127.0.0.1:3000").rstrip("/")
    request = urllib.request.Request(f"{base}/", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            body = response.read(8000)
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read(8000) if error.fp else b""

    assert status == 200
    text = body.decode("utf-8", errors="replace")
    assert "_next/static" not in text, f"GET / looked like Next.js: {text[:200]!r}"
