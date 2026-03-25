"""
Helpers for attaching Playwright to a launched Chromium CDP port.
"""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Optional


def cdp_http_url(debug_port: int, host: str = "127.0.0.1") -> str:
    return f"http://{host}:{int(debug_port)}"


def wait_for_cdp_http_url(
    debug_port: int,
    host: str = "127.0.0.1",
    timeout_seconds: float = 15.0,
) -> str:
    endpoint = cdp_http_url(debug_port, host=host)
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{endpoint}/json/version", timeout=2) as resp:
                payload = json.loads(resp.read())
                if payload.get("webSocketDebuggerUrl"):
                    return endpoint
        except Exception:
            time.sleep(0.25)

    raise TimeoutError(f"CDP endpoint not ready after {timeout_seconds:.1f}s: {endpoint}")


def connect_over_cdp(playwright, endpoint_url: str):
    return playwright.chromium.connect_over_cdp(endpoint_url)


def attach_to_debug_port(
    playwright,
    debug_port: int,
    host: str = "127.0.0.1",
    timeout_seconds: float = 15.0,
):
    endpoint = wait_for_cdp_http_url(debug_port, host=host, timeout_seconds=timeout_seconds)
    return connect_over_cdp(playwright, endpoint)


def first_context(browser):
    if not browser.contexts:
        raise RuntimeError(
            "No browser contexts exposed over CDP. Launch the browser with a persistent user data dir."
        )
    return browser.contexts[0]


def first_page(browser):
    context = first_context(browser)
    if context.pages:
        return context.pages[0]
    return context.new_page()
