"""
S Manage - Browser Launcher với CDP Injection
Inject fingerprint qua Chrome DevTools Protocol (không cần extension)
"""

import subprocess
import socket
import time
import json
import urllib.request
import urllib.parse
import os
import websocket
from pathlib import Path
from typing import Optional, Dict
import threading

from fingerprint_utils import DEFAULT_CHROME_VERSION

DEFAULT_CHROME_MAJOR = DEFAULT_CHROME_VERSION.split('.')[0]


class BrowserLauncher:
    """Launch browser và inject fingerprint qua CDP"""
    
    def __init__(self, browser_path: str):
        self.browser_path = Path(browser_path)
        self.process = None
        self.ws = None
        self.debug_host = "127.0.0.1"
        self.debug_port = None
        self.browser_ws_url = None
        self.injection_ready = threading.Event()
        self.injection_succeeded = False
        self._cdp_id = 0
        self.proxy_auth = None  # (username, password) nếu proxy có auth
        self.pending_start_url = "about:blank"

    def _prepare_user_data_dir(self, user_data_dir: str):
        """Prevent Chrome from restoring stale/crashed tabs on next launch."""
        user_data_path = Path(user_data_dir)
        default_dir = user_data_path / "Default"
        prefs_path = default_dir / "Preferences"
        secure_prefs_path = default_dir / "Secure Preferences"
        sessions_dir = default_dir / "Sessions"

        for path in (prefs_path, secure_prefs_path):
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                profile_block = data.setdefault("profile", {})
                profile_block["exit_type"] = "Normal"
                session_block = data.setdefault("session", {})
                session_block["restore_on_startup"] = 5
                session_block["startup_urls"] = []
                path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            except Exception as exc:
                print(f"[!] Failed to normalize prefs at {path}: {exc}")

        if sessions_dir.exists():
            for child in sessions_dir.iterdir():
                try:
                    if child.is_file():
                        child.unlink()
                except Exception as exc:
                    print(f"[!] Failed to remove session file {child}: {exc}")
        
    def find_free_port(self, host: str = "127.0.0.1") -> int:
        """Tìm port trống"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            return s.getsockname()[1]
    
    def _parse_proxy(self, proxy: str) -> Optional[str]:
        """
        Parse proxy URL và extract auth nếu có
        Input: socks5://user:pass@host:port hoặc http://host:port
        Output: socks5://host:port (auth lưu riêng cho CDP)
        """
        import re
        
        # Pattern: protocol://[user:pass@]host:port
        pattern = r'^(https?|socks[45]?)://(?:([^:@]+):([^@]+)@)?([^:]+):(\d+)$'
        match = re.match(pattern, proxy)
        
        if not match:
            # Thử format đơn giản host:port
            simple_pattern = r'^([^:]+):(\d+)$'
            simple_match = re.match(simple_pattern, proxy)
            if simple_match:
                return f"http://{proxy}"
            print(f"[!] Invalid proxy format: {proxy}")
            return None
        
        protocol, username, password, host, port = match.groups()
        
        # Lưu auth để dùng với CDP
        if username and password:
            self.proxy_auth = (username, password)
            print(f"[>] Proxy auth detected: {username}:****")
        else:
            self.proxy_auth = None
        
        # Return proxy URL không có auth
        return f"{protocol}://{host}:{port}"
    
    def launch(
        self,
        user_data_dir: str,
        fingerprint: Dict,
        proxy: Optional[str] = None,
        start_url: str = "about:blank",
        debug_port: Optional[int] = None,
        debug_host: str = "127.0.0.1",
    ) -> subprocess.Popen:
        """Launch browser với fingerprint injection"""
        
        # Tìm port debug
        self.debug_host = debug_host
        self.debug_port = int(debug_port) if debug_port else self.find_free_port(debug_host)
        self.pending_start_url = start_url or "about:blank"
        self._prepare_user_data_dir(user_data_dir)
        
        # Set environment variables for hardware spoofing
        env = os.environ.copy()
        
        # WebGL GPU
        if fingerprint.get('webgl_vendor'):
            env['SMANAGE_WEBGL_VENDOR'] = fingerprint['webgl_vendor']
            env['ANGLE_GL_VENDOR'] = fingerprint['webgl_vendor']
        if fingerprint.get('webgl_renderer'):
            env['SMANAGE_WEBGL_RENDERER'] = fingerprint['webgl_renderer']
            env['ANGLE_GL_RENDERER'] = fingerprint['webgl_renderer']
        
        # CPU cores
        if fingerprint.get('hardware_concurrency'):
            env['SMANAGE_HARDWARE_CONCURRENCY'] = str(fingerprint['hardware_concurrency'])
        
        # RAM
        if fingerprint.get('device_memory'):
            env['SMANAGE_DEVICE_MEMORY'] = str(fingerprint['device_memory'])
        
        # Platform version (Windows 10 = 10.0.0)
        env['SMANAGE_PLATFORM_VERSION'] = fingerprint.get('platform_version', '10.0.0')
        
        # Build args
        args = [
            str(self.browser_path),
            f"--user-data-dir={user_data_dir}",
            f"--remote-debugging-port={self.debug_port}",
            f"--remote-debugging-address={self.debug_host}",
            "--remote-allow-origins=*",
            # Sandbox disabled for copied browser compatibility
            "--no-sandbox",
            # Session/Tab restore - giữ lại tabs khi đóng mở lại
            # WebRTC IP leak protection
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
            "--webrtc-ip-handling-policy=disable_non_proxied_udp",
            "--disable-features=WebRtcHideLocalIpsWithMdns",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--disable-popup-blocking",
            "--disable-translate",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-client-side-phishing-detection",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-pings",
        ]
        
        # User agent
        if fingerprint.get('user_agent'):
            args.append(f"--user-agent={fingerprint['user_agent']}")

        if fingerprint.get('webgl_vendor'):
            args.append(f"--gpu-gl-vendor={fingerprint['webgl_vendor']}")
        if fingerprint.get('webgl_renderer'):
            args.append(f"--gpu-gl-renderer={fingerprint['webgl_renderer']}")
        
        # Window size
        width = fingerprint.get('screen_width', 1920)
        height = fingerprint.get('screen_height', 1080)
        args.append(f"--window-size={width},{height}")
        
        # Language
        lang = fingerprint.get('language', 'en-US')
        args.append(f"--lang={lang.split(',')[0]}")
        
        # Proxy - parse và xử lý auth riêng
        if proxy:
            proxy_server = self._parse_proxy(proxy)
            if proxy_server:
                args.append(f"--proxy-server={proxy_server}")
                print(f"[>] Proxy: {proxy_server}")
        
        # Start with about:blank so proxy auth and fingerprint hooks are ready
        # before the first real network request is made.
        args.append("about:blank")
        
        print(f"[>] Launching browser on debug port {self.debug_port}...")
        print(f"[>] Browser: {self.browser_path}")
        print(f"[>] User data: {user_data_dir}")
        if fingerprint.get('webgl_renderer'):
            print(f"[>] WebGL GPU: {fingerprint['webgl_renderer'][:50]}...")
        
        # Launch browser with custom environment
        try:
            # Don't capture stdout/stderr - it can block the browser
            self.process = subprocess.Popen(args, env=env)
            print(f"[+] Browser process started, PID: {self.process.pid}")
                
        except Exception as e:
            print(f"[!] Failed to launch browser: {e}")
            import traceback
            traceback.print_exc()
            return None
        
        # Wait và inject
        self.injection_ready.clear()
        self.injection_succeeded = False
        threading.Thread(target=self._inject_fingerprint, args=(fingerprint,), daemon=True).start()
        self.injection_ready.wait(timeout=5.0)
        
        return self.process
    
    def _inject_fingerprint(self, fingerprint: Dict):
        """Inject fingerprint script qua CDP"""
        time.sleep(2)  # Đợi browser khởi động
        
        try:
            # Kết nối WebSocket CDP
            ws_url = self._get_ws_url()
            if not ws_url:
                print("[!] Could not get CDP WebSocket URL")
                return
            
            self.ws = websocket.create_connection(ws_url)
            
            # Enable domains and apply emulation before script injection
            self._send_cdp({"method": "Page.enable"})
            self._send_cdp({"method": "Runtime.enable"})
            self._send_cdp({"method": "Network.enable"})
            self._apply_emulation(fingerprint)
            
            # Nếu có proxy auth, set up handler
            if self.proxy_auth:
                self._setup_proxy_auth()
            
            # Tạo script injection
            script = self._build_injection_script(fingerprint)
            
            # Dùng Page.addScriptToEvaluateOnNewDocument để inject vào mọi page
            self._send_cdp({
                "method": "Page.addScriptToEvaluateOnNewDocument",
                "params": {
                    "source": script
                }
            })
            
            print("[+] Fingerprint injection active via CDP")
            self.injection_succeeded = True

            # Listen for proxy auth requests before the first navigation.
            if self.proxy_auth:
                self._listen_for_auth_requests()

            if (
                fingerprint.get("geo_latitude") is not None
                and fingerprint.get("geo_longitude") is not None
                and self.pending_start_url
                and self.pending_start_url != "about:blank"
            ):
                try:
                    parsed = urllib.parse.urlsplit(self.pending_start_url)
                    if parsed.scheme and parsed.netloc:
                        origin = f"{parsed.scheme}://{parsed.netloc}"
                        self._send_cdp({
                            "method": "Browser.grantPermissions",
                            "params": {
                                "origin": origin,
                                "permissions": ["geolocation"],
                            },
                        })
                except Exception:
                    pass

            if self.pending_start_url and self.pending_start_url != "about:blank":
                self._send_cdp_async({
                    "method": "Page.navigate",
                    "params": {"url": self.pending_start_url},
                })
            else:
                self._send_cdp_async({"method": "Page.reload"})
            
        except Exception as e:
            print(f"[!] CDP injection error: {e}")
        finally:
            self.injection_ready.set()
    
    def _setup_proxy_auth(self):
        """Set up proxy authentication via CDP Fetch domain"""
        try:
            # Enable Fetch domain để intercept auth requests
            self._send_cdp({
                "method": "Fetch.enable",
                "params": {
                    "handleAuthRequests": True
                }
            })
            print("[+] Proxy auth handler enabled")
        except Exception as e:
            print(f"[!] Failed to setup proxy auth: {e}")
    
    def _listen_for_auth_requests(self):
        """Listen và respond to proxy authentication requests"""
        def auth_listener():
            try:
                while self.ws and self.process and self.process.poll() is None:
                    try:
                        self.ws.settimeout(1.0)
                        msg = self.ws.recv()
                        data = json.loads(msg)
                        
                        # Handle auth required event
                        if data.get("method") == "Fetch.authRequired":
                            request_id = data["params"]["requestId"]
                            auth_challenge = data["params"].get("authChallenge", {})
                            
                            print(f"[>] Proxy auth required: {auth_challenge.get('origin', 'unknown')}")
                            
                            if self.proxy_auth:
                                username, password = self.proxy_auth
                                # Respond với credentials
                                self._send_cdp_async({
                                    "method": "Fetch.continueWithAuth",
                                    "params": {
                                        "requestId": request_id,
                                        "authChallengeResponse": {
                                            "response": "ProvideCredentials",
                                            "username": username,
                                            "password": password
                                        }
                                    }
                                })
                                print("[+] Proxy auth credentials provided")
                        
                        # Handle request paused (continue normally)
                        elif data.get("method") == "Fetch.requestPaused":
                            request_id = data["params"]["requestId"]
                            self._send_cdp_async({
                                "method": "Fetch.continueRequest",
                                "params": {"requestId": request_id}
                            })
                            
                    except websocket.WebSocketTimeoutException:
                        continue
                    except Exception as e:
                        if "closed" not in str(e).lower():
                            print(f"[!] Auth listener error: {e}")
                        break
            except Exception as e:
                print(f"[!] Auth listener thread error: {e}")
        
        threading.Thread(target=auth_listener, daemon=True).start()
    
    def _send_cdp_async(self, message: Dict):
        """Gửi CDP command không đợi response"""
        try:
            self._cdp_id += 1
            message['id'] = self._cdp_id
            self.ws.send(json.dumps(message))
        except:
            pass

    def get_cdp_http_url(self) -> Optional[str]:
        """Return the HTTP CDP endpoint used by Playwright connect_over_cdp"""
        if self.debug_port is None:
            return None
        return f"http://{self.debug_host}:{self.debug_port}"

    def _read_debugger_json(self, path: str):
        url = f"{self.get_cdp_http_url()}{path}"
        with urllib.request.urlopen(url, timeout=2) as resp:
            return json.loads(resp.read())

    def wait_for_debugging_endpoint(self, timeout_seconds: float = 15.0) -> Optional[Dict]:
        """Wait until the browser-level CDP endpoint is ready"""
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            if self.process and self.process.poll() is not None:
                return None

            try:
                data = self._read_debugger_json("/json/version")
                self.browser_ws_url = data.get('webSocketDebuggerUrl')
                return {
                    'debug_port': self.debug_port,
                    'cdp_endpoint': self.get_cdp_http_url(),
                    'browser_ws_url': self.browser_ws_url,
                    'browser_version': data.get('Browser'),
                    'user_agent': data.get('User-Agent'),
                }
            except Exception:
                time.sleep(0.25)
    
    def _get_ws_url(self) -> Optional[str]:
        for _ in range(10):
            try:
                data = self._read_debugger_json("/json")
                if data:
                    for target in data:
                        if target.get('type') == 'page' and target.get('webSocketDebuggerUrl'):
                            return target.get('webSocketDebuggerUrl')
                    return data[0].get('webSocketDebuggerUrl')
            except Exception:
                time.sleep(0.5)

        return None
        """Lấy WebSocket URL từ CDP"""
        import urllib.request
        
        for _ in range(10):  # Retry 10 lần
            try:
                url = f"http://127.0.0.1:{self.debug_port}/json"
                with urllib.request.urlopen(url, timeout=2) as resp:
                    data = json.loads(resp.read())
                    if data:
                        return data[0].get('webSocketDebuggerUrl')
            except:
                time.sleep(0.5)
        
        return None
    
    def _send_cdp(self, message: Dict) -> Dict:
        """Gửi command qua CDP"""
        self._cdp_id += 1
        message['id'] = self._cdp_id
        self.ws.send(json.dumps(message))
        while True:
            payload = json.loads(self.ws.recv())
            if payload.get('id') == message['id']:
                return payload

    def _apply_emulation(self, fingerprint: Dict):
        """Apply CDP-level emulation so runtime values stay aligned."""
        width = int(fingerprint.get('screen_width', 1920))
        height = int(fingerprint.get('screen_height', 1080))
        language = fingerprint.get('language', 'en-US')
        timezone = fingerprint.get('timezone', 'Asia/Ho_Chi_Minh')
        geo_latitude = fingerprint.get('geo_latitude')
        geo_longitude = fingerprint.get('geo_longitude')
        geo_accuracy = fingerprint.get('geo_accuracy', 20)
        user_agent = fingerprint.get('user_agent')
        platform = fingerprint.get('platform', 'Win32')
        chrome_major = fingerprint.get('chrome_major', DEFAULT_CHROME_MAJOR)
        chrome_version = fingerprint.get('chrome_version', DEFAULT_CHROME_VERSION)
        platform_version = fingerprint.get('platform_version', '10.0.0')

        commands = [
            (
                "Emulation.setDeviceMetricsOverride",
                {
                    "width": width,
                    "height": height,
                    "deviceScaleFactor": 1,
                    "mobile": False,
                    "screenWidth": width,
                    "screenHeight": height,
                    "positionX": 0,
                    "positionY": 0,
                    "scale": 1,
                },
            ),
            ("Emulation.setTimezoneOverride", {"timezoneId": timezone}),
            ("Emulation.setLocaleOverride", {"locale": language}),
        ]

        for method, params in commands:
            try:
                self._send_cdp({"method": method, "params": params})
            except Exception:
                pass

        if geo_latitude is not None and geo_longitude is not None:
            try:
                self._send_cdp({
                    "method": "Emulation.setGeolocationOverride",
                    "params": {
                        "latitude": float(geo_latitude),
                        "longitude": float(geo_longitude),
                        "accuracy": float(geo_accuracy or 20),
                    },
                })
            except Exception:
                pass

        if user_agent:
            try:
                self._send_cdp({
                    "method": "Emulation.setUserAgentOverride",
                    "params": {
                        "userAgent": user_agent,
                        "acceptLanguage": language,
                        "platform": platform,
                        "userAgentMetadata": {
                            "brands": [
                                {"brand": "Chromium", "version": chrome_major},
                                {"brand": "Google Chrome", "version": chrome_major},
                                {"brand": "Not_A Brand", "version": "24"},
                            ],
                            "fullVersionList": [
                                {"brand": "Chromium", "version": chrome_version},
                                {"brand": "Google Chrome", "version": chrome_version},
                                {"brand": "Not_A Brand", "version": "24.0.0.0"},
                            ],
                            "fullVersion": chrome_version,
                            "platform": "Windows",
                            "platformVersion": platform_version,
                            "architecture": "x86",
                            "model": "",
                            "mobile": False,
                            "bitness": "64",
                            "wow64": False,
                        },
                    },
                })
            except Exception:
                pass
    
    def _build_injection_script(self, fp: Dict) -> str:
        """Build JavaScript injection script với anti-detection"""
        
        screen_width = fp.get('screen_width', 1920)
        screen_height = fp.get('screen_height', 1080)
        platform = fp.get('platform', 'Win32')
        language = fp.get('language', 'en-US')
        languages = fp.get('languages', ['en-US', 'en'])
        hardware_concurrency = fp.get('hardware_concurrency', 8)
        device_memory = fp.get('device_memory', 8)
        timezone = fp.get('timezone', 'Asia/Ho_Chi_Minh')
        geo_latitude = fp.get('geo_latitude')
        geo_longitude = fp.get('geo_longitude')
        geo_accuracy = fp.get('geo_accuracy', 20)
        chrome_major = fp.get('chrome_major', DEFAULT_CHROME_MAJOR)
        chrome_version = fp.get('chrome_version', DEFAULT_CHROME_VERSION)
        platform_version = fp.get('platform_version', '10.0.0')
        timezone_offset = fp.get('timezone_offset', -420)
        webgl_vendor = fp.get('webgl_vendor', 'Google Inc. (NVIDIA)')
        webgl_renderer = fp.get('webgl_renderer', 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650)')
        avail_height = max(int(screen_height) - 40, 0)
        
        return f'''
(function() {{
    'use strict';
    
    // ========== ANTI-DETECTION UTILS ==========
    // Native function string để bypass detection
    const nativeToString = Function.prototype.toString;
    const fakeNative = (fn, name) => {{
        const native = `function ${{name}}() {{ [native code] }}`;
        Object.defineProperty(fn, 'toString', {{
            value: () => native,
            writable: false,
            enumerable: false,
            configurable: false
        }});
        if (fn.prototype) {{
            Object.defineProperty(fn.prototype.constructor, 'toString', {{
                value: () => native,
                writable: false
            }});
        }}
        return fn;
    }};
    
    // Stealth defineProperty - match native descriptors exactly
    const stealthDefine = (obj, prop, value, opts = {{}}) => {{
        const descriptor = {{
            get: fakeNative(() => value, `get ${{prop}}`),
            set: undefined,
            enumerable: opts.enumerable !== false,
            configurable: opts.configurable !== false
        }};
        Object.defineProperty(obj, prop, descriptor);
    }};
    
    const primaryLanguage = {json.dumps(language)};
    const languageList = Object.freeze({json.dumps(languages)});
    const screenWidth = {int(screen_width)};
    const screenHeight = {int(screen_height)};
    const availHeight = {int(avail_height)};
    const deviceMemoryValue = {json.dumps(device_memory)};
    const timezoneValue = {json.dumps(timezone)};
    const timezoneOffsetValue = {int(timezone_offset)};
    const geoLatitudeValue = {json.dumps(geo_latitude)};
    const geoLongitudeValue = {json.dumps(geo_longitude)};
    const geoAccuracyValue = {json.dumps(geo_accuracy)};
    const hasGeolocationValue = geoLatitudeValue !== null && geoLongitudeValue !== null;

    // ========== SCREEN ==========
    const screenProto = Object.getPrototypeOf(window.screen);
    const spoofScreen = (prop, value) => {{
        try {{
            Object.defineProperty(window.screen, prop, {{
                get: fakeNative(() => value, `get ${{prop}}`),
                enumerable: true,
                configurable: true
            }});
        }} catch(e) {{}}
        try {{
            Object.defineProperty(screenProto, prop, {{
                get: fakeNative(() => value, `get ${{prop}}`),
                enumerable: true,
                configurable: true
            }});
        }} catch(e) {{}}
    }};

    spoofScreen('width', screenWidth);
    spoofScreen('height', screenHeight);
    spoofScreen('availWidth', screenWidth);
    spoofScreen('availHeight', availHeight);
    spoofScreen('colorDepth', 24);
    spoofScreen('pixelDepth', 24);

    const spoofWindowValue = (prop, value) => {{
        try {{
            Object.defineProperty(window, prop, {{
                get: fakeNative(() => value, `get ${{prop}}`),
                enumerable: true,
                configurable: true
            }});
        }} catch(e) {{}}
    }};

    spoofWindowValue('innerWidth', screenWidth);
    spoofWindowValue('outerWidth', screenWidth);
    spoofWindowValue('innerHeight', availHeight);
    spoofWindowValue('outerHeight', screenHeight);
    spoofWindowValue('devicePixelRatio', 1);
    
    // ========== NAVIGATOR PROTECTION ==========
    // Protect against property descriptor checks
    const navigatorProto = Object.getPrototypeOf(navigator);
    
    // Spoof with native-like getters that can't be detected
    const spoofNavigator = (prop, val) => {{
        const getter = fakeNative(() => val, `get ${{prop}}`);
        try {{
            Object.defineProperty(navigator, prop, {{
                get: getter,
                enumerable: true,
                configurable: true
            }});
        }} catch(e) {{}}
        try {{
            Object.defineProperty(navigatorProto, prop, {{
                get: getter,
                enumerable: true,
                configurable: true
            }});
        }} catch(e) {{}}
    }};
    
    spoofNavigator('platform', '{platform}');
    spoofNavigator('language', primaryLanguage);
    spoofNavigator('languages', languageList);
    spoofNavigator('hardwareConcurrency', {hardware_concurrency});
    spoofNavigator('deviceMemory', deviceMemoryValue);
    spoofNavigator('maxTouchPoints', 0);
    
    // Hide webdriver - critical for antibot
    try {{
        Object.defineProperty(navigatorProto, 'webdriver', {{
            get: fakeNative(() => undefined, 'get webdriver'),
            enumerable: true,
            configurable: true
        }});
    }} catch(e) {{}}
    
    // ========== USER AGENT DATA ==========
    if (navigator.userAgentData) {{
        const uaDataProto = typeof NavigatorUAData !== 'undefined' ? NavigatorUAData.prototype : Object.prototype;
        const fakeUAData = Object.create(uaDataProto);
        Object.defineProperties(fakeUAData, {{
            brands: {{
                get: fakeNative(() => Object.freeze([
                    Object.freeze({{ brand: "Chromium", version: "{chrome_major}" }}),
                    Object.freeze({{ brand: "Google Chrome", version: "{chrome_major}" }}),
                    Object.freeze({{ brand: "Not_A Brand", version: "24" }})
                ]), 'get brands'),
                enumerable: true
            }},
            mobile: {{
                get: fakeNative(() => false, 'get mobile'),
                enumerable: true
            }},
            platform: {{
                get: fakeNative(() => "Windows", 'get platform'),
                enumerable: true
            }}
        }});
        
        fakeUAData.getHighEntropyValues = fakeNative(async function(hints) {{
            const result = {{
                brands: this.brands,
                mobile: this.mobile,
                platform: this.platform
            }};
            if (hints.includes('platformVersion')) result.platformVersion = "{platform_version}";
            if (hints.includes('architecture')) result.architecture = "x86";
            if (hints.includes('model')) result.model = "";
            if (hints.includes('bitness')) result.bitness = "64";
            if (hints.includes('fullVersionList')) result.fullVersionList = this.brands;
            if (hints.includes('uaFullVersion')) result.uaFullVersion = "{chrome_version}";
            return result;
        }}, 'getHighEntropyValues');
        
        fakeUAData.toJSON = fakeNative(function() {{
            return {{ brands: this.brands, mobile: this.mobile, platform: this.platform }};
        }}, 'toJSON');
        
        Object.defineProperty(navigatorProto, 'userAgentData', {{
            get: fakeNative(() => fakeUAData, 'get userAgentData'),
            enumerable: true,
            configurable: true
        }});
    }}
    
    // ========== WEBRTC PROTECTION ==========
    if (window.RTCPeerConnection) {{
        const OrigRTC = window.RTCPeerConnection;
        const FakeRTC = function(config, constraints) {{
            config = config || {{}};
            config.iceServers = [];
            const pc = new OrigRTC(config, constraints);
            return pc;
        }};
        FakeRTC.prototype = OrigRTC.prototype;
        Object.defineProperty(FakeRTC, 'name', {{ value: 'RTCPeerConnection' }});
        fakeNative(FakeRTC, 'RTCPeerConnection');
        window.RTCPeerConnection = FakeRTC;
    }}
    
    if (window.webkitRTCPeerConnection) {{
        const OrigWebkitRTC = window.webkitRTCPeerConnection;
        const FakeWebkitRTC = function(config, constraints) {{
            config = config || {{}};
            config.iceServers = [];
            return new OrigWebkitRTC(config, constraints);
        }};
        FakeWebkitRTC.prototype = OrigWebkitRTC.prototype;
        fakeNative(FakeWebkitRTC, 'webkitRTCPeerConnection');
        window.webkitRTCPeerConnection = FakeWebkitRTC;
    }}
    
    // ========== TIMEZONE ==========
    const origGetTimezoneOffset = Date.prototype.getTimezoneOffset;
    Date.prototype.getTimezoneOffset = fakeNative(function() {{
        return timezoneOffsetValue;
    }}, 'getTimezoneOffset');
    
    const OrigDateTimeFormat = Intl.DateTimeFormat;
    const FakeDateTimeFormat = function(locales, options) {{
        options = Object.assign({{}}, options);
        if (!options.timeZone) options.timeZone = timezoneValue;
        return new OrigDateTimeFormat(locales, options);
    }};
    FakeDateTimeFormat.prototype = OrigDateTimeFormat.prototype;
    FakeDateTimeFormat.supportedLocalesOf = OrigDateTimeFormat.supportedLocalesOf;
    fakeNative(FakeDateTimeFormat, 'DateTimeFormat');
    Intl.DateTimeFormat = FakeDateTimeFormat;

    const origResolvedOptions = OrigDateTimeFormat.prototype.resolvedOptions;
    OrigDateTimeFormat.prototype.resolvedOptions = fakeNative(function() {{
        const options = origResolvedOptions.call(this);
        options.timeZone = timezoneValue;
        options.locale = primaryLanguage;
        return options;
    }}, 'resolvedOptions');

    // ========== GEOLOCATION ==========
    try {{
        const geolocationPayload = {{
            coords: {{
                latitude: hasGeolocationValue ? Number(geoLatitudeValue) : 0,
                longitude: hasGeolocationValue ? Number(geoLongitudeValue) : 0,
                accuracy: Number(geoAccuracyValue || 20),
                altitude: null,
                altitudeAccuracy: null,
                heading: null,
                speed: null,
            }},
            timestamp: Date.now(),
        }};

        const geolocationProto = navigator.geolocation && Object.getPrototypeOf(navigator.geolocation);
        if (geolocationProto && hasGeolocationValue) {{
            const successCall = (success) => {{
                if (typeof success === 'function') {{
                    setTimeout(() => success(geolocationPayload), 0);
                }}
            }};

            Object.defineProperty(geolocationProto, 'getCurrentPosition', {{
                value: fakeNative(function(success, error) {{
                    successCall(success);
                }}, 'getCurrentPosition'),
                configurable: true,
                writable: false
            }});

            Object.defineProperty(geolocationProto, 'watchPosition', {{
                value: fakeNative(function(success, error) {{
                    successCall(success);
                    return 1;
                }}, 'watchPosition'),
                configurable: true,
                writable: false
            }});

            Object.defineProperty(geolocationProto, 'clearWatch', {{
                value: fakeNative(function() {{}}, 'clearWatch'),
                configurable: true,
                writable: false
            }});
        }}

        if (navigator.permissions && navigator.permissions.query && hasGeolocationValue) {{
            const originalQuery = navigator.permissions.query.bind(navigator.permissions);
            navigator.permissions.query = fakeNative(function(parameters) {{
                if (parameters && parameters.name === 'geolocation') {{
                    return Promise.resolve({{
                        state: 'granted',
                        onchange: null
                    }});
                }}
                return originalQuery(parameters);
            }}, 'query');
        }}
    }} catch (e) {{}}
    
    // ========== WEBGL - native spoofed via ANGLE env vars ==========
    // Backup JS hook in case env vars not working
    const VENDOR_WEBGL = 37445;
    const RENDERER_WEBGL = 37446;
    const webglVendor = '{webgl_vendor}';
    const webglRenderer = '{webgl_renderer}';
    
    const hookWebGL = (proto) => {{
        if (!proto || !proto.getParameter) return;
        const origGetParam = proto.getParameter;
        proto.getParameter = fakeNative(function(param) {{
            if (param === VENDOR_WEBGL || param === 0x1F00) return webglVendor;
            if (param === RENDERER_WEBGL || param === 0x1F01) return webglRenderer;
            return origGetParam.call(this, param);
        }}, 'getParameter');
    }};
    
    hookWebGL(WebGLRenderingContext.prototype);
    if (typeof WebGL2RenderingContext !== 'undefined') {{
        hookWebGL(WebGL2RenderingContext.prototype);
    }}
    
    // ========== CANVAS FINGERPRINT NOISE ==========
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    const origGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    
    // Consistent noise based on canvas content hash
    const getNoiseValue = (width, height, idx) => {{
        const hash = (width * 31 + height * 17 + idx) % 256;
        return hash < 128 ? -1 : 1;
    }};
    
    const addNoise = (imageData, width, height) => {{
        for (let i = 0; i < imageData.data.length; i += 4) {{
            if (Math.random() < 0.0005) {{
                const noise = getNoiseValue(width, height, i);
                imageData.data[i] = Math.max(0, Math.min(255, imageData.data[i] + noise));
            }}
        }}
        return imageData;
    }};
    
    CanvasRenderingContext2D.prototype.getImageData = fakeNative(function(x, y, w, h) {{
        const imageData = origGetImageData.call(this, x, y, w, h);
        if (w < 500 && h < 300) {{
            addNoise(imageData, w, h);
        }}
        return imageData;
    }}, 'getImageData');
    
    HTMLCanvasElement.prototype.toDataURL = fakeNative(function(type, quality) {{
        if (this.width < 500 && this.height < 300) {{
            const ctx = this.getContext('2d');
            if (ctx && ctx.getImageData) {{
                try {{
                    const imageData = origGetImageData.call(ctx, 0, 0, this.width, this.height);
                    addNoise(imageData, this.width, this.height);
                    ctx.putImageData(imageData, 0, 0);
                }} catch(e) {{}}
            }}
        }}
        return origToDataURL.call(this, type, quality);
    }}, 'toDataURL');
    
    // ========== AUDIO FINGERPRINT PROTECTION ==========
    if (window.AudioContext || window.webkitAudioContext) {{
        const OrigAudioContext = window.AudioContext || window.webkitAudioContext;
        const origCreateAnalyser = OrigAudioContext.prototype.createAnalyser;
        const origCreateOscillator = OrigAudioContext.prototype.createOscillator;
        const origCreateDynamicsCompressor = OrigAudioContext.prototype.createDynamicsCompressor;
        
        // Add tiny noise to audio analysis
        if (typeof AnalyserNode !== 'undefined' && AnalyserNode.prototype.getFloatFrequencyData) {{
            const origGetFloatFreq = AnalyserNode.prototype.getFloatFrequencyData;
            AnalyserNode.prototype.getFloatFrequencyData = fakeNative(function(array) {{
                origGetFloatFreq.call(this, array);
                for (let i = 0; i < array.length; i++) {{
                    array[i] += (Math.random() - 0.5) * 0.0001;
                }}
            }}, 'getFloatFrequencyData');
        }}
    }}
    
    // ========== PLUGINS CONSISTENCY ==========
    // Ensure plugins array looks natural (already populated by Chrome)
    
    // ========== PERFORMANCE PROTECTION ==========
    // Prevent timing attacks that detect spoofing
    const origNow = Performance.prototype.now;
    Performance.prototype.now = fakeNative(function() {{
        return Math.floor(origNow.call(this) * 1000) / 1000;
    }}, 'now');

    const applyDocumentLanguage = () => {{
        try {{
            if (document.documentElement) {{
                document.documentElement.lang = primaryLanguage;
            }}
        }} catch(e) {{}}
    }};
    applyDocumentLanguage();
    document.addEventListener('DOMContentLoaded', applyDocumentLanguage, {{ once: true }});
    
    console.log('[S Manage] Fingerprint protection active (stealth mode)');
}})();
'''


# Test
if __name__ == "__main__":
    import sys
    
    browser_path = Path(__file__).parent.parent / "browser" / "chrome.exe"
    user_data = Path(__file__).parent.parent / "profiles" / "profile_cdp_test" / "UserData"
    user_data.mkdir(parents=True, exist_ok=True)
    
    fingerprint = {
        'screen_width': 1920,
        'screen_height': 1080,
        'platform': 'Win32',
        'language': 'en-US',
        'languages': ['en-US', 'en'],
        'hardware_concurrency': 8,
        'device_memory': 8,
        'timezone': 'America/New_York',
        'timezone_offset': 300,
        'webgl_vendor': 'Google Inc. (NVIDIA)',
        'webgl_renderer': 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
        'user_agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{DEFAULT_CHROME_VERSION} Safari/537.36'
    }
    
    launcher = BrowserLauncher(str(browser_path))
    launcher.launch(str(user_data), fingerprint, start_url="https://pixelscan.net")
    
    print("[*] Browser launched. Check DevTools console for '[S Manage]' message.")
    print("[*] Test at: pixelscan.net, browserleaks.com, creepjs.com")
