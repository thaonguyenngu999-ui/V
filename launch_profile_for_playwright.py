"""
Launch a saved S Manage profile and print the CDP endpoint for Playwright.
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

from profiles import ProfileManager  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch a profile and expose its CDP endpoint for Playwright."
    )
    parser.add_argument(
        "--config",
        default=str(ROOT / "config.json"),
        help="Path to the S Manage config.json file.",
    )
    parser.add_argument(
        "--profile",
        help="Profile id or exact profile name.",
    )
    parser.add_argument(
        "--start-url",
        default="about:blank",
        help="Initial URL to open in the launched browser.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Seconds to wait for the CDP endpoint.",
    )
    parser.add_argument(
        "--debug-port",
        type=int,
        help="Preferred remote debugging port. If omitted, a free local port is used.",
    )
    parser.add_argument(
        "--debug-host",
        default="127.0.0.1",
        help="Remote debugging bind address. Default is 127.0.0.1.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the launch result as JSON.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait until the browser process exits.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List profiles from the selected config and exit.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manager = ProfileManager(args.config)

    if args.list:
        for profile in manager.list_profiles():
            print(f"{profile.id}\t{profile.name}")
        return 0

    if not args.profile:
        print("[!] --profile is required unless --list is used", file=sys.stderr)
        return 1

    profile = manager.find_profile(args.profile)
    if not profile:
        print(f"[!] Profile not found: {args.profile}", file=sys.stderr)
        return 1

    launch = manager.launch_profile_for_playwright(
        profile.id,
        start_url=args.start_url,
        timeout_seconds=args.timeout,
        debug_port=args.debug_port,
        debug_host=args.debug_host,
    )
    if not launch or not launch.get("process"):
        print(f"[!] Failed to launch profile: {profile.id}", file=sys.stderr)
        return 1

    payload = {
        "profile_id": profile.id,
        "profile_name": profile.name,
        "debug_host": args.debug_host,
        "debug_port": launch.get("debug_port"),
        "cdp_endpoint": launch.get("cdp_endpoint"),
        "browser_ws_url": launch.get("browser_ws_url"),
        "browser_version": launch.get("browser_version"),
        "user_agent": launch.get("user_agent"),
        "pid": launch["process"].pid,
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"PROFILE_ID={payload['profile_id']}")
        print(f"PROFILE_NAME={payload['profile_name']}")
        print(f"PID={payload['pid']}")
        print(f"DEBUG_HOST={payload['debug_host']}")
        print(f"DEBUG_PORT={payload['debug_port']}")
        print(f"CDP_ENDPOINT={payload['cdp_endpoint']}")
        if payload.get("browser_ws_url"):
            print(f"BROWSER_WS_URL={payload['browser_ws_url']}")
        if payload.get("browser_version"):
            print(f"BROWSER_VERSION={payload['browser_version']}")

    if args.wait:
        try:
            launch["process"].wait()
        except KeyboardInterrupt:
            return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
