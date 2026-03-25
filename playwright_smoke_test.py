"""
Sample Playwright smoke test for the S Manage CDP port.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANAGER_DIR = ROOT / "manager"
if str(MANAGER_DIR) not in sys.path:
    sys.path.insert(0, str(MANAGER_DIR))

from playwright_attach import attach_to_debug_port, connect_over_cdp, first_page  # noqa: E402


SMOKE_TEST_URL = (
    "data:text/html,"
    "<title>S Manage Playwright Smoke Test</title>"
    "<h1>playwright_cdp_ok</h1>"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Attach Playwright to an S Manage CDP endpoint and validate the connection."
    )
    parser.add_argument("--cdp-url", help="HTTP CDP endpoint, for example http://127.0.0.1:9222")
    parser.add_argument("--debug-port", type=int, help="Debug port to wait for and attach to")
    parser.add_argument(
        "--debug-host",
        default="127.0.0.1",
        help="Host to use with --debug-port. Default is 127.0.0.1.",
    )
    parser.add_argument(
        "--url",
        default=SMOKE_TEST_URL,
        help="URL to load after attaching. Defaults to a local data: URL.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.cdp_url and not args.debug_port:
        print("[!] Provide --cdp-url or --debug-port", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] Playwright is not installed. Run: pip install playwright", file=sys.stderr)
        return 1

    with sync_playwright() as playwright:
        if args.cdp_url:
            browser = connect_over_cdp(playwright, args.cdp_url)
            endpoint = args.cdp_url
        else:
            endpoint = f"http://{args.debug_host}:{args.debug_port}"
            browser = attach_to_debug_port(playwright, args.debug_port, host=args.debug_host)

        page = first_page(browser)
        page.goto(args.url, wait_until="load")

        fingerprint = page.evaluate(
            """() => {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                let vendor = null;
                let renderer = null;
                if (gl) {
                    const ext = gl.getExtension('WEBGL_debug_renderer_info');
                    if (ext) {
                        vendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
                        renderer = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
                    } else {
                        vendor = gl.getParameter(37445);
                        renderer = gl.getParameter(37446);
                    }
                }

                return {
                    userAgent: navigator.userAgent,
                    hardwareConcurrency: navigator.hardwareConcurrency,
                    deviceMemory: navigator.deviceMemory,
                    language: navigator.language,
                    languages: navigator.languages,
                    webglVendor: vendor,
                    webglRenderer: renderer,
                    title: document.title,
                    url: location.href
                };
            }"""
        )

        print(f"ATTACHED_CDP={endpoint}")
        print(json.dumps(fingerprint, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
