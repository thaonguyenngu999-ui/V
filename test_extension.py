"""
S Manage - Test Extension Launch
Test browser with fingerprint extension
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Paths
    base_dir = Path(__file__).parent
    browser_path = base_dir / "browser" / "chrome.exe"
    extension_path = base_dir / "extension"
    profiles_dir = base_dir / "profiles" / "profile_test" / "UserData"
    
    # Ensure profile dir exists
    profiles_dir.mkdir(parents=True, exist_ok=True)
    
    if not browser_path.exists():
        print(f"[!] Browser not found: {browser_path}")
        sys.exit(1)
    
    if not extension_path.exists():
        print(f"[!] Extension not found: {extension_path}")
        sys.exit(1)
    
    print(f"[*] Browser: {browser_path}")
    print(f"[*] Extension: {extension_path}")
    print(f"[*] Profile: {profiles_dir}")
    
    # Build command
    args = [
        str(browser_path),
        f"--user-data-dir={profiles_dir}",
        f"--load-extension={extension_path}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-default-apps",
        "--disable-popup-blocking",
        "--disable-translate",
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        # Open test pages
        "https://browserleaks.com/canvas",
        "https://creepjs.com/",
    ]
    
    print(f"\n[>] Launching browser with extension...")
    print(f"    Command: {' '.join(args[:5])}...")
    
    # Launch
    process = subprocess.Popen(args)
    print(f"[+] Browser launched (PID: {process.pid})")
    print(f"\n[*] Check these pages:")
    print(f"    - browserleaks.com/canvas")
    print(f"    - creepjs.com")
    print(f"    - pixelscan.net")
    print(f"\n[*] Open DevTools Console (F12) to see '[S Manage]' messages")
    
    return process

if __name__ == "__main__":
    main()
