"""
Test fingerprint with full CDP injection
"""
import sys
sys.path.insert(0, 'F:\\ChromiumSoncuto\\manager')

from browser_launcher import BrowserLauncher

# Test fingerprint - consistent Windows 10 profile
fingerprint = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.139 Safari/537.36",
    "chrome_version": "131.0.6778.139",
    "chrome_major": "131",
    "platform_version": "10.0.0",  # Windows 10 (not 11!)
    "screen_width": 1920,
    "screen_height": 1080,
    "timezone": "America/New_York",
    "timezone_offset": 300,
    "language": "en-US",
    "platform": "Win32",
    "webgl_vendor": "Google Inc. (AMD)",
    "webgl_renderer": "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "hardware_concurrency": 8,
    "device_memory": 16,
}

browser_path = r"F:\ChromiumSoncuto\browser\chrome.exe"
user_data_dir = r"F:\ChromiumSoncuto\profiles\profile_FAKE_AMD\UserData"

launcher = BrowserLauncher(browser_path)
process = launcher.launch(
    user_data_dir=user_data_dir,
    fingerprint=fingerprint,
    start_url="https://abrahamjuliot.github.io/creepjs/"
)

print(f"[+] Browser launched with PID: {process.pid}")
print(f"[+] Debug port: {launcher.debug_port}")
print("[+] CDP injection will run in background...")
print("[+] Wait for page to load and check fingerprint values")

# Keep script running
try:
    process.wait()
except KeyboardInterrupt:
    print("[!] Stopping...")
