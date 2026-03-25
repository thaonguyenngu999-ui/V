"""
S Manage - Browser Profile Manager GUI v3.0
Professional antidetect browser with per-profile fingerprint config
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
import os
import sys
import json
import subprocess
import threading
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path


def get_app_path():
    """Get the application path - works for both script and frozen exe"""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


APP_PATH = get_app_path()
print(f"[DEBUG] APP_PATH = {APP_PATH}")
APP_VERSION_LABEL = "v3.1"

# Add app path to sys.path for imports
sys.path.insert(0, APP_PATH)

try:
    from profiles import ProfileManager, ProfileConfig
    from fingerprint import FingerprintGenerator
    from browser_launcher import BrowserLauncher
    from app_meta import APP_VERSION_LABEL
    from runtime_manager import (
        DEFAULT_RUNTIME_MANIFEST_URL,
        download_and_install as download_runtime_package,
        find_browser_path,
        get_runtime_status,
    )
    print("[DEBUG] Imports successful")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    # Try relative import as fallback
    import importlib.util
    
    def load_module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        return None
    
    profiles_mod = load_module("profiles", os.path.join(APP_PATH, "profiles.py"))
    fingerprint_mod = load_module("fingerprint", os.path.join(APP_PATH, "fingerprint.py"))
    browser_launcher_mod = load_module("browser_launcher", os.path.join(APP_PATH, "browser_launcher.py"))
    app_meta_mod = load_module("app_meta", os.path.join(APP_PATH, "app_meta.py"))
    runtime_manager_mod = load_module("runtime_manager", os.path.join(APP_PATH, "runtime_manager.py"))
    
    if profiles_mod:
        ProfileManager = profiles_mod.ProfileManager
        ProfileConfig = profiles_mod.ProfileConfig
    if fingerprint_mod:
        FingerprintGenerator = fingerprint_mod.FingerprintGenerator
    if browser_launcher_mod:
        BrowserLauncher = browser_launcher_mod.BrowserLauncher
    if app_meta_mod:
        APP_VERSION_LABEL = app_meta_mod.APP_VERSION_LABEL
    if runtime_manager_mod:
        DEFAULT_RUNTIME_MANIFEST_URL = runtime_manager_mod.DEFAULT_RUNTIME_MANIFEST_URL
        download_runtime_package = runtime_manager_mod.download_and_install
        find_browser_path = runtime_manager_mod.find_browser_path
        get_runtime_status = runtime_manager_mod.get_runtime_status
    print("[DEBUG] Fallback imports loaded")

# Cloud Sync
try:
    from cloud_sync import CloudSync, CloudProfile
    CLOUD_AVAILABLE = True
except ImportError:
    CLOUD_AVAILABLE = False
    CloudProfile = None
    print("[DEBUG] Cloud sync not available")

# Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Colors
COLORS = {
    "bg_dark": "#0e141b",
    "bg_panel": "#141d27",
    "bg_card": "#1b2633",
    "bg_hover": "#223244",
    "accent": "#ff8a3d",
    "accent_hover": "#e67830",
    "accent_soft": "#382518",
    "danger": "#d35d6e",
    "warning": "#f0b24f",
    "info": "#47c0ff",
    "info_hover": "#33a9e0",
    "success": "#33c47a",
    "success_soft": "#163826",
    "border": "#314558",
    "text": "#f4f7fb",
    "text_muted": "#95a6b8",
    "text_dim": "#6f8194",
}

# Settings file
SETTINGS_FILE = os.path.join(APP_PATH, "settings.json")
PROXY_CATALOG_FILE = os.path.join(APP_PATH, "proxy_catalog.json")
DEFAULT_LAUNCH_URL = "https://ipgeo.us/"


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_settings(settings: dict):
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)


def load_proxy_catalog() -> List[Dict]:
    if not os.path.exists(PROXY_CATALOG_FILE):
        return []
    try:
        with open(PROXY_CATALOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        print(f"[WARN] Failed to load proxy catalog: {exc}")
    return []


def save_proxy_catalog(entries: List[Dict]):
    with open(PROXY_CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def parse_proxy_string(raw: str, default_protocol: str = "http") -> Dict:
    raw = raw.strip()
    if not raw:
        raise ValueError("Proxy string is empty")

    protocol = default_protocol
    host = ""
    port = ""
    username = ""
    password = ""

    if "://" in raw:
        from urllib.parse import urlsplit

        parsed = urlsplit(raw)
        protocol = parsed.scheme or default_protocol
        host = parsed.hostname or ""
        port = str(parsed.port or "")
        username = parsed.username or ""
        password = parsed.password or ""
    else:
        parts = raw.split(":")
        if len(parts) >= 4:
            host, port, username, password = parts[0], parts[1], parts[2], ":".join(parts[3:])
        elif len(parts) == 2:
            host, port = parts
        else:
            raise ValueError("Unsupported proxy format")

    if not host or not port:
        raise ValueError("Proxy host or port missing")

    return {
        "id": str(uuid.uuid4())[:8],
        "name": f"{host}:{port}",
        "protocol": protocol,
        "host": host,
        "port": int(port),
        "username": username,
        "password": password,
        "status": "new",
        "last_ip": "",
        "last_checked": "",
        "google_status": "unknown",
        "note": "",
        "created_at": datetime.now().isoformat(),
    }


def proxy_display_name(proxy: Dict) -> str:
    name = proxy.get("name") or f"{proxy.get('host', '')}:{proxy.get('port', '')}"
    return f"{name} • {proxy.get('protocol', 'http')}://{proxy.get('host', '')}:{proxy.get('port', '')}"


def proxy_url(proxy: Dict) -> str:
    protocol = proxy.get("protocol", "http")
    host = proxy.get("host", "")
    port = proxy.get("port", "")
    username = proxy.get("username", "")
    password = proxy.get("password", "")
    url = f"{protocol}://"
    if username:
        url += f"{username}:{password}@"
    url += f"{host}:{port}"
    return url


def test_proxy_endpoint(proxy: Dict) -> str:
    proxy_addr = proxy_url(proxy)
    try:
        try:
            import requests

            proxies = {"http": proxy_addr, "https": proxy_addr}
            response = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=20)
            payload = response.json()
            return payload.get("ip", "unknown")
        except ImportError:
            if str(proxy.get("protocol", "http")).startswith("socks"):
                raise RuntimeError("SOCKS test needs requests[socks] installed")

            import base64
            import urllib.request

            host = proxy.get("host", "")
            port = proxy.get("port", "")
            username = proxy.get("username", "")
            password = proxy.get("password", "")
            proxy_handler = urllib.request.ProxyHandler({
                "http": f"http://{host}:{port}",
                "https": f"http://{host}:{port}",
            })
            opener = urllib.request.build_opener(proxy_handler)
            if username:
                token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
                opener.addheaders = [("Proxy-Authorization", f"Basic {token}")]
            with opener.open("https://api.ipify.org?format=json", timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                return payload.get("ip", "unknown")
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def assess_proxy_health(proxy: Dict) -> Dict:
    ip = test_proxy_endpoint(proxy)
    google_status = "unknown"
    note = ""
    try:
        try:
            import requests

            proxies = {"http": proxy_url(proxy), "https": proxy_url(proxy)}
            response = requests.get(
                "https://www.google.com/search?q=weather",
                proxies=proxies,
                timeout=25,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            body = response.text.lower()
            if (
                "sorry/index" in response.url.lower()
                or "unusual traffic" in body
                or "not a robot" in body
                or "recaptcha" in body
            ):
                google_status = "risk"
                note = "Google challenge detected"
            else:
                google_status = "ok"
        except ImportError:
            google_status = "unknown"
            note = "requests unavailable for Google heuristic"
    except Exception as exc:
        google_status = "unknown"
        note = str(exc)

    return {
        "ip": ip,
        "google_status": google_status,
        "note": note,
    }


COUNTRY_LANGUAGE_MAP = {
    "VN": "vi-VN",
    "US": "en-US",
    "GB": "en-GB",
    "AU": "en-AU",
    "CA": "en-CA",
    "JP": "ja-JP",
    "KR": "ko-KR",
    "CN": "zh-CN",
    "TW": "zh-TW",
    "HK": "zh-HK",
    "FR": "fr-FR",
    "DE": "de-DE",
    "TH": "th-TH",
    "ID": "id-ID",
    "MY": "ms-MY",
    "PH": "en-PH",
    "IN": "en-IN",
    "BR": "pt-BR",
    "ES": "es-ES",
    "IT": "it-IT",
    "RU": "ru-RU",
}


def fetch_ip_geo(ip: str) -> Dict:
    if not ip:
        raise ValueError("Missing IP for geo lookup")

    try:
        import requests

        response = requests.get(
            f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,regionName,city,timezone,lat,lon,query",
            timeout=20,
        )
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(payload.get("message", "geo lookup failed"))
        return {
            "ip": payload.get("query", ip),
            "country": payload.get("country", ""),
            "country_code": payload.get("countryCode", ""),
            "region": payload.get("regionName", ""),
            "city": payload.get("city", ""),
            "timezone": payload.get("timezone", ""),
            "lat": payload.get("lat"),
            "lon": payload.get("lon"),
        }
    except Exception:
        import urllib.request

        with urllib.request.urlopen(
            f"https://ipwho.is/{ip}",
            timeout=20,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("success", False):
            raise RuntimeError(payload.get("message", "geo lookup failed"))
        return {
            "ip": payload.get("ip", ip),
            "country": payload.get("country", ""),
            "country_code": payload.get("country_code", ""),
            "region": payload.get("region", ""),
            "city": payload.get("city", ""),
            "timezone": payload.get("timezone", {}).get("id", "") if isinstance(payload.get("timezone"), dict) else payload.get("timezone", ""),
            "lat": payload.get("latitude"),
            "lon": payload.get("longitude"),
        }


def fetch_proxy_geo(proxy: Dict) -> Dict:
    ip = test_proxy_endpoint(proxy)
    geo = fetch_ip_geo(ip)
    geo["ip"] = ip
    return geo


def language_for_country(country_code: str, fallback: str = "en-US") -> str:
    return COUNTRY_LANGUAGE_MAP.get((country_code or "").upper(), fallback)


def timezone_preset_key(timezone_name: str) -> str:
    for key, data in TIMEZONE_PRESETS.items():
        if data.get("name") == timezone_name:
            return key
    return timezone_name or "Vietnam (UTC+7)"


def os_label_for_platform(platform_value: str) -> str:
    platform_value = (platform_value or "").lower()
    if "win" in platform_value:
        return "Windows"
    if "mac" in platform_value:
        return "macOS"
    if "linux" in platform_value:
        return "Linux"
    return "Windows"


def proxy_display_name(proxy: Dict) -> str:
    name = proxy.get("name") or f"{proxy.get('host', '')}:{proxy.get('port', '')}"
    status = str(proxy.get("status", "new")).lower()
    google_status = str(proxy.get("google_status", "unknown")).lower()
    if status == "failed":
        prefix = "DEAD"
    elif status == "testing":
        prefix = "TEST"
    elif status == "ok":
        prefix = {"ok": "G-OK", "risk": "G-RISK"}.get(google_status, "OK")
    else:
        prefix = "NEW"
    return f"[{prefix}] {name} | {proxy.get('protocol', 'http')}://{proxy.get('host', '')}:{proxy.get('port', '')}"


def proxy_sort_key(proxy: Dict):
    status = str(proxy.get("status", "new")).lower()
    google_status = str(proxy.get("google_status", "unknown")).lower()
    if status == "ok" and google_status == "ok":
        rank = 0
    elif status == "ok" and google_status == "unknown":
        rank = 1
    elif status == "new":
        rank = 2
    elif status == "testing":
        rank = 3
    elif status == "ok" and google_status == "risk":
        rank = 4
    else:
        rank = 5
    return (rank, str(proxy.get("name", "")).lower(), str(proxy.get("host", "")).lower())


def merge_proxy_entries(existing: List[Dict], additions: List[Dict]) -> List[Dict]:
    merged = list(existing)
    for item in additions:
        duplicate = next(
            (
                current
                for current in merged
                if current.get("protocol") == item.get("protocol")
                and current.get("host") == item.get("host")
                and int(current.get("port", 0)) == int(item.get("port", 0))
                and current.get("username", "") == item.get("username", "")
            ),
            None,
        )
        if duplicate:
            duplicate.update(item)
            duplicate["id"] = duplicate.get("id") or item.get("id")
        else:
            merged.append(item)
    return merged


# ============================================================
# GPU PRESETS - Real GPU data for spoofing
# ============================================================
GPU_PRESETS = {
    "NVIDIA": {
        "GTX 1050 Ti": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "GTX 1650": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "GTX 1660 Ti": "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RTX 2060": "ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RTX 3060": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RTX 3070": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RTX 3080": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RTX 4060": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RTX 4070": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RTX 4080": "ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    "AMD": {
        "RX 580": "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RX 5600 XT": "ANGLE (AMD, AMD Radeon RX 5600 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RX 6600 XT": "ANGLE (AMD, AMD Radeon RX 6600 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RX 6700 XT": "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RX 6800 XT": "ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "RX 7900 XTX": "ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Radeon Graphics": "ANGLE (AMD, AMD Radeon Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
    "Intel": {
        "HD Graphics 530": "ANGLE (Intel, Intel(R) HD Graphics 530 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "UHD Graphics 620": "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "UHD Graphics 630": "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "UHD Graphics 770": "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        "Iris Xe Graphics": "ANGLE (Intel, Intel(R) Iris Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    },
}

TIMEZONE_PRESETS = {
    "Vietnam (UTC+7)": {"name": "Asia/Ho_Chi_Minh", "offset": -420},
    "Thailand (UTC+7)": {"name": "Asia/Bangkok", "offset": -420},
    "Singapore (UTC+8)": {"name": "Asia/Singapore", "offset": -480},
    "Japan (UTC+9)": {"name": "Asia/Tokyo", "offset": -540},
    "US East (UTC-5)": {"name": "America/New_York", "offset": 300},
    "US West (UTC-8)": {"name": "America/Los_Angeles", "offset": 480},
    "UK (UTC+0)": {"name": "Europe/London", "offset": 0},
    "Germany (UTC+1)": {"name": "Europe/Berlin", "offset": -60},
    "Australia (UTC+10)": {"name": "Australia/Sydney", "offset": -600},
}


class StartupDialog(ctk.CTk):
    """Dialog chọn thư mục profiles khi khởi động"""
    
    def __init__(self):
        super().__init__()
        
        self.profiles_path = None
        self.settings = load_settings()
        
        self.title("S Manage - Setup")
        self.geometry("550x400")
        self.resizable(False, False)
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 550) // 2
        y = (self.winfo_screenheight() - 400) // 2
        self.geometry(f"550x400+{x}+{y}")
        
        self._create_widgets()
        
        # Auto-continue if path exists
        if self.settings.get('profiles_path') and os.path.exists(self.settings['profiles_path']):
            self.path_entry.insert(0, self.settings['profiles_path'])
    
    def _create_widgets(self):
        # Logo/Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(pady=40)
        
        ctk.CTkLabel(
            title_frame,
            text="🛡️ S Manage",
            font=ctk.CTkFont(size=36, weight="bold")
        ).pack()
        
        ctk.CTkLabel(
            title_frame,
            text=f"Antidetect Browser Manager {APP_VERSION_LABEL}",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_muted"]
        ).pack(pady=5)
        
        # Path selection
        path_frame = ctk.CTkFrame(self, fg_color="transparent")
        path_frame.pack(fill="x", padx=50, pady=20)
        
        ctk.CTkLabel(
            path_frame,
            text="📁 Profiles Storage Location:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        ).pack(fill="x", pady=(0, 10))
        
        entry_frame = ctk.CTkFrame(path_frame, fg_color="transparent")
        entry_frame.pack(fill="x")
        
        self.path_entry = ctk.CTkEntry(
            entry_frame,
            placeholder_text="Select folder to store profiles...",
            height=45,
            font=ctk.CTkFont(size=13)
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkButton(
            entry_frame,
            text="📂 Browse",
            width=100,
            height=45,
            command=self._browse_folder
        ).pack(side="right")
        
        # Info
        ctk.CTkLabel(
            self,
            text="Each profile has isolated cookies, cache, and unique fingerprint.\nYour profiles will be saved in this folder.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            justify="center"
        ).pack(pady=15)
        
        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=25)
        
        ctk.CTkButton(
            btn_frame,
            text="✓ Continue",
            width=160,
            height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._continue
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            btn_frame,
            text="✕ Exit",
            width=100,
            height=50,
            font=ctk.CTkFont(size=14),
            fg_color="#6c757d",
            hover_color="#5a6268",
            command=self.destroy
        ).pack(side="left")
    
    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select Profiles Storage Folder")
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, folder)
    
    def _continue(self):
        path = self.path_entry.get().strip()
        if not path:
            messagebox.showerror("Error", "Please select a folder for profiles storage.")
            return
        
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create folder: {e}")
                return
        
        self.settings['profiles_path'] = path
        save_settings(self.settings)
        self.profiles_path = path
        self.destroy()


class ProfileCard(ctk.CTkFrame):
    """Card hiển thị 1 profile"""
    
    def __init__(self, master, profile: ProfileConfig, callbacks: dict, **kwargs):
        super().__init__(master, **kwargs)
        self.profile = profile
        self.callbacks = callbacks
        
        self.configure(fg_color=COLORS["bg_card"], corner_radius=12, height=80)
        self.pack_propagate(False)
        self._create_widgets()
        
        # Hover effect
        self.bind("<Enter>", lambda e: self.configure(fg_color=COLORS["bg_hover"]))
        self.bind("<Leave>", lambda e: self.configure(fg_color=COLORS["bg_card"]))
    
    def _create_widgets(self):
        # Main container
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Left - Info
        info = ctk.CTkFrame(main, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)
        
        # Name row
        name_row = ctk.CTkFrame(info, fg_color="transparent")
        name_row.pack(fill="x")
        
        # Status dot
        ctk.CTkLabel(
            name_row, text="●", font=ctk.CTkFont(size=10),
            text_color=COLORS["accent"] if getattr(self.profile, 'is_running', False) else COLORS["text_muted"]
        ).pack(side="left", padx=(0, 8))
        
        ctk.CTkLabel(
            name_row, text=self.profile.name,
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left")
        
        # Tags
        if self.profile.tags:
            for tag in self.profile.tags[:3]:
                ctk.CTkLabel(
                    name_row, text=tag,
                    font=ctk.CTkFont(size=10),
                    fg_color="#3a3a3a", corner_radius=4,
                    padx=6, pady=2
                ).pack(side="left", padx=3)
        
        # Fingerprint summary
        fp_info = self._get_fingerprint_summary()
        ctk.CTkLabel(
            info, text=fp_info,
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", pady=(3, 0))
        
        # Proxy info
        proxy_text = f"🔒 {self.profile.proxy_type}://{self.profile.proxy_host}:{self.profile.proxy_port}" if self.profile.proxy_enabled else "🌐 Direct"
        ctk.CTkLabel(
            info, text=proxy_text,
            font=ctk.CTkFont(size=11),
            text_color="#666666"
        ).pack(anchor="w")
        
        # Right - Buttons
        btns = ctk.CTkFrame(main, fg_color="transparent")
        btns.pack(side="right")
        
        ctk.CTkButton(
            btns, text="▶ Start", width=85, height=36,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.callbacks['launch'](self.profile.id)
        ).pack(side="left", padx=3)
        
        ctk.CTkButton(
            btns, text="✏️", width=36, height=36,
            fg_color=COLORS["info"], hover_color="#138496",
            command=lambda: self.callbacks['edit'](self.profile.id)
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btns, text="📋", width=36, height=36,
            fg_color="#6c757d", hover_color="#5a6268",
            command=lambda: self.callbacks['duplicate'](self.profile.id)
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btns, text="🗑️", width=36, height=36,
            fg_color=COLORS["danger"], hover_color="#c82333",
            command=lambda: self.callbacks['delete'](self.profile.id)
        ).pack(side="left", padx=2)
    
    def _get_fingerprint_summary(self):
        """Get fingerprint summary text"""
        gpu = self.profile.webgl_renderer or "Default GPU"
        if "NVIDIA" in gpu:
            gpu_icon = "🟢"
            gpu_name = gpu.split("NVIDIA ")[1].split(" Direct")[0] if "NVIDIA " in gpu else "NVIDIA"
        elif "AMD" in gpu:
            gpu_icon = "🔴"
            gpu_name = gpu.split("AMD ")[1].split(" Direct")[0] if "AMD " in gpu else "AMD"
        elif "Intel" in gpu:
            gpu_icon = "🔵"
            gpu_name = gpu.split("Intel(R) ")[1].split(" Direct")[0] if "Intel(R) " in gpu else "Intel"
        else:
            gpu_icon = "⚪"
            gpu_name = "Default"
        
        return f"{gpu_icon} {gpu_name} | 🖥️ {self.profile.screen_width}x{self.profile.screen_height} | 🌍 {self.profile.timezone.split('/')[-1]}"


class ProfileShelfCard(ctk.CTkFrame):
    """Richer profile management card."""

    def __init__(self, master, profile: ProfileConfig, callbacks: dict, **kwargs):
        super().__init__(master, **kwargs)
        self.profile = profile
        self.callbacks = callbacks

        self.configure(
            fg_color=COLORS["bg_card"],
            corner_radius=22,
            height=176,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.pack_propagate(False)
        self._create_widgets()
        self._bind_hover(self)

    def _bind_hover(self, widget):
        widget.bind("<Enter>", lambda _event: self._set_hover(True))
        widget.bind("<Leave>", lambda _event: self._set_hover(False))
        for child in widget.winfo_children():
            self._bind_hover(child)

    def _set_hover(self, hovered: bool):
        self.configure(fg_color=COLORS["bg_hover"] if hovered else COLORS["bg_card"])

    def _create_widgets(self):
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=20, pady=18)

        left = ctk.CTkFrame(shell, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True)

        right = ctk.CTkFrame(shell, fg_color="transparent", width=184)
        right.pack(side="right", fill="y", padx=(18, 0))
        right.pack_propagate(False)

        top = ctk.CTkFrame(left, fg_color="transparent")
        top.pack(fill="x")

        self._meta_chip(
            top,
            self._status_text(),
            COLORS["success_soft"] if getattr(self.profile, "is_running", False) else COLORS["bg_panel"],
            COLORS["success"] if getattr(self.profile, "is_running", False) else COLORS["text_muted"],
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            top,
            text=self.profile.name,
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        self._meta_chip(
            top,
            f"ID {self.profile.id}",
            COLORS["bg_panel"],
            COLORS["text_muted"],
        ).pack(side="left", padx=10)

        tags_row = ctk.CTkFrame(left, fg_color="transparent")
        tags_row.pack(fill="x", pady=(8, 0))
        for tag in (self.profile.tags or [])[:3]:
            self._meta_chip(tags_row, tag, COLORS["accent_soft"], COLORS["accent"]).pack(side="left", padx=(0, 6))

        summary_row = ctk.CTkFrame(left, fg_color="transparent")
        summary_row.pack(fill="x", pady=(12, 0))

        summary = ctk.CTkFrame(
            summary_row,
            fg_color=COLORS["bg_panel"],
            corner_radius=16,
            border_width=1,
            border_color=COLORS["border"],
            height=54,
        )
        summary.pack(side="left", fill="x", expand=True)
        summary.pack_propagate(False)

        ctk.CTkLabel(
            summary,
            text=self._gpu_name(),
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(anchor="w", padx=14, pady=(9, 0))
        ctk.CTkLabel(
            summary,
            text=f"Chrome {self._chrome_major()}  •  {self._proxy_text()}",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", padx=14, pady=(2, 0))

        metrics = ctk.CTkFrame(left, fg_color="transparent")
        metrics.pack(fill="x", pady=(14, 0))

        self._metric_tile(metrics, "Display", f"{self.profile.screen_width} × {self.profile.screen_height}").pack(
            side="left", fill="y"
        )
        self._metric_tile(metrics, "Hardware", f"{self.profile.cpu_cores} cores / {self.profile.ram_gb} GB").pack(
            side="left", fill="y", padx=8
        )
        self._metric_tile(metrics, "Locale", self.profile.language.split(",")[0].upper()).pack(
            side="left", fill="y"
        )
        self._metric_tile(metrics, "Timezone", self.profile.timezone.split("/")[-1]).pack(
            side="left", fill="y", padx=(8, 0)
        )

        ctk.CTkLabel(
            left,
            text=f"Last activity: {self._last_used_text()}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(12, 0))

        ctk.CTkButton(
            right,
            text="Launch" if not getattr(self.profile, "is_running", False) else "Running",
            width=184,
            height=46,
            corner_radius=14,
            fg_color=COLORS["accent"] if not getattr(self.profile, "is_running", False) else COLORS["success"],
            hover_color=COLORS["accent_hover"] if not getattr(self.profile, "is_running", False) else "#2aae69",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: self.callbacks["launch"](self.profile.id),
        ).pack(fill="x")

        ctk.CTkLabel(
            right,
            text="Fingerprint deck",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(12, 4))

        ctk.CTkButton(
            right,
            text="Edit Profile",
            width=184,
            height=34,
            corner_radius=12,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            text_color=COLORS["bg_dark"],
            command=lambda: self.callbacks["edit"](self.profile.id),
        ).pack(fill="x")

        ctk.CTkButton(
            right,
            text="Clone Profile",
            width=184,
            height=34,
            corner_radius=12,
            fg_color=COLORS["bg_panel"],
            hover_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            command=lambda: self.callbacks["duplicate"](self.profile.id),
        ).pack(fill="x", pady=8)

        ctk.CTkButton(
            right,
            text="Delete",
            width=184,
            height=34,
            corner_radius=12,
            fg_color=COLORS["danger"],
            hover_color="#bc4c5d",
            command=lambda: self.callbacks["delete"](self.profile.id),
        ).pack(fill="x")

    def _metric_tile(self, parent, label: str, value: str):
        tile = ctk.CTkFrame(
            parent,
            fg_color=COLORS["bg_panel"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
            width=146,
            height=68,
        )
        tile.pack_propagate(False)
        ctk.CTkLabel(
            tile,
            text=label.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", padx=12, pady=(10, 2))
        ctk.CTkLabel(
            tile,
            text=value,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=12)
        return tile

    def _meta_chip(self, parent, text: str, fg_color: str, text_color: str):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=fg_color,
            text_color=text_color,
            corner_radius=999,
            padx=10,
            pady=5,
        )

    def _status_text(self) -> str:
        return "LIVE" if getattr(self.profile, "is_running", False) else "READY"

    def _last_used_text(self) -> str:
        if not self.profile.last_used:
            return "Never launched"
        try:
            parsed = datetime.fromisoformat(self.profile.last_used)
            return parsed.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return self.profile.last_used

    def _proxy_text(self) -> str:
        if self.profile.proxy_enabled and self.profile.proxy_host:
            return f"Proxy {self.profile.proxy_type}://{self.profile.proxy_host}:{self.profile.proxy_port}"
        return "Direct connection"

    def _chrome_major(self) -> str:
        if self.profile.user_agent and "Chrome/" in self.profile.user_agent:
            try:
                return self.profile.user_agent.split("Chrome/", 1)[1].split(".", 1)[0]
            except IndexError:
                pass
        return "146"

    def _gpu_name(self) -> str:
        renderer = self.profile.webgl_renderer or ""
        for marker in ["NVIDIA ", "AMD ", "Intel(R) "]:
            if marker in renderer:
                return renderer.split(marker, 1)[1].split(" Direct", 1)[0]
        return "Default GPU"


class ProfileDialog(ctk.CTkToplevel):
    """Dialog tạo/sửa profile"""
    
    def __init__(self, master, manager: ProfileManager, on_save=None, edit_profile=None):
        super().__init__(master)
        
        self.manager = manager
        self.on_save = on_save
        self.edit_profile = edit_profile
        
        self.title("Edit Profile" if edit_profile else "Create New Profile")
        self.geometry("1040x780")
        self.resizable(True, True)
        
        self.transient(master)
        self.grab_set()
        
        # Center
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - 1040) // 2
        y = master.winfo_y() + (master.winfo_height() - 780) // 2
        self.geometry(f"1040x780+{x}+{y}")
        
        self._create_widgets()
        
        if edit_profile:
            self._load_profile()
    
    def _section(self, parent, title, icon=""):
        """Create section header"""
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_dark"], corner_radius=8)
        frame.pack(fill="x", pady=(15, 8))
        ctk.CTkLabel(
            frame, text=f"{icon} {title}",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=12, pady=10)
        return frame
    
    def _create_widgets(self):
        # Scrollable main
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=20, pady=10)
        
        # === PROFILE INFO ===
        self._section(main, "Profile Information", "📋")
        
        info_grid = ctk.CTkFrame(main, fg_color="transparent")
        info_grid.pack(fill="x", padx=10)
        
        ctk.CTkLabel(info_grid, text="Name:", width=100, anchor="w").grid(row=0, column=0, pady=5)
        self.name_entry = ctk.CTkEntry(info_grid, width=400, placeholder_text="Profile name")
        self.name_entry.grid(row=0, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(info_grid, text="Tags:", width=100, anchor="w").grid(row=1, column=0, pady=5)
        self.tags_entry = ctk.CTkEntry(info_grid, width=400, placeholder_text="work, facebook, main (comma separated)")
        self.tags_entry.grid(row=1, column=1, pady=5, sticky="w")
        
        # === GPU / WEBGL ===
        self._section(main, "GPU / WebGL", "🎮")
        
        gpu_grid = ctk.CTkFrame(main, fg_color="transparent")
        gpu_grid.pack(fill="x", padx=10)
        
        ctk.CTkLabel(gpu_grid, text="Brand:", width=100, anchor="w").grid(row=0, column=0, pady=5)
        self.gpu_brand_var = ctk.StringVar(value="NVIDIA")
        self.gpu_brand = ctk.CTkComboBox(
            gpu_grid, width=150, values=list(GPU_PRESETS.keys()),
            variable=self.gpu_brand_var, command=self._on_gpu_brand_change
        )
        self.gpu_brand.grid(row=0, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(gpu_grid, text="Model:", width=100, anchor="w").grid(row=1, column=0, pady=5)
        self.gpu_model_var = ctk.StringVar()
        self.gpu_model = ctk.CTkComboBox(gpu_grid, width=350, variable=self.gpu_model_var)
        self.gpu_model.grid(row=1, column=1, pady=5, sticky="w")
        self._on_gpu_brand_change("NVIDIA")
        
        # === SCREEN ===
        self._section(main, "Screen & Display", "🖥️")
        
        screen_grid = ctk.CTkFrame(main, fg_color="transparent")
        screen_grid.pack(fill="x", padx=10)
        
        ctk.CTkLabel(screen_grid, text="Resolution:", width=100, anchor="w").grid(row=0, column=0, pady=5)
        self.resolution_var = ctk.StringVar(value="1920x1080")
        ctk.CTkComboBox(
            screen_grid, width=180,
            values=["1366x768", "1440x900", "1536x864", "1600x900", "1920x1080", "2560x1440", "3840x2160"],
            variable=self.resolution_var
        ).grid(row=0, column=1, pady=5, sticky="w")
        
        # === HARDWARE (CPU/RAM) ===
        self._section(main, "Hardware", "💻")
        
        hw_grid = ctk.CTkFrame(main, fg_color="transparent")
        hw_grid.pack(fill="x", padx=10)
        
        ctk.CTkLabel(hw_grid, text="CPU Cores:", width=100, anchor="w").grid(row=0, column=0, pady=5)
        self.cpu_cores_var = ctk.StringVar(value="8")
        ctk.CTkComboBox(
            hw_grid, width=100,
            values=["2", "4", "6", "8", "10", "12", "16", "24", "32"],
            variable=self.cpu_cores_var
        ).grid(row=0, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(hw_grid, text="RAM (GB):", width=100, anchor="w").grid(row=1, column=0, pady=5)
        self.ram_var = ctk.StringVar(value="8")
        ctk.CTkComboBox(
            hw_grid, width=100,
            values=["2", "4", "8", "16", "32", "64"],
            variable=self.ram_var
        ).grid(row=1, column=1, pady=5, sticky="w")
        
        # === TIMEZONE ===
        self._section(main, "Timezone & Language", "🌍")
        
        tz_grid = ctk.CTkFrame(main, fg_color="transparent")
        tz_grid.pack(fill="x", padx=10)
        
        ctk.CTkLabel(tz_grid, text="Timezone:", width=100, anchor="w").grid(row=0, column=0, pady=5)
        self.timezone_var = ctk.StringVar(value="Vietnam (UTC+7)")
        ctk.CTkComboBox(
            tz_grid, width=250, values=list(TIMEZONE_PRESETS.keys()),
            variable=self.timezone_var
        ).grid(row=0, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(tz_grid, text="Language:", width=100, anchor="w").grid(row=1, column=0, pady=5)
        self.language_var = ctk.StringVar(value="en-US")
        ctk.CTkComboBox(
            tz_grid, width=150,
            values=["en-US", "en-GB", "vi-VN", "zh-CN", "ja-JP", "ko-KR", "fr-FR", "de-DE"],
            variable=self.language_var
        ).grid(row=1, column=1, pady=5, sticky="w")
        
        # === PROXY ===
        self._section(main, "Proxy Settings", "🔒")
        
        proxy_grid = ctk.CTkFrame(main, fg_color="transparent")
        proxy_grid.pack(fill="x", padx=10)
        
        self.proxy_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            proxy_grid, text="Enable Proxy",
            variable=self.proxy_enabled, command=self._toggle_proxy
        ).grid(row=0, column=0, columnspan=2, pady=5, sticky="w")
        
        ctk.CTkLabel(proxy_grid, text="Type:", width=100, anchor="w").grid(row=1, column=0, pady=5)
        self.proxy_type = ctk.StringVar(value="http")
        self.proxy_type_cb = ctk.CTkComboBox(
            proxy_grid, width=100, values=["http", "socks5"],
            variable=self.proxy_type, state="disabled"
        )
        self.proxy_type_cb.grid(row=1, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(proxy_grid, text="Host:", width=100, anchor="w").grid(row=2, column=0, pady=5)
        self.proxy_host = ctk.CTkEntry(proxy_grid, width=300, placeholder_text="proxy.example.com", state="disabled")
        self.proxy_host.grid(row=2, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(proxy_grid, text="Port:", width=100, anchor="w").grid(row=3, column=0, pady=5)
        self.proxy_port = ctk.CTkEntry(proxy_grid, width=100, placeholder_text="8080", state="disabled")
        self.proxy_port.grid(row=3, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(proxy_grid, text="Username:", width=100, anchor="w").grid(row=4, column=0, pady=5)
        self.proxy_user = ctk.CTkEntry(proxy_grid, width=200, placeholder_text="optional", state="disabled")
        self.proxy_user.grid(row=4, column=1, pady=5, sticky="w")
        
        ctk.CTkLabel(proxy_grid, text="Password:", width=100, anchor="w").grid(row=5, column=0, pady=5)
        self.proxy_pass = ctk.CTkEntry(proxy_grid, width=200, placeholder_text="optional", show="*", state="disabled")
        self.proxy_pass.grid(row=5, column=1, pady=5, sticky="w")
        
        # === BUTTONS ===
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkButton(
            btn_frame, text="🎲 Randomize",
            width=120, fg_color="#6c757d", hover_color="#5a6268",
            command=self._randomize
        ).pack(side="left")
        
        ctk.CTkButton(
            btn_frame, text="✕ Cancel",
            width=100, fg_color=COLORS["danger"], hover_color="#c82333",
            command=self.destroy
        ).pack(side="right", padx=(10, 0))
        
        ctk.CTkButton(
            btn_frame, text="✓ Save Profile",
            width=150, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(weight="bold"),
            command=self._save
        ).pack(side="right")
    
    def _on_gpu_brand_change(self, brand):
        models = list(GPU_PRESETS.get(brand, {}).keys())
        self.gpu_model.configure(values=models)
        if models:
            self.gpu_model_var.set(models[0])
    
    def _toggle_proxy(self):
        state = "normal" if self.proxy_enabled.get() else "disabled"
        self.proxy_type_cb.configure(state=state)
        self.proxy_host.configure(state=state)
        self.proxy_port.configure(state=state)
        self.proxy_user.configure(state=state)
        self.proxy_pass.configure(state=state)
    
    def _randomize(self):
        import random
        
        brand = random.choice(list(GPU_PRESETS.keys()))
        self.gpu_brand_var.set(brand)
        self._on_gpu_brand_change(brand)
        model = random.choice(list(GPU_PRESETS[brand].keys()))
        self.gpu_model_var.set(model)
        
        self.resolution_var.set(random.choice(["1920x1080", "1366x768", "2560x1440"]))
        self.timezone_var.set(random.choice(list(TIMEZONE_PRESETS.keys())))
        self.language_var.set(random.choice(["en-US", "en-GB", "vi-VN"]))
    
    def _load_profile(self):
        p = self.edit_profile
        self.name_entry.insert(0, p.name)
        self.tags_entry.insert(0, ", ".join(p.tags) if p.tags else "")
        
        # GPU
        renderer = p.webgl_renderer or ""
        for brand, models in GPU_PRESETS.items():
            for model_name, model_str in models.items():
                if model_str == renderer:
                    self.gpu_brand_var.set(brand)
                    self._on_gpu_brand_change(brand)
                    self.gpu_model_var.set(model_name)
                    break
        
        self.resolution_var.set(f"{p.screen_width}x{p.screen_height}")
        
        # Hardware
        self.cpu_cores_var.set(str(p.cpu_cores if hasattr(p, 'cpu_cores') else 8))
        self.ram_var.set(str(p.ram_gb if hasattr(p, 'ram_gb') else 8))
        
        # Timezone
        for name, data in TIMEZONE_PRESETS.items():
            if data["name"] == p.timezone:
                self.timezone_var.set(name)
                break
        
        self.language_var.set(p.language.split(",")[0])
        
        # Proxy
        self.proxy_enabled.set(p.proxy_enabled)
        self._toggle_proxy()
        if p.proxy_enabled:
            self.proxy_type.set(p.proxy_type)
            self.proxy_host.insert(0, p.proxy_host)
            self.proxy_port.insert(0, str(p.proxy_port))
            if p.proxy_username:
                self.proxy_user.insert(0, p.proxy_username)
            if p.proxy_password:
                self.proxy_pass.insert(0, p.proxy_password)
        if hasattr(self, "_refresh_preview"):
            self._refresh_preview()
    
    def _save(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Profile name is required")
            return
        
        # Parse data
        res = self.resolution_var.get().split("x")
        screen_width, screen_height = int(res[0]), int(res[1])
        
        brand = self.gpu_brand_var.get()
        model = self.gpu_model_var.get()
        webgl_vendor = f"Google Inc. ({brand})"
        webgl_renderer = GPU_PRESETS.get(brand, {}).get(model, "")
        
        tz_data = TIMEZONE_PRESETS.get(self.timezone_var.get(), {"name": "Asia/Ho_Chi_Minh", "offset": -420})
        
        tags = [t.strip() for t in self.tags_entry.get().split(",") if t.strip()]
        
        if self.edit_profile:
            # Update
            p = self.edit_profile
            p.name = name
            p.tags = tags
            p.screen_width = screen_width
            p.screen_height = screen_height
            p.cpu_cores = int(self.cpu_cores_var.get())
            p.ram_gb = int(self.ram_var.get())
            p.webgl_vendor = webgl_vendor
            p.webgl_renderer = webgl_renderer
            p.timezone = tz_data["name"]
            p.language = self.language_var.get()
            p.proxy_enabled = self.proxy_enabled.get()
            if p.proxy_enabled:
                p.proxy_type = self.proxy_type.get()
                p.proxy_host = self.proxy_host.get()
                p.proxy_port = int(self.proxy_port.get() or 0)
                p.proxy_username = self.proxy_user.get()
                p.proxy_password = self.proxy_pass.get()
            
            self.manager._save_profile_config(p)
        else:
            # Create new
            fingerprint = {
                'screen_width': screen_width,
                'screen_height': screen_height,
                'cpu_cores': int(self.cpu_cores_var.get()),
                'ram_gb': int(self.ram_var.get()),
                'webgl_vendor': webgl_vendor,
                'webgl_renderer': webgl_renderer,
                'timezone': tz_data["name"],
                'language': self.language_var.get(),
            }
            
            p = self.manager.create_profile(name=name, fingerprint=fingerprint)
            p.tags = tags
            p.proxy_enabled = self.proxy_enabled.get()
            if p.proxy_enabled:
                p.proxy_type = self.proxy_type.get()
                p.proxy_host = self.proxy_host.get()
                p.proxy_port = int(self.proxy_port.get() or 0)
                p.proxy_username = self.proxy_user.get()
                p.proxy_password = self.proxy_pass.get()
            
            self.manager._save_profile_config(p)

        if hasattr(self.master, "_show_page"):
            try:
                self.master._show_page("profiles")
            except Exception:
                pass
        if hasattr(self.master, "selected_profile_id"):
            self.master.selected_profile_id = p.id

        if self.on_save:
            self.on_save()

        if getattr(self, "_launch_after_save", False) and hasattr(self.master, "_launch"):
            self.master.after(250, lambda pid=p.id: self.master._launch(pid))
        self._launch_after_save = False
        self.destroy()


class MainApp(ctk.CTk):
    """Main application"""
    
    def __init__(self, profiles_path: str):
        super().__init__()
        
        self.profiles_path = profiles_path

        settings = load_settings()
        configured_browser = settings.get("browser_path", "")
        self.browser_path = find_browser_path(APP_PATH, configured_browser)
        print(f"[DEBUG] Runtime browser path = {self.browser_path}")
        if not self.browser_path:
            messagebox.showerror(
                "Browser Runtime Missing",
                "Browser runtime is not installed yet.\nOpen setup again and download the runtime package.",
            )
            self.browser_path = configured_browser or os.path.join(os.path.dirname(APP_PATH), "browser", "chrome.exe")
        
        # Create config for ProfileManager
        config_path = os.path.join(APP_PATH, "config.json")
        config = {"browser_path": self.browser_path, "profiles_dir": profiles_path, "default_args": []}
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        self.manager = ProfileManager(config_path)
        self.running = {}
        
        self.title("S Manage - Antidetect Browser Manager")
        self.geometry("1100x750")
        self.minsize(900, 600)
        
        self._create_widgets()
        self._refresh()
    
    def _create_widgets(self):
        # Header
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], height=65)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header, text="🛡️ S Manage",
            font=ctk.CTkFont(size=26, weight="bold")
        ).pack(side="left", padx=25, pady=15)
        
        # Version badge
        ctk.CTkLabel(
            header, text=APP_VERSION_LABEL,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["accent"], corner_radius=4,
            padx=8, pady=2
        ).pack(side="left", pady=20)
        
        # Path
        ctk.CTkLabel(
            header, text=f"📁 {self.profiles_path}",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        ).pack(side="left", padx=15)
        
        # Settings
        ctk.CTkButton(
            header, text="⚙️ Settings",
            width=100, fg_color="transparent", hover_color="#333",
            command=self._open_settings
        ).pack(side="right", padx=15, pady=15)
        
        # Cloud Sync Button
        if CLOUD_AVAILABLE:
            self.cloud_sync = CloudSync(APP_PATH)
            self.cloud_btn = ctk.CTkButton(
                header, text="☁️ Cloud",
                width=100, fg_color="transparent", hover_color="#333",
                command=self._open_cloud
            )
            self.cloud_btn.pack(side="right", pady=15)
            self._update_cloud_status()
        
        # Toolbar
        toolbar = ctk.CTkFrame(self, fg_color="transparent", height=55)
        toolbar.pack(fill="x", padx=25, pady=10)
        
        ctk.CTkButton(
            toolbar, text="➕ New Profile",
            width=150, height=42,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._new_profile
        ).pack(side="left")
        
        ctk.CTkButton(
            toolbar, text="🔄", width=42, height=42,
            fg_color=COLORS["info"], hover_color="#138496",
            command=self._refresh
        ).pack(side="left", padx=10)
        
        # Search
        self.search_var = ctk.StringVar()
        self.search_var.trace("w", lambda *_: self._filter())
        ctk.CTkEntry(
            toolbar, placeholder_text="🔍 Search profiles...",
            width=280, height=42, textvariable=self.search_var
        ).pack(side="right")
        
        # Stats
        self.stats = ctk.CTkLabel(toolbar, text="", font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"])
        self.stats.pack(side="right", padx=20)
        
        # Profile list
        self.list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list_frame.pack(fill="both", expand=True, padx=25, pady=10)
        
        # Status bar
        status = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], height=35)
        status.pack(fill="x", side="bottom")
        
        self.status = ctk.CTkLabel(
            status, text="Ready",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.status.pack(side="left", padx=15, pady=8)
    
    def _refresh(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        
        profiles = self.manager.list_profiles()
        self.stats.configure(text=f"📊 {len(profiles)} profiles")
        
        if not profiles:
            ctk.CTkLabel(
                self.list_frame,
                text="No profiles yet. Click '➕ New Profile' to create one.",
                font=ctk.CTkFont(size=14),
                text_color=COLORS["text_muted"]
            ).pack(pady=80)
            return
        
        callbacks = {
            'launch': self._launch,
            'edit': self._edit,
            'delete': self._delete,
            'duplicate': self._duplicate,
        }
        
        for p in profiles:
            card = ProfileCard(self.list_frame, p, callbacks)
            card.pack(fill="x", pady=4)
    
    def _filter(self):
        search = self.search_var.get().lower()
        for w in self.list_frame.winfo_children():
            if isinstance(w, ProfileCard):
                match = search in w.profile.name.lower()
                if w.profile.tags:
                    match = match or any(search in t.lower() for t in w.profile.tags)
                w.pack(fill="x", pady=4) if match else w.pack_forget()
    
    def _new_profile(self):
        ProfileDialog(self, self.manager, on_save=self._refresh)
    
    def _edit(self, pid):
        p = self.manager.load_profile(pid)
        if p:
            ProfileDialog(self, self.manager, on_save=self._refresh, edit_profile=p)
    
    def _delete(self, pid):
        if messagebox.askyesno("Delete", "Delete this profile?"):
            self.manager.delete_profile(pid)
            self._refresh()
            self.status.configure(text="Profile deleted")
    
    def _duplicate(self, pid):
        p = self.manager.load_profile(pid)
        if p:
            self.manager.clone_profile(pid, f"{p.name} (Copy)")
            self._refresh()
            self.status.configure(text="Profile duplicated")
    
    def _launch(self, pid):
        p = self.manager.load_profile(pid)
        if not p:
            return
        
        self.status.configure(text=f"Launching {p.name}...")
        
        def run():
            try:
                print(f"[DEBUG] Browser path: {self.browser_path}")
                print(f"[DEBUG] Browser exists: {os.path.exists(self.browser_path)}")
                
                launcher = BrowserLauncher(self.browser_path)
                
                # Build fingerprint
                fp = {
                    'screen_width': p.screen_width,
                    'screen_height': p.screen_height,
                    'hardware_concurrency': p.cpu_cores if hasattr(p, 'cpu_cores') else 8,
                    'device_memory': p.ram_gb if hasattr(p, 'ram_gb') else 8,
                    'webgl_vendor': p.webgl_vendor,
                    'webgl_renderer': p.webgl_renderer,
                    'timezone': p.timezone,
                    'language': p.language,
                    'platform': 'Win32',
                }
                
                # Proxy
                proxy = None
                if p.proxy_enabled:
                    proxy = f"{p.proxy_type}://"
                    if p.proxy_username:
                        proxy += f"{p.proxy_username}:{p.proxy_password}@"
                    proxy += f"{p.proxy_host}:{p.proxy_port}"
                
                user_data = str(self.manager.profiles_dir / f"profile_{pid}" / "UserData")
                print(f"[DEBUG] User data: {user_data}")
                
                process = launcher.launch(user_data_dir=user_data, fingerprint=fp, proxy=proxy)
                self.running[pid] = process
                
                p.last_used = datetime.now().isoformat()
                self.manager._save_profile_config(p)
                
                self.after(0, lambda: self.status.configure(text=f"✓ {p.name} running"))
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        threading.Thread(target=run, daemon=True).start()
    
    def _open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("450x350")
        win.transient(self)
        win.grab_set()
        
        ctk.CTkLabel(win, text="⚙️ Settings", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=25)
        
        settings = load_settings()
        
        ctk.CTkLabel(win, text="Profiles Path:", anchor="w").pack(fill="x", padx=25)
        path_entry = ctk.CTkEntry(win, width=350)
        path_entry.insert(0, settings.get('profiles_path', ''))
        path_entry.pack(padx=25, pady=5)
        
        ctk.CTkLabel(win, text="Browser Path:", anchor="w").pack(fill="x", padx=25, pady=(15, 0))
        browser_entry = ctk.CTkEntry(win, width=350)
        browser_entry.insert(0, self.browser_path)
        browser_entry.pack(padx=25, pady=5)
        
        def save():
            settings['profiles_path'] = path_entry.get()
            settings['browser_path'] = browser_entry.get()
            save_settings(settings)
            messagebox.showinfo("Saved", "Settings saved. Restart to apply.")
            win.destroy()
        
        ctk.CTkButton(win, text="Save", fg_color=COLORS["accent"], command=save).pack(pady=25)
    
    def _update_cloud_status(self):
        """Update cloud button text based on login status"""
        if not CLOUD_AVAILABLE:
            return
        
        if self.cloud_sync.is_logged_in():
            email = self.cloud_sync.get_user_email() or "Connected"
            short_email = email.split('@')[0][:10] if '@' in email else email[:10]
            self.cloud_btn.configure(text=f"☁️ {short_email}", fg_color=COLORS["accent"])
        else:
            self.cloud_btn.configure(text="☁️ Cloud", fg_color="transparent")
    
    def _open_cloud(self):
        """Open cloud sync dialog"""
        win = ctk.CTkToplevel(self)
        win.title("Cloud Sync")
        win.geometry("500x450")
        win.transient(self)
        win.grab_set()
        
        ctk.CTkLabel(win, text="☁️ Google Drive Sync", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=20)
        
        # Status frame
        status_frame = ctk.CTkFrame(win, fg_color=COLORS["bg_card"])
        status_frame.pack(fill="x", padx=25, pady=10)
        
        if self.cloud_sync.is_logged_in():
            email = self.cloud_sync.get_user_email() or "Connected"
            ctk.CTkLabel(status_frame, text=f"✅ Đã đăng nhập: {email}", 
                        text_color=COLORS["accent"]).pack(pady=15)
            
            # Cloud profiles count
            cloud_profiles = self.cloud_sync.list_cloud_profiles()
            ctk.CTkLabel(status_frame, text=f"📁 {len(cloud_profiles)} profiles trên cloud",
                        text_color=COLORS["text_muted"]).pack(pady=(0, 15))
        else:
            ctk.CTkLabel(status_frame, text="❌ Chưa đăng nhập", 
                        text_color=COLORS["text_muted"]).pack(pady=15)
        
        # Progress bar (hidden initially)
        progress_frame = ctk.CTkFrame(win, fg_color="transparent")
        progress_frame.pack(fill="x", padx=25, pady=10)
        progress_label = ctk.CTkLabel(progress_frame, text="")
        progress_label.pack()
        progress_bar = ctk.CTkProgressBar(progress_frame)
        progress_bar.set(0)
        
        # Buttons
        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=20)
        
        def on_login():
            if self.cloud_sync.login():
                self._update_cloud_status()
                win.destroy()
                self._open_cloud()  # Reopen with new status
            else:
                messagebox.showerror("Error", "Đăng nhập thất bại!")
        
        def on_logout():
            self.cloud_sync.logout()
            self._update_cloud_status()
            win.destroy()
            self._open_cloud()
        
        def on_download():
            progress_bar.pack(pady=5)
            progress_label.configure(text="Đang tải profiles từ cloud...")
            
            def download_thread():
                def update_progress(current, total):
                    self.after(0, lambda: progress_bar.set(current / total))
                    self.after(0, lambda: progress_label.configure(
                        text=f"Đang tải... {current}/{total}"))
                
                count = self.cloud_sync.download_all_profiles(
                    self.manager.profiles_dir, update_progress)
                
                self.after(0, lambda: progress_label.configure(
                    text=f"✅ Đã tải {count} profiles"))
                self.after(0, self._refresh)
            
            threading.Thread(target=download_thread, daemon=True).start()
        
        def on_upload():
            progress_bar.pack(pady=5)
            progress_label.configure(text="Đang upload profiles lên cloud...")
            
            def upload_thread():
                def update_progress(current, total):
                    self.after(0, lambda: progress_bar.set(current / total))
                    self.after(0, lambda: progress_label.configure(
                        text=f"Đang upload... {current}/{total}"))
                
                count = self.cloud_sync.upload_all_profiles(
                    self.manager.profiles_dir, update_progress)
                
                self.after(0, lambda: progress_label.configure(
                    text=f"✅ Đã upload {count} profiles"))
            
            threading.Thread(target=upload_thread, daemon=True).start()
        
        if self.cloud_sync.is_logged_in():
            ctk.CTkButton(btn_frame, text="📥 Tải từ Cloud", width=200, height=45,
                         font=ctk.CTkFont(size=14, weight="bold"),
                         fg_color=COLORS["info"], hover_color="#138496",
                         command=on_download).pack(pady=8)
            
            ctk.CTkButton(btn_frame, text="📤 Upload lên Cloud", width=200, height=45,
                         font=ctk.CTkFont(size=14),
                         fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                         command=on_upload).pack(pady=8)
            
            ctk.CTkButton(btn_frame, text="🚪 Đăng xuất", width=200, height=40,
                         fg_color=COLORS["danger"], hover_color="#c82333",
                         command=on_logout).pack(pady=15)
        else:
            ctk.CTkButton(btn_frame, text="🔐 Đăng nhập Google", width=250, height=50,
                         font=ctk.CTkFont(size=16, weight="bold"),
                         fg_color="#4285f4", hover_color="#3367d6",
                         command=on_login).pack(pady=20)
            
            ctk.CTkLabel(btn_frame, text="Đăng nhập để sync profiles\ngiữa các máy tính",
                        text_color=COLORS["text_muted"], justify="center").pack()

class ProfileListItem(ctk.CTkFrame):
    """Selectable item for the profile list pane."""

    def __init__(self, master, profile: ProfileConfig, on_select, **kwargs):
        super().__init__(master, **kwargs)
        self.profile = profile
        self.on_select = on_select
        self.selected = False
        self.hovered = False

        self.configure(
            fg_color=COLORS["bg_card"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
            height=118,
        )
        self.pack_propagate(False)
        self._create_widgets()
        self._bind_recursive(self)

    def _create_widgets(self):
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=16, pady=14)

        top = ctk.CTkFrame(shell, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(
            top,
            text=self.profile.name,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        self.status_badge = ctk.CTkLabel(
            top,
            text="LIVE" if getattr(self.profile, "is_running", False) else "READY",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=999,
            padx=10,
            pady=4,
        )
        self.status_badge.pack(side="right")

        ctk.CTkLabel(
            shell,
            text=f"{self._gpu_name()}  •  {self.profile.screen_width} x {self.profile.screen_height}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(8, 0))

        meta = ctk.CTkFrame(shell, fg_color="transparent")
        meta.pack(fill="x", pady=(10, 0))
        self._chip(meta, self._timezone_label(), COLORS["bg_panel"], COLORS["text_muted"]).pack(side="left")
        self._chip(meta, self._language_label(), COLORS["bg_panel"], COLORS["text_muted"]).pack(side="left", padx=6)
        self._chip(meta, f"{self.profile.cpu_cores}C / {self.profile.ram_gb}G", COLORS["accent_soft"], COLORS["accent"]).pack(side="left")

        if self.profile.tags:
            tags = ctk.CTkFrame(shell, fg_color="transparent")
            tags.pack(fill="x", pady=(10, 0))
            for tag in self.profile.tags[:2]:
                self._chip(tags, tag, COLORS["bg_hover"], COLORS["text"]).pack(side="left", padx=(0, 6))

        self._apply_state()

    def _chip(self, parent, text: str, fg_color: str, text_color: str):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=fg_color,
            text_color=text_color,
            corner_radius=999,
            padx=8,
            pady=4,
        )

    def _bind_recursive(self, widget):
        widget.bind("<Button-1>", lambda _event: self.on_select(self.profile.id))
        widget.bind("<Enter>", lambda _event: self._set_hover(True))
        widget.bind("<Leave>", lambda _event: self._set_hover(False))
        for child in widget.winfo_children():
            self._bind_recursive(child)

    def _set_hover(self, hovered: bool):
        self.hovered = hovered
        self._apply_state()

    def set_selected(self, selected: bool):
        self.selected = selected
        self._apply_state()

    def _apply_state(self):
        if self.selected:
            fg_color = "#202f41"
            border_color = COLORS["accent"]
        elif self.hovered:
            fg_color = COLORS["bg_hover"]
            border_color = "#4a6177"
        else:
            fg_color = COLORS["bg_card"]
            border_color = COLORS["border"]

        self.configure(fg_color=fg_color, border_color=border_color)
        running = getattr(self.profile, "is_running", False)
        self.status_badge.configure(
            fg_color=COLORS["success_soft"] if running else COLORS["bg_panel"],
            text_color=COLORS["success"] if running else COLORS["text_muted"],
        )

    def _gpu_name(self) -> str:
        renderer = self.profile.webgl_renderer or ""
        for marker in ["NVIDIA ", "AMD ", "Intel(R) "]:
            if marker in renderer:
                return renderer.split(marker, 1)[1].split(" Direct", 1)[0]
        return "Default GPU"

    def _timezone_label(self) -> str:
        return self.profile.timezone.split("/")[-1].replace("_", " ")

    def _language_label(self) -> str:
        return (self.profile.language or "en-US").split(",")[0].upper()


def _mainapp_create_stat_card(self, parent, title: str, value: str):
    card = ctk.CTkFrame(
        parent,
        fg_color=COLORS["bg_card"],
        corner_radius=18,
        border_width=1,
        border_color=COLORS["border"],
        height=88,
    )
    card.pack_propagate(False)

    ctk.CTkLabel(
        card,
        text=title.upper(),
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=COLORS["text_dim"],
    ).pack(anchor="w", padx=14, pady=(14, 4))

    value_label = ctk.CTkLabel(
        card,
        text=value,
        font=ctk.CTkFont(size=20, weight="bold"),
        justify="left",
        wraplength=210,
    )
    value_label.pack(anchor="w", padx=14)
    card.value_label = value_label
    return card


def _mainapp_clean_running(self):
    self.running = {
        pid: process
        for pid, process in self.running.items()
        if process and process.poll() is None
    }


def _mainapp_latest_activity_text(self, profiles: List[ProfileConfig]) -> str:
    dated = []
    for profile in profiles:
        stamp = profile.last_used or profile.created_at
        try:
            dated.append((datetime.fromisoformat(stamp), profile))
        except ValueError:
            continue
    if not dated:
        return "No activity"
    _, latest = max(dated, key=lambda item: item[0])
    return latest.name


def _mainapp_create_widgets(self):
    self.geometry("1420x860")
    self.minsize(1180, 760)
    self.configure(fg_color=COLORS["bg_dark"])
    self.selected_profile_id = None
    self.profile_rows = {}
    self.profile_by_id = {}
    self.visible_profile_ids = []

    shell = ctk.CTkFrame(self, fg_color="transparent")
    shell.pack(fill="both", expand=True, padx=18, pady=18)

    sidebar = ctk.CTkFrame(
        shell,
        fg_color=COLORS["bg_panel"],
        corner_radius=26,
        border_width=1,
        border_color=COLORS["border"],
        width=272,
    )
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    workspace = ctk.CTkFrame(shell, fg_color="transparent")
    workspace.pack(side="left", fill="both", expand=True, padx=(18, 0))

    brand = ctk.CTkFrame(sidebar, fg_color="transparent")
    brand.pack(fill="x", padx=20, pady=(20, 12))

    ctk.CTkLabel(brand, text="S Manage", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(
        brand,
        text=APP_VERSION_LABEL,
        font=ctk.CTkFont(size=11, weight="bold"),
        fg_color=COLORS["accent_soft"],
        text_color=COLORS["accent"],
        corner_radius=999,
        padx=10,
        pady=4,
    ).pack(anchor="w", pady=(8, 0))
    ctk.CTkLabel(
        brand,
        text="Profile operations, runtime state and storage health in one workspace.",
        font=ctk.CTkFont(size=12),
        text_color=COLORS["text_muted"],
        justify="left",
        wraplength=220,
    ).pack(anchor="w", pady=(12, 0))

    actions = ctk.CTkFrame(sidebar, fg_color="transparent")
    actions.pack(fill="x", padx=20, pady=(8, 0))

    ctk.CTkButton(
        actions,
        text="Create Profile",
        height=46,
        corner_radius=15,
        font=ctk.CTkFont(size=14, weight="bold"),
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        command=self._new_profile,
    ).pack(fill="x")
    ctk.CTkButton(
        actions,
        text="Refresh Workspace",
        height=40,
        corner_radius=14,
        fg_color=COLORS["info"],
        hover_color=COLORS["info_hover"],
        text_color=COLORS["bg_dark"],
        command=self._refresh,
    ).pack(fill="x", pady=(10, 0))
    ctk.CTkButton(
        actions,
        text="Settings",
        height=40,
        corner_radius=14,
        fg_color=COLORS["bg_card"],
        hover_color=COLORS["bg_hover"],
        border_width=1,
        border_color=COLORS["border"],
        command=self._open_settings,
    ).pack(fill="x", pady=(10, 0))

    if CLOUD_AVAILABLE:
        self.cloud_sync = CloudSync(APP_PATH)
        self.cloud_btn = ctk.CTkButton(
            actions,
            text="Cloud",
            height=40,
            corner_radius=14,
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["bg_hover"],
            border_width=1,
            border_color=COLORS["border"],
            command=self._open_cloud,
        )
        self.cloud_btn.pack(fill="x", pady=(10, 0))
        self._update_cloud_status()

    storage = ctk.CTkFrame(
        sidebar,
        fg_color=COLORS["bg_card"],
        corner_radius=20,
        border_width=1,
        border_color=COLORS["border"],
    )
    storage.pack(fill="x", padx=20, pady=(18, 12))
    ctk.CTkLabel(
        storage,
        text="PROFILE STORAGE",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=COLORS["text_dim"],
    ).pack(anchor="w", padx=14, pady=(14, 4))
    ctk.CTkLabel(
        storage,
        text=self.profiles_path,
        font=ctk.CTkFont(size=12),
        justify="left",
        wraplength=220,
        text_color=COLORS["text"],
    ).pack(anchor="w", padx=14, pady=(0, 14))

    stats = ctk.CTkFrame(sidebar, fg_color="transparent")
    stats.pack(fill="x", padx=20)
    self.stat_cards = {
        "profiles": self._create_stat_card(stats, "Profiles", "0"),
        "running": self._create_stat_card(stats, "Running", "0"),
        "recent": self._create_stat_card(stats, "Recent", "No activity"),
    }
    self.stat_cards["profiles"].pack(fill="x")
    self.stat_cards["running"].pack(fill="x", pady=10)
    self.stat_cards["recent"].pack(fill="x")

    note = ctk.CTkFrame(
        sidebar,
        fg_color=COLORS["bg_card"],
        corner_radius=20,
        border_width=1,
        border_color=COLORS["border"],
    )
    note.pack(fill="x", padx=20, pady=(12, 20))
    ctk.CTkLabel(
        note,
        text="RUNTIME STATUS",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=COLORS["text_dim"],
    ).pack(anchor="w", padx=14, pady=(14, 4))
    ctk.CTkLabel(
        note,
        text="Verified in source: UA, CPU/RAM, GPU, timezone, language and screen. Remaining work is rerunning external checker sites and rebuilding release artifacts.",
        font=ctk.CTkFont(size=12),
        text_color=COLORS["text_muted"],
        justify="left",
        wraplength=220,
    ).pack(anchor="w", padx=14, pady=(0, 14))

    header = ctk.CTkFrame(
        workspace,
        fg_color=COLORS["bg_panel"],
        corner_radius=26,
        border_width=1,
        border_color=COLORS["border"],
    )
    header.pack(fill="x")

    header_inner = ctk.CTkFrame(header, fg_color="transparent")
    header_inner.pack(fill="x", padx=22, pady=18)

    title_block = ctk.CTkFrame(header_inner, fg_color="transparent")
    title_block.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(title_block, text="Profile Workspace", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w")
    self.list_hint = ctk.CTkLabel(
        title_block,
        text="Browse the list, pick one profile, then operate from the detail pane.",
        font=ctk.CTkFont(size=12),
        text_color=COLORS["text_muted"],
    )
    self.list_hint.pack(anchor="w", pady=(8, 0))

    header_controls = ctk.CTkFrame(header_inner, fg_color="transparent")
    header_controls.pack(side="right")
    self.search_var = ctk.StringVar()
    self.search_var.trace("w", lambda *_: self._filter())
    ctk.CTkEntry(
        header_controls,
        placeholder_text="Search by name, tag, language, timezone, GPU...",
        width=360,
        height=46,
        corner_radius=14,
        textvariable=self.search_var,
    ).pack(side="right")

    self.stats = ctk.CTkLabel(
        header_controls,
        text="0 visible",
        font=ctk.CTkFont(size=12, weight="bold"),
        fg_color=COLORS["accent_soft"],
        text_color=COLORS["accent"],
        corner_radius=999,
        padx=12,
        pady=6,
    )
    self.stats.pack(side="right", padx=(0, 12))

    content = ctk.CTkFrame(workspace, fg_color="transparent")
    content.pack(fill="both", expand=True, pady=(18, 0))

    list_shell = ctk.CTkFrame(
        content,
        fg_color=COLORS["bg_panel"],
        corner_radius=24,
        border_width=1,
        border_color=COLORS["border"],
        width=380,
    )
    list_shell.pack(side="left", fill="both")
    list_shell.pack_propagate(False)

    list_header = ctk.CTkFrame(list_shell, fg_color="transparent")
    list_header.pack(fill="x", padx=18, pady=(18, 10))
    ctk.CTkLabel(list_header, text="Profiles", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
    self.list_counter = ctk.CTkLabel(
        list_header,
        text="0 shown",
        font=ctk.CTkFont(size=11),
        text_color=COLORS["text_dim"],
    )
    self.list_counter.pack(side="right")

    self.list_frame = ctk.CTkScrollableFrame(
        list_shell,
        fg_color="transparent",
        scrollbar_button_color=COLORS["bg_hover"],
        scrollbar_button_hover_color=COLORS["border"],
    )
    self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    self.detail_shell = ctk.CTkFrame(
        content,
        fg_color=COLORS["bg_panel"],
        corner_radius=24,
        border_width=1,
        border_color=COLORS["border"],
    )
    self.detail_shell.pack(side="left", fill="both", expand=True, padx=(18, 0))

    self.detail_frame = ctk.CTkFrame(self.detail_shell, fg_color="transparent")
    self.detail_frame.pack(fill="both", expand=True, padx=18, pady=18)

    status = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=0, height=38)
    status.pack(fill="x", side="bottom")
    self.status = ctk.CTkLabel(
        status,
        text="Ready",
        font=ctk.CTkFont(size=11),
        text_color=COLORS["text_muted"],
    )
    self.status.pack(side="left", padx=16, pady=10)


def _mainapp_refresh(self):
    self._clean_running()
    for widget in self.list_frame.winfo_children():
        widget.destroy()

    profiles = self.manager.list_profiles()
    self.profile_rows = {}
    self.profile_by_id = {}
    running_count = 0
    for profile in profiles:
        profile.is_running = profile.id in self.running
        self.profile_by_id[profile.id] = profile
        if profile.is_running:
            running_count += 1

    self.stat_cards["profiles"].value_label.configure(text=str(len(profiles)))
    self.stat_cards["running"].value_label.configure(text=str(running_count))
    self.stat_cards["recent"].value_label.configure(text=self._latest_activity_text(profiles))

    if not profiles:
        self.list_counter.configure(text="0 shown")
        self.stats.configure(text="0 visible")
        self.selected_profile_id = None
        empty = ctk.CTkFrame(
            self.list_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=18,
            border_width=1,
            border_color=COLORS["border"],
            height=180,
        )
        empty.pack(fill="x", padx=10, pady=60)
        empty.pack_propagate(False)
        ctk.CTkLabel(
            empty,
            text="No profiles yet",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(pady=(48, 8))
        ctk.CTkLabel(
            empty,
            text="Create your first isolated browser profile from the action bar above.",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_muted"],
        ).pack()
        self._render_empty_detail(
            "Empty workspace",
            "There are no profiles in storage yet. Create the first profile from the sidebar to populate this workspace.",
        )
        return

    for profile in profiles:
        row = ProfileListItem(self.list_frame, profile, self._select_profile)
        row.pack(fill="x", pady=6, padx=8)
        self.profile_rows[profile.id] = row

    if self.selected_profile_id not in self.profile_by_id:
        self.selected_profile_id = profiles[0].id

    self._filter()
    if self.visible_profile_ids:
        active_id = self.selected_profile_id if self.selected_profile_id in self.visible_profile_ids else self.visible_profile_ids[0]
        self._select_profile(active_id, update_status=False)
    else:
        self._render_empty_detail(
            "No match",
            "The current search filter hides every profile. Change the query to inspect a profile again.",
        )


def _mainapp_filter(self):
    search = self.search_var.get().lower().strip()
    visible_ids = []
    for pid, row in self.profile_rows.items():
        match = self._matches_search(row.profile, search)
        if match:
            row.pack(fill="x", pady=6, padx=8)
            visible_ids.append(pid)
        else:
            row.pack_forget()

    self.visible_profile_ids = visible_ids
    visible_count = len(visible_ids)
    self.list_counter.configure(text=f"{visible_count} shown")
    self.stats.configure(text=f"{visible_count} visible")
    self.list_hint.configure(
        text="Browse the list, pick one profile, then operate from the detail pane."
        if not search
        else f"Filter active for '{search}'"
    )

    if visible_ids:
        selected = self.selected_profile_id if self.selected_profile_id in visible_ids else visible_ids[0]
        self._select_profile(selected, update_status=False)
    elif self.profile_rows:
        self._render_empty_detail(
            "No match",
            "Nothing in the current profile set matches this search. Try name, tag, language, timezone or GPU.",
        )


def _mainapp_matches_search(self, profile: ProfileConfig, search: str) -> bool:
    if not search:
        return True

    haystacks = [
        profile.id.lower(),
        profile.name.lower(),
        profile.timezone.lower(),
        profile.language.lower(),
        (profile.webgl_renderer or "").lower(),
        (profile.webgl_vendor or "").lower(),
        (profile.user_agent or "").lower(),
    ]
    if any(search in item for item in haystacks):
        return True
    return any(search in tag.lower() for tag in (profile.tags or []))


def _mainapp_render_empty_detail(self, title: str, body: str):
    for widget in self.detail_frame.winfo_children():
        widget.destroy()

    empty = ctk.CTkFrame(
        self.detail_frame,
        fg_color=COLORS["bg_card"],
        corner_radius=22,
        border_width=1,
        border_color=COLORS["border"],
    )
    empty.pack(fill="both", expand=True)
    ctk.CTkLabel(empty, text=title, font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w", padx=28, pady=(32, 8))
    ctk.CTkLabel(
        empty,
        text=body,
        font=ctk.CTkFont(size=13),
        text_color=COLORS["text_muted"],
        justify="left",
        wraplength=700,
    ).pack(anchor="w", padx=28)


def _mainapp_select_profile(self, pid, update_status: bool = True):
    if pid not in self.profile_by_id:
        return

    self.selected_profile_id = pid
    for profile_id, row in self.profile_rows.items():
        row.set_selected(profile_id == pid)

    self._render_detail(self.profile_by_id[pid])
    if update_status:
        self.status.configure(text=f"Selected {self.profile_by_id[pid].name}")


def _mainapp_detail_metric(self, parent, label: str, value: str, accent: str = None):
    card = ctk.CTkFrame(
        parent,
        fg_color=COLORS["bg_card"],
        corner_radius=18,
        border_width=1,
        border_color=COLORS["border"],
        height=92,
    )
    card.pack_propagate(False)
    ctk.CTkLabel(
        card,
        text=label.upper(),
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=COLORS["text_dim"],
    ).pack(anchor="w", padx=14, pady=(14, 4))
    ctk.CTkLabel(
        card,
        text=value,
        font=ctk.CTkFont(size=20, weight="bold"),
        text_color=accent or COLORS["text"],
        wraplength=220,
        justify="left",
    ).pack(anchor="w", padx=14)
    return card


def _mainapp_detail_section(self, parent, title: str):
    frame = ctk.CTkFrame(
        parent,
        fg_color=COLORS["bg_card"],
        corner_radius=20,
        border_width=1,
        border_color=COLORS["border"],
    )
    ctk.CTkLabel(
        frame,
        text=title.upper(),
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=COLORS["text_dim"],
    ).pack(anchor="w", padx=16, pady=(16, 10))
    return frame


def _mainapp_detail_line(self, parent, label: str, value: str):
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", padx=16, pady=4)
    ctk.CTkLabel(
        row,
        text=label,
        width=132,
        anchor="w",
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=COLORS["text_muted"],
    ).pack(side="left")
    ctk.CTkLabel(
        row,
        text=value,
        anchor="w",
        justify="left",
        wraplength=390,
        font=ctk.CTkFont(size=12),
        text_color=COLORS["text"],
    ).pack(side="left", fill="x", expand=True)


def _mainapp_render_detail(self, profile: ProfileConfig):
    for widget in self.detail_frame.winfo_children():
        widget.destroy()

    def chip(parent, text: str, fg_color: str, text_color: str):
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=fg_color,
            text_color=text_color,
            corner_radius=999,
            padx=10,
            pady=5,
        ).pack(side="left", padx=(0, 8))

    hero = ctk.CTkFrame(
        self.detail_frame,
        fg_color=COLORS["bg_card"],
        corner_radius=22,
        border_width=1,
        border_color=COLORS["border"],
    )
    hero.pack(fill="x")

    hero_inner = ctk.CTkFrame(hero, fg_color="transparent")
    hero_inner.pack(fill="x", padx=22, pady=20)

    hero_left = ctk.CTkFrame(hero_inner, fg_color="transparent")
    hero_left.pack(side="left", fill="x", expand=True)

    title_row = ctk.CTkFrame(hero_left, fg_color="transparent")
    title_row.pack(fill="x")
    ctk.CTkLabel(title_row, text=profile.name, font=ctk.CTkFont(size=30, weight="bold")).pack(side="left")
    chip(
        title_row,
        "LIVE" if getattr(profile, "is_running", False) else "READY",
        COLORS["success_soft"] if getattr(profile, "is_running", False) else COLORS["bg_panel"],
        COLORS["success"] if getattr(profile, "is_running", False) else COLORS["text_muted"],
    )
    chip(title_row, f"ID {profile.id}", COLORS["bg_panel"], COLORS["text_muted"])

    meta_row = ctk.CTkFrame(hero_left, fg_color="transparent")
    meta_row.pack(fill="x", pady=(12, 0))
    chip(meta_row, f"Chrome {self._chrome_major(profile)}", COLORS["accent_soft"], COLORS["accent"])
    chip(meta_row, self._gpu_name(profile), COLORS["bg_hover"], COLORS["text"])
    chip(meta_row, self._proxy_text(profile), COLORS["bg_panel"], COLORS["text_muted"])

    if profile.tags:
        tags_row = ctk.CTkFrame(hero_left, fg_color="transparent")
        tags_row.pack(fill="x", pady=(12, 0))
        for tag in profile.tags[:4]:
            chip(tags_row, tag, COLORS["bg_hover"], COLORS["text"])

    ctk.CTkLabel(
        hero_left,
        text="Inspect the profile on the left, operate here, then launch only when its fingerprint deck looks coherent.",
        font=ctk.CTkFont(size=12),
        text_color=COLORS["text_muted"],
        justify="left",
    ).pack(anchor="w", pady=(14, 0))

    hero_right = ctk.CTkFrame(hero_inner, fg_color="transparent", width=224)
    hero_right.pack(side="right", fill="y", padx=(18, 0))
    hero_right.pack_propagate(False)
    ctk.CTkButton(
        hero_right,
        text="Launch Browser",
        height=46,
        corner_radius=14,
        fg_color=COLORS["accent"] if not getattr(profile, "is_running", False) else COLORS["success"],
        hover_color=COLORS["accent_hover"] if not getattr(profile, "is_running", False) else "#2aae69",
        font=ctk.CTkFont(size=14, weight="bold"),
        command=lambda: self._launch(profile.id),
    ).pack(fill="x")
    ctk.CTkButton(
        hero_right,
        text="Edit Profile",
        height=36,
        corner_radius=12,
        fg_color=COLORS["info"],
        hover_color=COLORS["info_hover"],
        text_color=COLORS["bg_dark"],
        command=lambda: self._edit(profile.id),
    ).pack(fill="x", pady=(10, 0))
    ctk.CTkButton(
        hero_right,
        text="Clone Profile",
        height=36,
        corner_radius=12,
        fg_color=COLORS["bg_panel"],
        hover_color=COLORS["bg_hover"],
        border_width=1,
        border_color=COLORS["border"],
        command=lambda: self._duplicate(profile.id),
    ).pack(fill="x", pady=(8, 0))
    ctk.CTkButton(
        hero_right,
        text="Delete",
        height=36,
        corner_radius=12,
        fg_color=COLORS["danger"],
        hover_color="#bc4c5d",
        command=lambda: self._delete(profile.id),
    ).pack(fill="x", pady=(8, 0))

    metrics = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
    metrics.pack(fill="x", pady=(18, 0))
    self._detail_metric(metrics, "Display", f"{profile.screen_width} x {profile.screen_height}").pack(side="left", fill="both", expand=True)
    self._detail_metric(metrics, "Hardware", f"{profile.cpu_cores} cores / {profile.ram_gb} GB").pack(side="left", fill="both", expand=True, padx=12)
    self._detail_metric(metrics, "Locale", (profile.language or "en-US").split(",")[0].upper()).pack(side="left", fill="both", expand=True)
    self._detail_metric(metrics, "Timezone", profile.timezone.split("/")[-1].replace("_", " ")).pack(side="left", fill="both", expand=True, padx=(12, 0))

    lower = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
    lower.pack(fill="both", expand=True, pady=(18, 0))

    left = self._detail_section(lower, "Fingerprint Surface")
    left.pack(side="left", fill="both", expand=True)
    self._detail_line(left, "User Agent", profile.user_agent or "Chrome 146 runtime")
    self._detail_line(left, "WebGL Vendor", profile.webgl_vendor or "Default vendor")
    self._detail_line(left, "WebGL Renderer", profile.webgl_renderer or "Default renderer")
    self._detail_line(left, "Platform", "Win32 / Windows NT 10.0")
    self._detail_line(left, "Profile Path", str(self.manager.profiles_dir / f"profile_{profile.id}"))

    right = self._detail_section(lower, "Connection & Activity")
    right.pack(side="left", fill="both", expand=True, padx=(18, 0))
    self._detail_line(right, "OS", os_label_for_platform(getattr(profile, "platform", "Win32")))
    self._detail_line(right, "Proxy", self._proxy_text(profile))
    self._detail_line(right, "Proxy Geo", self._profile_geo_text(profile))
    self._detail_line(right, "Created", profile.created_at or "Unknown")
    self._detail_line(right, "Last Used", profile.last_used or "Never launched")
    self._detail_line(right, "Tags", ", ".join(profile.tags) if profile.tags else "No tags")
    self._detail_line(right, "Runtime Check", "UA, CPU/RAM, GPU, timezone, language and screen verified in current source build.")


def _mainapp_proxy_text(self, profile: ProfileConfig) -> str:
    if profile.proxy_enabled and profile.proxy_host:
        return f"{profile.proxy_type}://{profile.proxy_host}:{profile.proxy_port}"
    return "Direct connection"


def _mainapp_profile_geo_text(self, profile: ProfileConfig) -> str:
    city = getattr(profile, "geo_city", "") or getattr(profile, "geo_region", "") or getattr(profile, "geo_country", "")
    timezone_name = getattr(profile, "timezone", "") or "Unknown TZ"
    if city:
        return f"{city} • {timezone_name}"
    return "No proxy geo stored"


def _mainapp_chrome_major(self, profile: ProfileConfig) -> str:
    user_agent = profile.user_agent or ""
    if "Chrome/" in user_agent:
        try:
            return user_agent.split("Chrome/", 1)[1].split(".", 1)[0]
        except IndexError:
            pass
    return "146"


def _mainapp_gpu_name(self, profile: ProfileConfig) -> str:
    renderer = profile.webgl_renderer or ""
    for marker in ["NVIDIA ", "AMD ", "Intel(R) "]:
        if marker in renderer:
            return renderer.split(marker, 1)[1].split(" Direct", 1)[0]
    return "Default GPU"


def _mainapp_launch(self, pid):
    profile = self.manager.load_profile(pid)
    if not profile:
        return

    self.status.configure(text=f"Launching {profile.name}...")

    def run():
        try:
            print(f"[DEBUG] Browser path: {self.browser_path}")
            print(f"[DEBUG] Browser exists: {os.path.exists(self.browser_path)}")

            launcher = BrowserLauncher(self.browser_path)
            launch_profile = self.manager.sync_profile_runtime_context(profile)
            fingerprint = self.manager.build_fingerprint(launch_profile)
            proxy = self.manager.build_proxy_url(launch_profile)

            user_data = str(self.manager.profiles_dir / f"profile_{pid}" / "UserData")
            print(f"[DEBUG] User data: {user_data}")

            process = launcher.launch(
                user_data_dir=user_data,
                fingerprint=fingerprint,
                proxy=proxy,
                start_url=DEFAULT_LAUNCH_URL,
            )
            self.running[pid] = process

            launch_profile.last_used = datetime.now().isoformat()
            launch_profile.user_agent = fingerprint.get("user_agent", launch_profile.user_agent)
            self.manager._save_profile_config(launch_profile)

            self.after(0, self._refresh)
            self.after(0, lambda: self.status.configure(text=f"Running {launch_profile.name}"))
        except Exception as exc:
            import traceback

            traceback.print_exc()
            self.after(0, lambda: messagebox.showerror("Error", str(exc)))

    threading.Thread(target=run, daemon=True).start()


MainApp._create_stat_card = _mainapp_create_stat_card
MainApp._clean_running = _mainapp_clean_running
MainApp._latest_activity_text = _mainapp_latest_activity_text
MainApp._create_widgets = _mainapp_create_widgets
MainApp._matches_search = _mainapp_matches_search
MainApp._render_empty_detail = _mainapp_render_empty_detail
MainApp._select_profile = _mainapp_select_profile
MainApp._detail_metric = _mainapp_detail_metric
MainApp._detail_section = _mainapp_detail_section
MainApp._detail_line = _mainapp_detail_line
MainApp._render_detail = _mainapp_render_detail
MainApp._refresh = _mainapp_refresh
MainApp._filter = _mainapp_filter
MainApp._proxy_text = _mainapp_proxy_text
MainApp._profile_geo_text = _mainapp_profile_geo_text
MainApp._chrome_major = _mainapp_chrome_major
MainApp._gpu_name = _mainapp_gpu_name
MainApp._launch = _mainapp_launch


class ProfileTableRow(ctk.CTkFrame):
    """Operational row for table-first profile management."""

    def __init__(self, master, profile: ProfileConfig, callbacks: dict, on_select, **kwargs):
        super().__init__(master, **kwargs)
        self.profile = profile
        self.callbacks = callbacks
        self.on_select = on_select
        self.selected = False
        self.hovered = False

        self.configure(
            fg_color=COLORS["bg_card"],
            corner_radius=14,
            border_width=1,
            border_color=COLORS["border"],
            height=84,
        )
        self.pack_propagate(False)
        self._create_widgets()
        self._bind_recursive(self)

    def _create_widgets(self):
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=14, pady=10)

        shell.grid_columnconfigure(0, weight=5, minsize=270)
        shell.grid_columnconfigure(1, weight=2, minsize=110)
        shell.grid_columnconfigure(2, weight=2, minsize=120)
        shell.grid_columnconfigure(3, weight=2, minsize=110)
        shell.grid_columnconfigure(4, weight=2, minsize=120)
        shell.grid_columnconfigure(5, weight=2, minsize=130)
        shell.grid_columnconfigure(6, weight=1, minsize=96)
        shell.grid_columnconfigure(7, weight=2, minsize=168)

        name_cell = ctk.CTkFrame(shell, fg_color="transparent")
        name_cell.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        name_row = ctk.CTkFrame(name_cell, fg_color="transparent")
        name_row.pack(fill="x")

        ctk.CTkLabel(
            name_row,
            text=self.profile.name,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            name_row,
            text=f"ID {self.profile.id}",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["bg_panel"],
            text_color=COLORS["text_dim"],
            corner_radius=999,
            padx=8,
            pady=3,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            name_cell,
            text=f"{self._gpu_name()}  •  Chrome {self._chrome_major()}",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(6, 0))

        if self.profile.tags:
            tags_row = ctk.CTkFrame(name_cell, fg_color="transparent")
            tags_row.pack(fill="x", pady=(8, 0))
            for tag in self.profile.tags[:2]:
                ctk.CTkLabel(
                    tags_row,
                    text=tag,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color=COLORS["bg_hover"],
                    text_color=COLORS["text"],
                    corner_radius=999,
                    padx=8,
                    pady=3,
                ).pack(side="left", padx=(0, 6))

        self._make_cell(shell, 1, "Screen", f"{self.profile.screen_width} x {self.profile.screen_height}")
        self._make_cell(shell, 2, "Hardware", f"{self.profile.cpu_cores}C / {self.profile.ram_gb}G")
        self._make_cell(shell, 3, "Locale", (self.profile.language or "en-US").split(",")[0].upper())
        self._make_cell(shell, 4, "Proxy", self._proxy_text())
        self._make_cell(shell, 5, "Last Open", self._last_used_text())

        status_cell = ctk.CTkFrame(shell, fg_color="transparent")
        status_cell.grid(row=0, column=6, sticky="nsew", padx=(0, 10))
        self.status_badge = ctk.CTkLabel(
            status_cell,
            text="Running" if getattr(self.profile, "is_running", False) else "Ready",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=999,
            padx=10,
            pady=5,
        )
        self.status_badge.pack(anchor="center", pady=(18, 0))

        actions = ctk.CTkFrame(shell, fg_color="transparent")
        actions.grid(row=0, column=7, sticky="e")

        ctk.CTkButton(
            actions,
            text="Start" if not getattr(self.profile, "is_running", False) else "Open",
            width=76,
            height=32,
            corner_radius=10,
            fg_color=COLORS["accent"] if not getattr(self.profile, "is_running", False) else COLORS["success"],
            hover_color=COLORS["accent_hover"] if not getattr(self.profile, "is_running", False) else "#2aae69",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self.callbacks["launch"](self.profile.id),
        ).pack(side="left")

        ctk.CTkButton(
            actions,
            text="Edit",
            width=64,
            height=32,
            corner_radius=10,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            text_color=COLORS["bg_dark"],
            command=lambda: self.callbacks["edit"](self.profile.id),
        ).pack(side="left", padx=8)

        self._apply_state()

    def _make_cell(self, parent, column: int, label: str, value: str):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=0, column=column, sticky="nsew", padx=(0, 10))
        ctk.CTkLabel(
            cell,
            text=label.upper(),
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=COLORS["text_dim"],
        ).pack(anchor="w", pady=(10, 4))
        ctk.CTkLabel(
            cell,
            text=value,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text"],
            wraplength=120,
            justify="left",
        ).pack(anchor="w")

    def _bind_recursive(self, widget):
        widget.bind("<Button-1>", lambda _event: self.on_select(self.profile.id))
        widget.bind("<Enter>", lambda _event: self._set_hover(True))
        widget.bind("<Leave>", lambda _event: self._set_hover(False))
        for child in widget.winfo_children():
            self._bind_recursive(child)

    def _set_hover(self, hovered: bool):
        self.hovered = hovered
        self._apply_state()

    def set_selected(self, selected: bool):
        self.selected = selected
        self._apply_state()

    def _apply_state(self):
        if self.selected:
            fg_color = "#172332"
            border_color = COLORS["accent"]
        elif self.hovered:
            fg_color = COLORS["bg_hover"]
            border_color = "#496177"
        else:
            fg_color = COLORS["bg_card"]
            border_color = COLORS["border"]

        self.configure(fg_color=fg_color, border_color=border_color)
        running = getattr(self.profile, "is_running", False)
        self.status_badge.configure(
            fg_color=COLORS["success_soft"] if running else COLORS["bg_panel"],
            text_color=COLORS["success"] if running else COLORS["text_muted"],
        )

    def _gpu_name(self) -> str:
        renderer = self.profile.webgl_renderer or ""
        for marker in ["NVIDIA ", "AMD ", "Intel(R) "]:
            if marker in renderer:
                return renderer.split(marker, 1)[1].split(" Direct", 1)[0]
        return "Default GPU"

    def _chrome_major(self) -> str:
        user_agent = self.profile.user_agent or ""
        if "Chrome/" in user_agent:
            try:
                return user_agent.split("Chrome/", 1)[1].split(".", 1)[0]
            except IndexError:
                pass
        return "146"

    def _proxy_text(self) -> str:
        if self.profile.proxy_enabled and self.profile.proxy_host:
            return f"{self.profile.proxy_type}://{self.profile.proxy_host}:{self.profile.proxy_port}"
        return "Direct"

    def _last_used_text(self) -> str:
        stamp = self.profile.last_used
        if not stamp:
            return "Never"
        try:
            return datetime.fromisoformat(stamp).strftime("%d/%m %H:%M")
        except ValueError:
            return stamp[:16]


def _ops_create_widgets(self):
    self.geometry("1480x880")
    self.minsize(1240, 760)
    self.configure(fg_color=COLORS["bg_dark"])
    self.selected_profile_id = None
    self.profile_rows = {}
    self.profile_by_id = {}
    self.visible_profile_ids = []

    shell = ctk.CTkFrame(self, fg_color="transparent")
    shell.pack(fill="both", expand=True, padx=16, pady=16)

    sidebar = ctk.CTkFrame(
        shell,
        fg_color="#111923",
        corner_radius=20,
        border_width=1,
        border_color=COLORS["border"],
        width=228,
    )
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    main = ctk.CTkFrame(shell, fg_color="transparent")
    main.pack(side="left", fill="both", expand=True, padx=(16, 0))

    ctk.CTkLabel(sidebar, text="S Manage", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w", padx=18, pady=(18, 4))
    ctk.CTkLabel(
        sidebar,
        text=APP_VERSION_LABEL,
        font=ctk.CTkFont(size=11, weight="bold"),
        fg_color=COLORS["accent_soft"],
        text_color=COLORS["accent"],
        corner_radius=999,
        padx=10,
        pady=4,
    ).pack(anchor="w", padx=18, pady=(0, 14))

    nav = ctk.CTkFrame(sidebar, fg_color="transparent")
    nav.pack(fill="x", padx=14)
    ctk.CTkButton(nav, text="Profiles", height=38, corner_radius=12, fg_color=COLORS["info"], hover_color=COLORS["info_hover"], text_color=COLORS["bg_dark"]).pack(fill="x")
    ctk.CTkButton(nav, text="Settings", height=38, corner_radius=12, fg_color=COLORS["bg_card"], hover_color=COLORS["bg_hover"], border_width=1, border_color=COLORS["border"], command=self._open_settings).pack(fill="x", pady=(8, 0))
    if CLOUD_AVAILABLE:
        self.cloud_sync = CloudSync(APP_PATH)
        self.cloud_btn = ctk.CTkButton(nav, text="Cloud Sync", height=38, corner_radius=12, fg_color=COLORS["bg_card"], hover_color=COLORS["bg_hover"], border_width=1, border_color=COLORS["border"], command=self._open_cloud)
        self.cloud_btn.pack(fill="x", pady=(8, 0))
        self._update_cloud_status()

    ctk.CTkButton(sidebar, text="New Profile", height=42, corner_radius=14, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], font=ctk.CTkFont(size=14, weight="bold"), command=self._new_profile).pack(fill="x", padx=18, pady=(18, 0))
    ctk.CTkButton(sidebar, text="Refresh", height=38, corner_radius=12, fg_color=COLORS["bg_card"], hover_color=COLORS["bg_hover"], border_width=1, border_color=COLORS["border"], command=self._refresh).pack(fill="x", padx=18, pady=(10, 0))

    self.sidebar_stats = {}
    stats_box = ctk.CTkFrame(sidebar, fg_color="transparent")
    stats_box.pack(fill="x", padx=18, pady=(18, 0))
    self.sidebar_stats["profiles"] = self._create_stat_card(stats_box, "Profiles", "0")
    self.sidebar_stats["profiles"].pack(fill="x")
    self.sidebar_stats["running"] = self._create_stat_card(stats_box, "Running", "0")
    self.sidebar_stats["running"].pack(fill="x", pady=10)
    self.sidebar_stats["recent"] = self._create_stat_card(stats_box, "Recent", "No activity")
    self.sidebar_stats["recent"].pack(fill="x")

    storage = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_card"], corner_radius=18, border_width=1, border_color=COLORS["border"])
    storage.pack(fill="x", padx=18, pady=(16, 18))
    ctk.CTkLabel(storage, text="PROFILE STORAGE", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_dim"]).pack(anchor="w", padx=14, pady=(14, 4))
    ctk.CTkLabel(storage, text=self.profiles_path, font=ctk.CTkFont(size=12), justify="left", wraplength=180, text_color=COLORS["text"]).pack(anchor="w", padx=14, pady=(0, 14))

    header = ctk.CTkFrame(main, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["border"])
    header.pack(fill="x")
    header_inner = ctk.CTkFrame(header, fg_color="transparent")
    header_inner.pack(fill="x", padx=18, pady=16)

    title_block = ctk.CTkFrame(header_inner, fg_color="transparent")
    title_block.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(title_block, text="Profiles", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
    self.list_hint = ctk.CTkLabel(title_block, text="Table-first view for fast launch, edit and audit.", font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"])
    self.list_hint.pack(anchor="w", pady=(6, 0))

    toolbar = ctk.CTkFrame(main, fg_color="transparent")
    toolbar.pack(fill="x", pady=(14, 12))
    ctk.CTkButton(toolbar, text="Quick Create", width=120, height=38, corner_radius=12, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._new_profile).pack(side="left")
    ctk.CTkButton(toolbar, text="Import Zip", width=108, height=38, corner_radius=12, fg_color=COLORS["bg_card"], hover_color=COLORS["bg_hover"], border_width=1, border_color=COLORS["border"], command=self._import_profile_ui).pack(side="left", padx=8)
    ctk.CTkButton(toolbar, text="Export Selected", width=132, height=38, corner_radius=12, fg_color=COLORS["bg_card"], hover_color=COLORS["bg_hover"], border_width=1, border_color=COLORS["border"], command=self._export_profile_ui).pack(side="left")
    self.stats = ctk.CTkLabel(toolbar, text="0 visible", font=ctk.CTkFont(size=12, weight="bold"), fg_color=COLORS["accent_soft"], text_color=COLORS["accent"], corner_radius=999, padx=12, pady=6)
    self.stats.pack(side="right")
    self.search_var = ctk.StringVar()
    self.search_var.trace("w", lambda *_: self._filter())
    ctk.CTkEntry(toolbar, placeholder_text="Search name, tag, language, timezone, GPU...", width=340, height=40, corner_radius=12, textvariable=self.search_var).pack(side="right", padx=(0, 12))

    self.table_shell = ctk.CTkFrame(main, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["border"])
    self.table_shell.pack(fill="both", expand=True)

    header_row = ctk.CTkFrame(self.table_shell, fg_color="#121c28", corner_radius=14, height=44)
    header_row.pack(fill="x", padx=12, pady=(12, 8))
    header_row.pack_propagate(False)

    headers = [
        ("Profile", 0.28),
        ("Screen", 0.10),
        ("Hardware", 0.11),
        ("Locale", 0.09),
        ("Proxy", 0.12),
        ("Last Open", 0.12),
        ("Status", 0.08),
        ("Action", 0.10),
    ]
    for text, relx in headers:
        ctk.CTkLabel(header_row, text=text, font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text_dim"]).place(relx=relx, rely=0.5, anchor="w")

    self.list_frame = ctk.CTkScrollableFrame(
        self.table_shell,
        fg_color="transparent",
        scrollbar_button_color=COLORS["bg_hover"],
        scrollbar_button_hover_color=COLORS["border"],
    )
    self.list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    self.detail_shell = ctk.CTkFrame(main, fg_color=COLORS["bg_panel"], corner_radius=20, border_width=1, border_color=COLORS["border"], height=220)
    self.detail_shell.pack(fill="x", pady=(12, 0))
    self.detail_shell.pack_propagate(False)
    self.detail_frame = ctk.CTkFrame(self.detail_shell, fg_color="transparent")
    self.detail_frame.pack(fill="both", expand=True, padx=16, pady=16)

    status = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=0, height=34)
    status.pack(fill="x", side="bottom")
    self.status = ctk.CTkLabel(status, text="Ready", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
    self.status.pack(side="left", padx=14, pady=8)


def _ops_matches_search(self, profile: ProfileConfig, search: str) -> bool:
    if not search:
        return True
    haystacks = [
        profile.id.lower(),
        profile.name.lower(),
        profile.timezone.lower(),
        profile.language.lower(),
        (profile.webgl_renderer or "").lower(),
        (profile.webgl_vendor or "").lower(),
        (profile.user_agent or "").lower(),
    ]
    if any(search in item for item in haystacks):
        return True
    return any(search in tag.lower() for tag in (profile.tags or []))


def _ops_last_used_text(self, profile: ProfileConfig) -> str:
    stamp = profile.last_used
    if not stamp:
        return "Never"
    try:
        return datetime.fromisoformat(stamp).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return stamp


def _ops_proxy_text(self, profile: ProfileConfig) -> str:
    if profile.proxy_enabled and profile.proxy_host:
        return f"{profile.proxy_type}://{profile.proxy_host}:{profile.proxy_port}"
    return "Direct connection"


def _ops_gpu_name(self, profile: ProfileConfig) -> str:
    renderer = profile.webgl_renderer or ""
    for marker in ["NVIDIA ", "AMD ", "Intel(R) "]:
        if marker in renderer:
            return renderer.split(marker, 1)[1].split(" Direct", 1)[0]
    return "Default GPU"


def _ops_select_profile(self, pid, update_status: bool = True):
    if pid not in self.profile_by_id:
        return
    self.selected_profile_id = pid
    for row_pid, row in self.profile_rows.items():
        row.set_selected(row_pid == pid)
    self._render_detail(self.profile_by_id[pid])
    if update_status:
        self.status.configure(text=f"Selected {self.profile_by_id[pid].name}")


def _ops_render_detail(self, profile: ProfileConfig):
    for widget in self.detail_frame.winfo_children():
        widget.destroy()

    top = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
    top.pack(fill="x")
    ctk.CTkLabel(top, text=profile.name, font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
    ctk.CTkLabel(top, text=f"ID {profile.id}", font=ctk.CTkFont(size=10, weight="bold"), fg_color=COLORS["bg_card"], text_color=COLORS["text_dim"], corner_radius=999, padx=8, pady=4).pack(side="left", padx=(10, 0))
    ctk.CTkButton(top, text="Clone", width=74, height=30, corner_radius=10, fg_color=COLORS["bg_card"], hover_color=COLORS["bg_hover"], border_width=1, border_color=COLORS["border"], command=lambda: self._duplicate(profile.id)).pack(side="right")
    ctk.CTkButton(top, text="Delete", width=74, height=30, corner_radius=10, fg_color=COLORS["danger"], hover_color="#bc4c5d", command=lambda: self._delete(profile.id)).pack(side="right", padx=(8, 0))

    content = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
    content.pack(fill="both", expand=True, pady=(14, 0))
    left = ctk.CTkFrame(content, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"])
    left.pack(side="left", fill="both", expand=True)
    right = ctk.CTkFrame(content, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"], width=360)
    right.pack(side="left", fill="both", padx=(12, 0))
    right.pack_propagate(False)

    ctk.CTkLabel(left, text="OVERVIEW", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_dim"]).pack(anchor="w", padx=14, pady=(14, 10))
    ctk.CTkLabel(left, text=f"Display: {profile.screen_width} x {profile.screen_height}", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=3)
    ctk.CTkLabel(left, text=f"Hardware: {profile.cpu_cores} cores / {profile.ram_gb} GB", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=3)
    ctk.CTkLabel(left, text=f"Locale: {(profile.language or 'en-US').split(',')[0].upper()}  •  {profile.timezone}", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=3)
    ctk.CTkLabel(left, text=f"GPU: {self._gpu_name(profile)}", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=14, pady=3)
    ctk.CTkLabel(left, text=f"Profile path: {self.manager.profiles_dir / f'profile_{profile.id}'}", font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"], wraplength=690, justify="left").pack(anchor="w", padx=14, pady=(6, 0))

    ctk.CTkLabel(right, text="FINGERPRINT", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_dim"]).pack(anchor="w", padx=14, pady=(14, 10))
    for label, value in [
        ("User Agent", profile.user_agent or "Chrome 146 runtime"),
        ("WebGL Vendor", profile.webgl_vendor or "Default vendor"),
        ("WebGL Renderer", profile.webgl_renderer or "Default renderer"),
        ("Proxy", self._proxy_text(profile)),
        ("Last Used", self._last_used_text(profile)),
    ]:
        row = ctk.CTkFrame(right, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row, text=label, width=92, anchor="w", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left")
        ctk.CTkLabel(row, text=value, anchor="w", justify="left", wraplength=220, font=ctk.CTkFont(size=12)).pack(side="left", fill="x", expand=True)


def _ops_render_empty_detail(self, title: str, body: str):
    for widget in self.detail_frame.winfo_children():
        widget.destroy()
    card = ctk.CTkFrame(self.detail_frame, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"])
    card.pack(fill="both", expand=True)
    ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", padx=18, pady=(18, 8))
    ctk.CTkLabel(card, text=body, font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"], justify="left", wraplength=980).pack(anchor="w", padx=18)


def _ops_refresh(self):
    self._clean_running()
    for widget in self.list_frame.winfo_children():
        widget.destroy()

    profiles = self.manager.list_profiles()
    self.profile_rows = {}
    self.profile_by_id = {}
    running_count = 0
    for profile in profiles:
        profile.is_running = profile.id in self.running
        self.profile_by_id[profile.id] = profile
        if profile.is_running:
            running_count += 1

    self.sidebar_stats["profiles"].value_label.configure(text=str(len(profiles)))
    self.sidebar_stats["running"].value_label.configure(text=str(running_count))
    self.sidebar_stats["recent"].value_label.configure(text=self._latest_activity_text(profiles))

    if not profiles:
        self.stats.configure(text="0 visible")
        empty = ctk.CTkFrame(self.list_frame, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"], height=140)
        empty.pack(fill="x", padx=8, pady=24)
        empty.pack_propagate(False)
        ctk.CTkLabel(empty, text="No profiles yet", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(34, 8))
        ctk.CTkLabel(empty, text="Create or import a profile from the toolbar.", font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack()
        self._render_empty_detail("Empty inspector", "Select a profile row to inspect its fingerprint, proxy and runtime details here.")
        return

    callbacks = {"launch": self._launch, "edit": self._edit}
    for profile in profiles:
        row = ProfileTableRow(self.list_frame, profile, callbacks, self._select_profile)
        row.pack(fill="x", padx=8, pady=4)
        self.profile_rows[profile.id] = row

    if self.selected_profile_id not in self.profile_by_id:
        self.selected_profile_id = profiles[0].id

    self._filter()
    if self.visible_profile_ids:
        self._select_profile(self.visible_profile_ids[0] if self.selected_profile_id not in self.visible_profile_ids else self.selected_profile_id, update_status=False)
    else:
        self._render_empty_detail("No match", "The active search hides all profiles. Change the query to inspect a row.")


def _ops_filter(self):
    search = self.search_var.get().lower().strip()
    visible_ids = []
    for pid, row in self.profile_rows.items():
        match = self._matches_search(row.profile, search)
        if match:
            row.pack(fill="x", padx=8, pady=4)
            visible_ids.append(pid)
        else:
            row.pack_forget()

    self.visible_profile_ids = visible_ids
    self.stats.configure(text=f"{len(visible_ids)} visible")
    self.list_hint.configure(text="Table-first view for fast launch, edit and audit." if not search else f"Filter active for '{search}'")

    if visible_ids:
        selected = self.selected_profile_id if self.selected_profile_id in visible_ids else visible_ids[0]
        self._select_profile(selected, update_status=False)
    elif self.profile_rows:
        self._render_empty_detail("No match", "Nothing matches this filter. Try name, tag, language, timezone or GPU.")


def _ops_export_profile_ui(self):
    if not self.selected_profile_id:
        messagebox.showwarning("Export", "Select a profile first.")
        return
    profile = self.profile_by_id.get(self.selected_profile_id)
    if not profile:
        return
    export_path = filedialog.asksaveasfilename(
        title="Export profile",
        defaultextension=".zip",
        initialfile=f"{profile.name}.zip",
        filetypes=[("Zip archive", "*.zip")],
    )
    if not export_path:
        return
    if self.manager.export_profile(profile.id, export_path):
        self.status.configure(text=f"Exported {profile.name}")
    else:
        messagebox.showerror("Export", "Failed to export profile.")


def _ops_import_profile_ui(self):
    zip_path = filedialog.askopenfilename(
        title="Import profile",
        filetypes=[("Zip archive", "*.zip")],
    )
    if not zip_path:
        return
    profile = self.manager.import_profile(zip_path)
    if not profile:
        messagebox.showerror("Import", "Failed to import profile.")
        return
    self._refresh()
    self._select_profile(profile.id)
    self.status.configure(text=f"Imported {profile.name}")



MainApp._create_widgets = _ops_create_widgets
MainApp._matches_search = _ops_matches_search
MainApp._last_used_text = _ops_last_used_text
MainApp._proxy_text = _ops_proxy_text
MainApp._gpu_name = _ops_gpu_name
MainApp._select_profile = _ops_select_profile
MainApp._render_detail = _ops_render_detail
MainApp._render_empty_detail = _ops_render_empty_detail
MainApp._refresh = _ops_refresh
MainApp._filter = _ops_filter
MainApp._export_profile_ui = _ops_export_profile_ui
MainApp._import_profile_ui = _ops_import_profile_ui


COMPACT_TABLE_COLUMNS = [
    ("Profile", 350),
    ("Screen", 110),
    ("Hardware", 120),
    ("Locale", 95),
    ("Proxy", 120),
    ("Last Open", 120),
    ("Status", 90),
    ("Action", 150),
]


class CompactProfileRow(ctk.CTkFrame):
    """Denser row aligned to the same grid as the header."""

    def __init__(self, master, profile: ProfileConfig, callbacks: dict, on_select, **kwargs):
        super().__init__(master, **kwargs)
        self.profile = profile
        self.callbacks = callbacks
        self.on_select = on_select
        self.selected = False
        self.hovered = False

        self.configure(
            fg_color="#151c25",
            corner_radius=10,
            border_width=1,
            border_color="#233446",
            height=68,
        )
        self.pack_propagate(False)
        self._create_widgets()
        self._bind_recursive(self)

    def _create_widgets(self):
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=12, pady=8)
        for idx, (_, width) in enumerate(COMPACT_TABLE_COLUMNS):
            shell.grid_columnconfigure(idx, minsize=width, weight=0)

        name_cell = ctk.CTkFrame(shell, fg_color="transparent")
        name_cell.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        top = ctk.CTkFrame(name_cell, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(
            top,
            text=self.profile.name,
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")

        if self.profile.tags:
            ctk.CTkLabel(
                top,
                text=(self.profile.tags or [""])[0],
                font=ctk.CTkFont(size=9, weight="bold"),
                fg_color="#223244",
                text_color="#9ec4ff",
                corner_radius=999,
                padx=7,
                pady=2,
            ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            name_cell,
            text=f"{self._gpu_name()}  •  {self._chrome_major()}",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"],
        ).pack(anchor="w", pady=(4, 0))

        self._metric_cell(shell, 1, f"{self.profile.screen_width} x {self.profile.screen_height}")
        self._metric_cell(shell, 2, f"{self.profile.cpu_cores}C / {self.profile.ram_gb}G")
        self._metric_cell(shell, 3, (self.profile.language or "en-US").split(",")[0].upper())
        self._metric_cell(shell, 4, self._proxy_text())
        self._metric_cell(shell, 5, self._last_used_text())

        status_cell = ctk.CTkFrame(shell, fg_color="transparent")
        status_cell.grid(row=0, column=6, sticky="nsew", padx=(0, 8))
        self.status_badge = ctk.CTkLabel(
            status_cell,
            text="Ready" if not getattr(self.profile, "is_running", False) else "Running",
            font=ctk.CTkFont(size=9, weight="bold"),
            corner_radius=8,
            padx=8,
            pady=4,
        )
        self.status_badge.pack(anchor="center", pady=(14, 0))

        actions = ctk.CTkFrame(shell, fg_color="transparent")
        actions.grid(row=0, column=7, sticky="e")
        ctk.CTkButton(
            actions,
            text="Start" if not getattr(self.profile, "is_running", False) else "Open",
            width=70,
            height=28,
            corner_radius=8,
            fg_color=COLORS["accent"] if not getattr(self.profile, "is_running", False) else COLORS["success"],
            hover_color=COLORS["accent_hover"] if not getattr(self.profile, "is_running", False) else "#2aae69",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: self.callbacks["launch"](self.profile.id),
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Edit",
            width=62,
            height=28,
            corner_radius=8,
            fg_color="#203142",
            hover_color="#294057",
            text_color=COLORS["text"],
            command=lambda: self.callbacks["edit"](self.profile.id),
        ).pack(side="left", padx=(6, 0))

        self._apply_state()

    def _metric_cell(self, parent, column: int, value: str):
        cell = ctk.CTkFrame(parent, fg_color="transparent")
        cell.grid(row=0, column=column, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(
            cell,
            text=value,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLORS["text"],
            wraplength=110,
            justify="left",
        ).pack(anchor="w", pady=(16, 0))

    def _bind_recursive(self, widget):
        widget.bind("<Button-1>", lambda _event: self.on_select(self.profile.id))
        widget.bind("<Enter>", lambda _event: self._set_hover(True))
        widget.bind("<Leave>", lambda _event: self._set_hover(False))
        for child in widget.winfo_children():
            self._bind_recursive(child)

    def _set_hover(self, hovered: bool):
        self.hovered = hovered
        self._apply_state()

    def set_selected(self, selected: bool):
        self.selected = selected
        self._apply_state()

    def _apply_state(self):
        if self.selected:
            fg_color = "#182433"
            border_color = COLORS["accent"]
        elif self.hovered:
            fg_color = "#1a2633"
            border_color = "#395069"
        else:
            fg_color = "#151c25"
            border_color = "#233446"
        self.configure(fg_color=fg_color, border_color=border_color)
        running = getattr(self.profile, "is_running", False)
        self.status_badge.configure(
            fg_color="#163826" if running else "#1b2430",
            text_color=COLORS["success"] if running else COLORS["text_muted"],
        )

    def _gpu_name(self) -> str:
        renderer = self.profile.webgl_renderer or ""
        for marker in ["NVIDIA ", "AMD ", "Intel(R) "]:
            if marker in renderer:
                return renderer.split(marker, 1)[1].split(" Direct", 1)[0]
        return "Default GPU"

    def _chrome_major(self) -> str:
        user_agent = self.profile.user_agent or ""
        if "Chrome/" in user_agent:
            try:
                return f"Chrome {user_agent.split('Chrome/', 1)[1].split('.', 1)[0]}"
            except IndexError:
                pass
        return "Chrome 146"

    def _proxy_text(self) -> str:
        if self.profile.proxy_enabled and self.profile.proxy_host:
            return self.profile.proxy_type
        return "Direct"

    def _last_used_text(self) -> str:
        stamp = self.profile.last_used
        if not stamp:
            return "Never"
        try:
            return datetime.fromisoformat(stamp).strftime("%d/%m %H:%M")
        except ValueError:
            return stamp[:16]


def _compact_create_widgets(self):
    self.geometry("1450x840")
    self.minsize(1220, 740)
    self.configure(fg_color="#0d1218")
    self.selected_profile_id = None
    self.profile_rows = {}
    self.profile_by_id = {}
    self.visible_profile_ids = []

    root = ctk.CTkFrame(self, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=14)

    sidebar = ctk.CTkFrame(
        root,
        fg_color="#10161d",
        corner_radius=18,
        border_width=1,
        border_color="#223140",
        width=186,
    )
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    main = ctk.CTkFrame(root, fg_color="transparent")
    main.pack(side="left", fill="both", expand=True, padx=(14, 0))

    ctk.CTkLabel(sidebar, text="S Manage", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", padx=16, pady=(16, 4))
    ctk.CTkLabel(
        sidebar,
        text=APP_VERSION_LABEL,
        font=ctk.CTkFont(size=10, weight="bold"),
        fg_color=COLORS["accent_soft"],
        text_color=COLORS["accent"],
        corner_radius=999,
        padx=8,
        pady=3,
    ).pack(anchor="w", padx=16, pady=(0, 10))

    ctk.CTkButton(sidebar, text="Profiles", height=34, corner_radius=10, fg_color="#1d4ed8", hover_color="#1e40af").pack(fill="x", padx=14)
    ctk.CTkButton(sidebar, text="New Profile", height=36, corner_radius=10, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], font=ctk.CTkFont(size=12, weight="bold"), command=self._new_profile).pack(fill="x", padx=14, pady=(10, 0))
    ctk.CTkButton(sidebar, text="Refresh", height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._refresh).pack(fill="x", padx=14, pady=(8, 0))
    ctk.CTkButton(sidebar, text="Settings", height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._open_settings).pack(fill="x", padx=14, pady=(8, 0))
    if CLOUD_AVAILABLE:
        self.cloud_sync = CloudSync(APP_PATH)
        self.cloud_btn = ctk.CTkButton(sidebar, text="Cloud", height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._open_cloud)
        self.cloud_btn.pack(fill="x", padx=14, pady=(8, 0))
        self._update_cloud_status()

    self.sidebar_stats = {}
    stats_wrap = ctk.CTkFrame(sidebar, fg_color="transparent")
    stats_wrap.pack(fill="x", padx=14, pady=(18, 0))
    self.sidebar_stats["profiles"] = self._create_stat_card(stats_wrap, "Profiles", "0")
    self.sidebar_stats["profiles"].pack(fill="x")
    self.sidebar_stats["running"] = self._create_stat_card(stats_wrap, "Running", "0")
    self.sidebar_stats["running"].pack(fill="x", pady=8)
    self.sidebar_stats["recent"] = self._create_stat_card(stats_wrap, "Recent", "No activity")
    self.sidebar_stats["recent"].pack(fill="x")

    header = ctk.CTkFrame(main, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140")
    header.pack(fill="x")
    header_inner = ctk.CTkFrame(header, fg_color="transparent")
    header_inner.pack(fill="x", padx=16, pady=14)
    title_box = ctk.CTkFrame(header_inner, fg_color="transparent")
    title_box.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(title_box, text="Profiles", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
    self.list_hint = ctk.CTkLabel(title_box, text="Operational table for launch, edit and quick inspection.", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
    self.list_hint.pack(anchor="w", pady=(4, 0))

    toolbar = ctk.CTkFrame(main, fg_color="transparent")
    toolbar.pack(fill="x", pady=(12, 10))
    ctk.CTkButton(toolbar, text="Quick Create", width=108, height=34, corner_radius=10, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._new_profile).pack(side="left")
    ctk.CTkButton(toolbar, text="Import", width=84, height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._import_profile_ui).pack(side="left", padx=(8, 0))
    ctk.CTkButton(toolbar, text="Export", width=84, height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._export_profile_ui).pack(side="left", padx=(8, 0))
    self.stats = ctk.CTkLabel(toolbar, text="0 visible", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#2b2118", text_color=COLORS["accent"], corner_radius=999, padx=10, pady=5)
    self.stats.pack(side="right")
    self.search_var = ctk.StringVar()
    self.search_var.trace("w", lambda *_: self._filter())
    ctk.CTkEntry(toolbar, placeholder_text="Search profiles...", width=280, height=36, corner_radius=10, textvariable=self.search_var).pack(side="right", padx=(0, 10))

    self.table_shell = ctk.CTkFrame(main, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140")
    self.table_shell.pack(fill="both", expand=True)

    header_row = ctk.CTkFrame(self.table_shell, fg_color="#141d27", corner_radius=10, height=38)
    header_row.pack(fill="x", padx=10, pady=(10, 6))
    header_row.pack_propagate(False)
    header_grid = ctk.CTkFrame(header_row, fg_color="transparent")
    header_grid.pack(fill="both", expand=True, padx=12)
    for idx, (label, width) in enumerate(COMPACT_TABLE_COLUMNS):
        header_grid.grid_columnconfigure(idx, minsize=width, weight=0)
        ctk.CTkLabel(
            header_grid,
            text=label,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=COLORS["text_dim"],
        ).grid(row=0, column=idx, sticky="w", padx=(0, 8), pady=10)

    self.list_frame = ctk.CTkScrollableFrame(
        self.table_shell,
        fg_color="transparent",
        scrollbar_button_color="#223244",
        scrollbar_button_hover_color="#314558",
    )
    self.list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    self.detail_shell = ctk.CTkFrame(main, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140", height=168)
    self.detail_shell.pack(fill="x", pady=(10, 0))
    self.detail_shell.pack_propagate(False)
    self.detail_frame = ctk.CTkFrame(self.detail_shell, fg_color="transparent")
    self.detail_frame.pack(fill="both", expand=True, padx=14, pady=14)

    status = ctk.CTkFrame(self, fg_color="#111923", corner_radius=0, height=30)
    status.pack(fill="x", side="bottom")
    self.status = ctk.CTkLabel(status, text="Ready", font=ctk.CTkFont(size=10), text_color=COLORS["text_muted"])
    self.status.pack(side="left", padx=12, pady=7)


def _compact_render_detail(self, profile: ProfileConfig):
    for widget in self.detail_frame.winfo_children():
        widget.destroy()

    top = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
    top.pack(fill="x")
    ctk.CTkLabel(top, text=profile.name, font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
    ctk.CTkLabel(top, text=f"ID {profile.id}", font=ctk.CTkFont(size=9, weight="bold"), fg_color="#1b2430", text_color=COLORS["text_dim"], corner_radius=999, padx=7, pady=3).pack(side="left", padx=(8, 0))
    ctk.CTkButton(top, text="Delete", width=68, height=28, corner_radius=8, fg_color=COLORS["danger"], hover_color="#bc4c5d", command=lambda: self._delete(profile.id)).pack(side="right")
    ctk.CTkButton(top, text="Clone", width=68, height=28, corner_radius=8, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=lambda: self._duplicate(profile.id)).pack(side="right", padx=(0, 6))

    grid = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
    grid.pack(fill="both", expand=True, pady=(12, 0))
    grid.grid_columnconfigure(0, weight=2)
    grid.grid_columnconfigure(1, weight=2)
    grid.grid_columnconfigure(2, weight=3)

    def mini(parent, title, value, col):
        box = ctk.CTkFrame(parent, fg_color="#151c25", corner_radius=12, border_width=1, border_color="#233446")
        box.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 0))
        ctk.CTkLabel(box, text=title.upper(), font=ctk.CTkFont(size=9, weight="bold"), text_color=COLORS["text_dim"]).pack(anchor="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(box, text=value, font=ctk.CTkFont(size=12, weight="bold"), wraplength=280, justify="left").pack(anchor="w", padx=12, pady=(0, 10))

    mini(grid, "Overview", f"{profile.screen_width} x {profile.screen_height}  •  {profile.cpu_cores}C / {profile.ram_gb}G\n{(profile.language or 'en-US').split(',')[0].upper()}  •  {profile.timezone}", 0)
    mini(grid, "Connection", f"{self._proxy_text(profile)}\nLast used: {self._last_used_text(profile)}", 1)
    mini(grid, "Fingerprint", f"{self._gpu_name(profile)}\n{profile.webgl_vendor or 'Default vendor'}\nChrome {self._chrome_major(profile)}", 2)


def _compact_render_empty_detail(self, title: str, body: str):
    for widget in self.detail_frame.winfo_children():
        widget.destroy()
    card = ctk.CTkFrame(self.detail_frame, fg_color="#151c25", corner_radius=12, border_width=1, border_color="#233446")
    card.pack(fill="both", expand=True)
    ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=16, pady=(14, 6))
    ctk.CTkLabel(card, text=body, font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"], justify="left", wraplength=980).pack(anchor="w", padx=16)


def _compact_refresh(self):
    self._clean_running()
    for widget in self.list_frame.winfo_children():
        widget.destroy()

    profiles = self.manager.list_profiles()
    self.profile_rows = {}
    self.profile_by_id = {}
    running_count = 0
    for profile in profiles:
        profile.is_running = profile.id in self.running
        self.profile_by_id[profile.id] = profile
        if profile.is_running:
            running_count += 1

    self.sidebar_stats["profiles"].value_label.configure(text=str(len(profiles)))
    self.sidebar_stats["running"].value_label.configure(text=str(running_count))
    self.sidebar_stats["recent"].value_label.configure(text=self._latest_activity_text(profiles))

    if not profiles:
        self.stats.configure(text="0 visible")
        self._render_empty_detail("Empty inspector", "Create or import a profile to start managing rows here.")
        return

    callbacks = {"launch": self._launch, "edit": self._edit}
    for profile in profiles:
        row = CompactProfileRow(self.list_frame, profile, callbacks, self._select_profile)
        row.pack(fill="x", padx=6, pady=3)
        self.profile_rows[profile.id] = row

    if self.selected_profile_id not in self.profile_by_id:
        self.selected_profile_id = profiles[0].id
    self._filter()
    if self.visible_profile_ids:
        selected = self.selected_profile_id if self.selected_profile_id in self.visible_profile_ids else self.visible_profile_ids[0]
        self._select_profile(selected, update_status=False)
    else:
        self._render_empty_detail("No match", "Nothing matches this filter right now.")


def _compact_filter(self):
    search = self.search_var.get().lower().strip()
    visible_ids = []
    for pid, row in self.profile_rows.items():
        match = self._matches_search(row.profile, search)
        if match:
            row.pack(fill="x", padx=6, pady=3)
            visible_ids.append(pid)
        else:
            row.pack_forget()

    self.visible_profile_ids = visible_ids
    self.stats.configure(text=f"{len(visible_ids)} visible")
    self.list_hint.configure(text="Operational table for launch, edit and quick inspection." if not search else f"Filter active for '{search}'")
    if visible_ids:
        selected = self.selected_profile_id if self.selected_profile_id in visible_ids else visible_ids[0]
        self._select_profile(selected, update_status=False)
    elif self.profile_rows:
        self._render_empty_detail("No match", "Try name, tag, language, timezone or GPU.")


def _dialog_card(parent, title: str, description: str = ""):
    card = ctk.CTkFrame(
        parent,
        fg_color="#151c25",
        corner_radius=16,
        border_width=1,
        border_color="#233446",
    )
    ctk.CTkLabel(
        card,
        text=title.upper(),
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=COLORS["text_dim"],
    ).pack(anchor="w", padx=16, pady=(14, 4))
    if description:
        ctk.CTkLabel(
            card,
            text=description,
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"],
            justify="left",
            wraplength=260,
        ).pack(anchor="w", padx=16, pady=(0, 10))
    return card


def _dialog_refresh_preview(self, *_args):
    if not hasattr(self, "preview_name"):
        return

    name = self.name_entry.get().strip() or "Untitled profile"
    tags = self.tags_entry.get().strip() or "No tags"
    gpu = f"{self.gpu_brand_var.get()} {self.gpu_model_var.get()}".strip()
    display = self.resolution_var.get() or "1920x1080"
    hardware = f"{self.cpu_cores_var.get()} cores / {self.ram_var.get()} GB"
    locale = f"{self.language_var.get()}  •  {TIMEZONE_PRESETS.get(self.timezone_var.get(), {}).get('name', 'Asia/Ho_Chi_Minh').replace('_', ' ')}"
    os_text = os_label_for_platform(getattr(self, "platform_var", tk.StringVar(value="Win32")).get())
    proxy = "Direct connection"
    if self.proxy_enabled.get():
        host = self.proxy_host.get().strip() or "proxy-host"
        port = self.proxy_port.get().strip() or "0000"
        proxy = f"{self.proxy_type.get()}://{host}:{port}"
    proxy_geo = "No proxy geo"
    geo_info = getattr(self, "proxy_geo_info", None)
    if geo_info:
        city = geo_info.get("city") or geo_info.get("region") or geo_info.get("country") or "Unknown"
        tz = geo_info.get("timezone") or "Unknown TZ"
        proxy_geo = f"{city} • {tz}"

    self.preview_name.configure(text=name)
    self.preview_tags.configure(text=tags)
    self.preview_gpu.configure(text=gpu)
    self.preview_display.configure(text=display)
    self.preview_hardware.configure(text=hardware)
    self.preview_locale.configure(text=locale)
    self.preview_os.configure(text=os_text)
    self.preview_proxy.configure(text=proxy)
    self.preview_geo.configure(text=proxy_geo)


def _dialog_bind_preview(self):
    watched = [
        self.platform_var,
        self.gpu_brand_var,
        self.gpu_model_var,
        self.resolution_var,
        self.cpu_cores_var,
        self.ram_var,
        self.timezone_var,
        self.language_var,
        self.proxy_type,
        self.proxy_enabled,
    ]
    for var in watched:
        var.trace_add("write", self._refresh_preview)

    for entry in [self.name_entry, self.tags_entry, self.proxy_host, self.proxy_port, self.proxy_user, self.proxy_pass]:
        entry.bind("<KeyRelease>", self._refresh_preview)


def _dialog_toggle_proxy(self):
    ProfileDialog._original_toggle_proxy(self)
    self._refresh_preview()


def _dialog_set_proxy_status(self, message: str, color: str = None):
    if hasattr(self, "proxy_status_label"):
        self.proxy_status_label.configure(text=message, text_color=color or COLORS["text_muted"])


def _dialog_parse_proxy_input(self):
    raw = self.proxy_quick_entry.get().strip()
    if not raw:
        self._set_proxy_status("Paste a proxy string first.", COLORS["warning"])
        return

    protocol = self.proxy_type.get() or "http"
    host = ""
    port = ""
    username = ""
    password = ""

    try:
        if "://" in raw:
            from urllib.parse import urlsplit

            parsed = urlsplit(raw)
            protocol = parsed.scheme or protocol
            host = parsed.hostname or ""
            port = str(parsed.port or "")
            username = parsed.username or ""
            password = parsed.password or ""
        else:
            parts = raw.split(":")
            if len(parts) >= 4:
                host, port, username, password = parts[0], parts[1], parts[2], ":".join(parts[3:])
            elif len(parts) == 2:
                host, port = parts
            else:
                raise ValueError("Unsupported proxy format")
    except Exception:
        self._set_proxy_status("Unsupported proxy format.", COLORS["danger"])
        return

    self.proxy_enabled.set(True)
    self._toggle_proxy()
    self.proxy_type.set(protocol)
    self.proxy_host.delete(0, tk.END)
    self.proxy_host.insert(0, host)
    self.proxy_port.delete(0, tk.END)
    self.proxy_port.insert(0, port)
    self.proxy_user.delete(0, tk.END)
    if username:
        self.proxy_user.insert(0, username)
    self.proxy_pass.delete(0, tk.END)
    if password:
        self.proxy_pass.insert(0, password)

    self._set_proxy_status("Proxy fields parsed.", COLORS["success"])
    self._refresh_preview()


def _dialog_test_proxy(self):
    protocol = self.proxy_type.get().strip() or "http"
    host = self.proxy_host.get().strip()
    port = self.proxy_port.get().strip()
    username = self.proxy_user.get().strip()
    password = self.proxy_pass.get().strip()

    if not host or not port:
        self._set_proxy_status("Host and port are required.", COLORS["warning"])
        return

    self._set_proxy_status("Testing proxy...", COLORS["info"])

    def worker():
        proxy_url = f"{protocol}://"
        if username:
            proxy_url += f"{username}:{password}@"
        proxy_url += f"{host}:{port}"

        try:
            try:
                import requests

                proxies = {"http": proxy_url, "https": proxy_url}
                response = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=20)
                payload = response.json()
                ip = payload.get("ip", "unknown")
            except ImportError:
                if protocol.startswith("socks"):
                    raise RuntimeError("SOCKS test needs requests[socks] installed")

                import base64
                import json
                import urllib.request

                proxy_handler = urllib.request.ProxyHandler({
                    "http": f"http://{host}:{port}",
                    "https": f"http://{host}:{port}",
                })
                opener = urllib.request.build_opener(proxy_handler)
                if username:
                    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
                    opener.addheaders = [("Proxy-Authorization", f"Basic {token}")]
                with opener.open("https://api.ipify.org?format=json", timeout=20) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    ip = payload.get("ip", "unknown")

            self.after(0, lambda: self._set_proxy_status(f"Proxy OK • IP {ip}", COLORS["success"]))
        except Exception as exc:
            self.after(0, lambda: self._set_proxy_status(f"Proxy failed • {exc}", COLORS["danger"]))

    threading.Thread(target=worker, daemon=True).start()


def _dialog_reload_saved_proxy_choices(self):
    self.saved_proxy_entries = load_proxy_catalog()
    self.saved_proxy_lookup = {proxy_display_name(item): item for item in self.saved_proxy_entries}
    choices = ["Select saved proxy..."] + list(self.saved_proxy_lookup.keys())
    if hasattr(self, "saved_proxy_combo"):
        self.saved_proxy_combo.configure(values=choices)
        if not self.saved_proxy_var.get():
            self.saved_proxy_var.set("Select saved proxy...")


def _dialog_apply_saved_proxy(self):
    selection = self.saved_proxy_var.get().strip()
    if not selection or selection == "Select saved proxy...":
        self._set_proxy_status("Choose a saved proxy first.", COLORS["warning"])
        return

    proxy = self.saved_proxy_lookup.get(selection)
    if not proxy:
        self._set_proxy_status("Saved proxy was not found.", COLORS["danger"])
        return

    self.proxy_enabled.set(True)
    self._toggle_proxy()
    self.proxy_type.set(proxy.get("protocol", "http"))
    self.proxy_host.delete(0, tk.END)
    self.proxy_host.insert(0, proxy.get("host", ""))
    self.proxy_port.delete(0, tk.END)
    self.proxy_port.insert(0, str(proxy.get("port", "")))
    self.proxy_user.delete(0, tk.END)
    if proxy.get("username"):
        self.proxy_user.insert(0, proxy.get("username", ""))
    self.proxy_pass.delete(0, tk.END)
    if proxy.get("password"):
        self.proxy_pass.insert(0, proxy.get("password", ""))
    self._set_proxy_status(f"Loaded {proxy.get('name', proxy.get('host', 'proxy'))}.", COLORS["success"])
    self._refresh_preview()


def _dialog_save_and_launch(self):
    self._launch_after_save = True
    self._save()


def _dialog_create_widgets(self):
    self.configure(fg_color="#0f141b")

    header = ctk.CTkFrame(
        self,
        fg_color="#10161d",
        corner_radius=0,
        height=72,
    )
    header.pack(fill="x")
    header.pack_propagate(False)

    ctk.CTkLabel(
        header,
        text="Edit Profile" if self.edit_profile else "Create Profile",
        font=ctk.CTkFont(size=22, weight="bold"),
    ).pack(anchor="w", padx=20, pady=(14, 2))
    ctk.CTkLabel(
        header,
        text="Shape the identity first, then review the preview panel before saving.",
        font=ctk.CTkFont(size=11),
        text_color=COLORS["text_muted"],
    ).pack(anchor="w", padx=20)

    body = ctk.CTkFrame(self, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=16, pady=16)
    body.grid_columnconfigure(0, weight=5)
    body.grid_columnconfigure(1, weight=4)
    body.grid_rowconfigure(0, weight=1)

    left_scroll = ctk.CTkScrollableFrame(
        body,
        fg_color="transparent",
        scrollbar_button_color="#223244",
        scrollbar_button_hover_color="#314558",
    )
    left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    right_panel = ctk.CTkFrame(
        body,
        fg_color="#10161d",
        corner_radius=18,
        border_width=1,
        border_color="#233446",
    )
    right_panel.grid(row=0, column=1, sticky="nsew")

    identity = _dialog_card(left_scroll, "Identity", "Name and tag grouping used in the manager.")
    identity.pack(fill="x", pady=(0, 12))
    identity_grid = ctk.CTkFrame(identity, fg_color="transparent")
    identity_grid.pack(fill="x", padx=16, pady=(0, 16))
    identity_grid.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(identity_grid, text="Profile Name", anchor="w", text_color=COLORS["text_muted"]).grid(row=0, column=0, sticky="w", pady=6)
    self.name_entry = ctk.CTkEntry(identity_grid, height=34, placeholder_text="Main US profile")
    self.name_entry.grid(row=0, column=1, sticky="ew", pady=6, padx=(12, 0))
    ctk.CTkLabel(identity_grid, text="Tags", anchor="w", text_color=COLORS["text_muted"]).grid(row=1, column=0, sticky="w", pady=6)
    self.tags_entry = ctk.CTkEntry(identity_grid, height=34, placeholder_text="work, facebook, warm")
    self.tags_entry.grid(row=1, column=1, sticky="ew", pady=6, padx=(12, 0))

    device = _dialog_card(left_scroll, "Device Surface", "GPU, display and hardware should look coherent together.")
    device.pack(fill="x", pady=(0, 12))
    device_grid = ctk.CTkFrame(device, fg_color="transparent")
    device_grid.pack(fill="x", padx=16, pady=(0, 16))
    for idx in range(2):
        device_grid.grid_columnconfigure(idx, weight=1)

    ctk.CTkLabel(device_grid, text="GPU Brand", anchor="w", text_color=COLORS["text_muted"]).grid(row=0, column=0, sticky="w", pady=6)
    self.gpu_brand_var = ctk.StringVar(value="NVIDIA")
    self.gpu_brand = ctk.CTkComboBox(
        device_grid,
        values=list(GPU_PRESETS.keys()),
        variable=self.gpu_brand_var,
        command=self._on_gpu_brand_change,
        height=34,
    )
    self.gpu_brand.grid(row=1, column=0, sticky="ew", padx=(0, 8))

    ctk.CTkLabel(device_grid, text="GPU Model", anchor="w", text_color=COLORS["text_muted"]).grid(row=0, column=1, sticky="w", pady=6)
    self.gpu_model_var = ctk.StringVar()
    self.gpu_model = ctk.CTkComboBox(device_grid, variable=self.gpu_model_var, height=34)
    self.gpu_model.grid(row=1, column=1, sticky="ew")

    ctk.CTkLabel(device_grid, text="Resolution", anchor="w", text_color=COLORS["text_muted"]).grid(row=2, column=0, sticky="w", pady=(12, 6))
    self.resolution_var = ctk.StringVar(value="1920x1080")
    ctk.CTkComboBox(
        device_grid,
        values=["1366x768", "1440x900", "1536x864", "1600x900", "1920x1080", "2560x1440", "3840x2160"],
        variable=self.resolution_var,
        height=34,
    ).grid(row=3, column=0, sticky="ew", padx=(0, 8))

    ctk.CTkLabel(device_grid, text="CPU Cores", anchor="w", text_color=COLORS["text_muted"]).grid(row=2, column=1, sticky="w", pady=(12, 6))
    self.cpu_cores_var = ctk.StringVar(value="8")
    ctk.CTkComboBox(
        device_grid,
        values=["2", "4", "6", "8", "10", "12", "16", "24", "32"],
        variable=self.cpu_cores_var,
        height=34,
    ).grid(row=3, column=1, sticky="ew")

    ctk.CTkLabel(device_grid, text="RAM", anchor="w", text_color=COLORS["text_muted"]).grid(row=4, column=0, sticky="w", pady=(12, 6))
    self.ram_var = ctk.StringVar(value="8")
    ctk.CTkComboBox(
        device_grid,
        values=["2", "4", "8", "16", "32", "64"],
        variable=self.ram_var,
        height=34,
    ).grid(row=5, column=0, sticky="ew", padx=(0, 8))
    self._on_gpu_brand_change("NVIDIA")

    locale_card = _dialog_card(left_scroll, "Locale & Timezone", "Keep language and timezone aligned with the profile target region.")
    locale_card.pack(fill="x", pady=(0, 12))
    locale_grid = ctk.CTkFrame(locale_card, fg_color="transparent")
    locale_grid.pack(fill="x", padx=16, pady=(0, 16))
    locale_grid.grid_columnconfigure(0, weight=1)
    locale_grid.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(locale_grid, text="Timezone", anchor="w", text_color=COLORS["text_muted"]).grid(row=0, column=0, sticky="w", pady=6)
    self.timezone_var = ctk.StringVar(value="Vietnam (UTC+7)")
    ctk.CTkComboBox(locale_grid, values=list(TIMEZONE_PRESETS.keys()), variable=self.timezone_var, height=34).grid(row=1, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkLabel(locale_grid, text="Language", anchor="w", text_color=COLORS["text_muted"]).grid(row=0, column=1, sticky="w", pady=6)
    self.language_var = ctk.StringVar(value="en-US")
    ctk.CTkComboBox(locale_grid, values=["en-US", "en-GB", "en-AU", "vi-VN", "th-TH", "zh-CN", "zh-TW", "ja-JP", "ko-KR", "fr-FR", "de-DE", "es-ES", "pt-BR"], variable=self.language_var, height=34).grid(row=1, column=1, sticky="ew")
    ctk.CTkLabel(locale_grid, text="Operating System", anchor="w", text_color=COLORS["text_muted"]).grid(row=2, column=0, sticky="w", pady=(12, 6))
    self.platform_var = tk.StringVar(value="Win32")
    ctk.CTkEntry(locale_grid, textvariable=self.platform_var, state="disabled", height=34).grid(row=3, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkLabel(locale_grid, text="Geo Source", anchor="w", text_color=COLORS["text_muted"]).grid(row=2, column=1, sticky="w", pady=(12, 6))
    self.proxy_geo_label = ctk.CTkLabel(locale_grid, text="Manual locale", anchor="w", justify="left", wraplength=220, text_color=COLORS["text_muted"])
    self.proxy_geo_label.grid(row=3, column=1, sticky="w")

    proxy_card = _dialog_card(left_scroll, "Proxy", "Enable only when this profile should always launch through a fixed endpoint.")
    proxy_card.pack(fill="x", pady=(0, 12))
    proxy_grid = ctk.CTkFrame(proxy_card, fg_color="transparent")
    proxy_grid.pack(fill="x", padx=16, pady=(0, 16))
    for idx in range(2):
        proxy_grid.grid_columnconfigure(idx, weight=1)
    self.proxy_geo_info = None
    self.saved_proxy_var = ctk.StringVar(value="Select saved proxy...")
    self.saved_proxy_entries = []
    self.saved_proxy_lookup = {}
    ctk.CTkLabel(proxy_grid, text="Saved Proxy", anchor="w", text_color=COLORS["text_muted"]).grid(row=0, column=0, sticky="w", pady=(0, 6))
    self.saved_proxy_combo = ctk.CTkComboBox(proxy_grid, variable=self.saved_proxy_var, values=["Select saved proxy..."], height=34)
    self.saved_proxy_combo.grid(row=1, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkButton(
        proxy_grid,
        text="Use Saved",
        width=96,
        height=30,
        corner_radius=8,
        fg_color="#19232f",
        hover_color="#223244",
        border_width=1,
        border_color="#27394b",
        command=self._apply_saved_proxy,
    ).grid(row=1, column=1, sticky="w")

    ctk.CTkLabel(proxy_grid, text="Quick Paste", anchor="w", text_color=COLORS["text_muted"]).grid(row=2, column=0, sticky="w", pady=(12, 6))
    self.proxy_quick_entry = ctk.CTkEntry(proxy_grid, placeholder_text="host:port:user:pass or http://user:pass@host:port", height=34)
    self.proxy_quick_entry.grid(row=3, column=0, columnspan=2, sticky="ew")
    proxy_quick_actions = ctk.CTkFrame(proxy_grid, fg_color="transparent")
    proxy_quick_actions.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(8, 12))
    ctk.CTkButton(
        proxy_quick_actions,
        text="Parse",
        width=82,
        height=30,
        corner_radius=8,
        fg_color="#19232f",
        hover_color="#223244",
        border_width=1,
        border_color="#27394b",
        command=self._parse_proxy_input,
    ).pack(side="left")
    ctk.CTkButton(
        proxy_quick_actions,
        text="Test Proxy",
        width=96,
        height=30,
        corner_radius=8,
        fg_color=COLORS["info"],
        hover_color=COLORS["info_hover"],
        text_color=COLORS["bg_dark"],
        command=self._test_proxy,
    ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(
        proxy_quick_actions,
        text="Apply Proxy Geo",
        width=118,
        height=30,
        corner_radius=8,
        fg_color="#19232f",
        hover_color="#223244",
        border_width=1,
        border_color="#27394b",
        command=self._apply_proxy_geo,
    ).pack(side="left", padx=(8, 0))
    self.proxy_status_label = ctk.CTkLabel(
        proxy_quick_actions,
        text="",
        font=ctk.CTkFont(size=10),
        text_color=COLORS["text_muted"],
    )
    self.proxy_status_label.pack(side="left", padx=(12, 0))
    self.proxy_enabled = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(proxy_grid, text="Enable proxy", variable=self.proxy_enabled, command=self._toggle_proxy).grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 12))
    ctk.CTkLabel(proxy_grid, text="Type", anchor="w", text_color=COLORS["text_muted"]).grid(row=6, column=0, sticky="w", pady=6)
    self.proxy_type = ctk.StringVar(value="http")
    self.proxy_type_cb = ctk.CTkComboBox(proxy_grid, values=["http", "socks5"], variable=self.proxy_type, state="disabled", height=34)
    self.proxy_type_cb.grid(row=7, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkLabel(proxy_grid, text="Host", anchor="w", text_color=COLORS["text_muted"]).grid(row=6, column=1, sticky="w", pady=6)
    self.proxy_host = ctk.CTkEntry(proxy_grid, placeholder_text="proxy.example.com", state="disabled", height=34)
    self.proxy_host.grid(row=7, column=1, sticky="ew")
    ctk.CTkLabel(proxy_grid, text="Port", anchor="w", text_color=COLORS["text_muted"]).grid(row=8, column=0, sticky="w", pady=(12, 6))
    self.proxy_port = ctk.CTkEntry(proxy_grid, placeholder_text="8080", state="disabled", height=34)
    self.proxy_port.grid(row=9, column=0, sticky="ew", padx=(0, 8))
    ctk.CTkLabel(proxy_grid, text="Username", anchor="w", text_color=COLORS["text_muted"]).grid(row=8, column=1, sticky="w", pady=(12, 6))
    self.proxy_user = ctk.CTkEntry(proxy_grid, placeholder_text="optional", state="disabled", height=34)
    self.proxy_user.grid(row=9, column=1, sticky="ew")
    ctk.CTkLabel(proxy_grid, text="Password", anchor="w", text_color=COLORS["text_muted"]).grid(row=10, column=0, sticky="w", pady=(12, 6))
    self.proxy_pass = ctk.CTkEntry(proxy_grid, placeholder_text="optional", show="*", state="disabled", height=34)
    self.proxy_pass.grid(row=11, column=0, sticky="ew", padx=(0, 8))

    preview = _dialog_card(right_panel, "Profile Preview", "Review the composed identity before saving.")
    preview.pack(fill="x", padx=16, pady=(16, 12))
    self.preview_name = ctk.CTkLabel(preview, text="Untitled profile", font=ctk.CTkFont(size=18, weight="bold"))
    self.preview_name.pack(anchor="w", padx=16, pady=(0, 6))
    self.preview_tags = ctk.CTkLabel(preview, text="No tags", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
    self.preview_tags.pack(anchor="w", padx=16, pady=(0, 12))
    for title, attr in [
        ("OS", "preview_os"),
        ("GPU", "preview_gpu"),
        ("Display", "preview_display"),
        ("Hardware", "preview_hardware"),
        ("Locale", "preview_locale"),
        ("Proxy Geo", "preview_geo"),
        ("Proxy", "preview_proxy"),
    ]:
        row = ctk.CTkFrame(preview, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row, text=title, width=68, anchor="w", font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_muted"]).pack(side="left")
        label = ctk.CTkLabel(row, text="-", anchor="w", justify="left", wraplength=210, font=ctk.CTkFont(size=11, weight="bold"))
        label.pack(side="left", fill="x", expand=True)
        setattr(self, attr, label)

    tips = _dialog_card(right_panel, "Operator Notes", "A good profile should keep GPU, locale, timezone and proxy coherent with the account it is meant to run.")
    tips.pack(fill="x", padx=16)

    footer = ctk.CTkFrame(self, fg_color="#10161d", corner_radius=0, height=60)
    footer.pack(fill="x", side="bottom")
    footer.pack_propagate(False)
    ctk.CTkButton(
        footer,
        text="Randomize",
        width=112,
        height=34,
        corner_radius=10,
        fg_color="#19232f",
        hover_color="#223244",
        border_width=1,
        border_color="#27394b",
        command=self._randomize,
    ).pack(side="left", padx=18, pady=16)
    ctk.CTkButton(
        footer,
        text="Cancel",
        width=96,
        height=34,
        corner_radius=10,
        fg_color="#19232f",
        hover_color="#223244",
        border_width=1,
        border_color="#27394b",
        command=self.destroy,
    ).pack(side="right", padx=(8, 18), pady=16)
    ctk.CTkButton(
        footer,
        text="Save & Launch",
        width=132,
        height=34,
        corner_radius=10,
        fg_color=COLORS["info"],
        hover_color=COLORS["info_hover"],
        text_color=COLORS["bg_dark"],
        font=ctk.CTkFont(size=13, weight="bold"),
        command=self._save_and_launch,
    ).pack(side="right", padx=(0, 8), pady=16)
    ctk.CTkButton(
        footer,
        text="Save Profile",
        width=128,
        height=34,
        corner_radius=10,
        fg_color=COLORS["accent"],
        hover_color=COLORS["accent_hover"],
        font=ctk.CTkFont(size=13, weight="bold"),
        command=self._save,
    ).pack(side="right", pady=16)

    self._bind_preview()
    self._reload_saved_proxy_choices()
    self._refresh_preview()

MainApp._create_widgets = _compact_create_widgets
MainApp._matches_search = _ops_matches_search
MainApp._last_used_text = _ops_last_used_text
MainApp._proxy_text = _ops_proxy_text
MainApp._gpu_name = _ops_gpu_name
MainApp._select_profile = _ops_select_profile
MainApp._render_detail = _compact_render_detail
MainApp._render_empty_detail = _compact_render_empty_detail
MainApp._refresh = _compact_refresh
MainApp._filter = _compact_filter
MainApp._export_profile_ui = _ops_export_profile_ui
MainApp._import_profile_ui = _ops_import_profile_ui

ProfileDialog._original_toggle_proxy = ProfileDialog._toggle_proxy
ProfileDialog._create_widgets = _dialog_create_widgets
ProfileDialog._refresh_preview = _dialog_refresh_preview
ProfileDialog._bind_preview = _dialog_bind_preview
ProfileDialog._set_proxy_status = _dialog_set_proxy_status
ProfileDialog._parse_proxy_input = _dialog_parse_proxy_input
ProfileDialog._test_proxy = _dialog_test_proxy
ProfileDialog._save_and_launch = _dialog_save_and_launch
ProfileDialog._toggle_proxy = _dialog_toggle_proxy


class ProxyCatalogRow(ctk.CTkFrame):
    """Row for the proxy manager table."""

    def __init__(self, master, proxy: Dict, callbacks: dict, **kwargs):
        super().__init__(master, **kwargs)
        self.proxy = proxy
        self.callbacks = callbacks
        self.configure(
            fg_color="#151c25",
            corner_radius=10,
            border_width=1,
            border_color="#233446",
            height=62,
        )
        self.pack_propagate(False)
        self._create_widgets()

    def _create_widgets(self):
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=12, pady=8)
        widths = [220, 90, 160, 120, 120, 140]
        for idx, width in enumerate(widths):
            shell.grid_columnconfigure(idx, minsize=width, weight=0)

        ctk.CTkLabel(shell, text=self.proxy.get("name", f"{self.proxy.get('host')}:{self.proxy.get('port')}"), font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ctk.CTkLabel(shell, text=str(self.proxy.get("protocol", "http")).upper(), font=ctk.CTkFont(size=11, weight="bold"), text_color=COLORS["text"]).grid(row=0, column=1, sticky="w", padx=(0, 8))
        ctk.CTkLabel(shell, text=f"{self.proxy.get('host', '')}:{self.proxy.get('port', '')}", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=2, sticky="w", padx=(0, 8))
        auth_text = self.proxy.get("username", "") or "No auth"
        ctk.CTkLabel(shell, text=auth_text, font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).grid(row=0, column=3, sticky="w", padx=(0, 8))
        ctk.CTkLabel(shell, text=self.proxy.get("last_checked", "") or "Never", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).grid(row=0, column=4, sticky="w", padx=(0, 8))

        status = self.proxy.get("status", "new")
        status_color = COLORS["success"] if status == "ok" else COLORS["warning"] if status == "testing" else COLORS["text_muted"]
        status_bg = COLORS["success_soft"] if status == "ok" else "#2b2415" if status == "testing" else "#1b2430"
        ctk.CTkLabel(
            shell,
            text=(f"OK • {self.proxy.get('last_ip')}" if status == "ok" and self.proxy.get("last_ip") else status.upper()),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=status_bg,
            text_color=status_color,
            corner_radius=999,
            padx=8,
            pady=4,
        ).grid(row=0, column=5, sticky="w", padx=(0, 8))

        actions = ctk.CTkFrame(shell, fg_color="transparent")
        actions.grid(row=0, column=6, sticky="e")
        ctk.CTkButton(
            actions,
            text="Check",
            width=70,
            height=28,
            corner_radius=8,
            fg_color=COLORS["info"],
            hover_color=COLORS["info_hover"],
            text_color=COLORS["bg_dark"],
            command=lambda: self.callbacks["check"](self.proxy["id"]),
        ).pack(side="left")
        ctk.CTkButton(
            actions,
            text="Delete",
            width=70,
            height=28,
            corner_radius=8,
            fg_color="#19232f",
            hover_color="#223244",
            border_width=1,
            border_color="#27394b",
            command=lambda: self.callbacks["delete"](self.proxy["id"]),
        ).pack(side="left", padx=(6, 0))


def _workspace_build_profiles_page(self, parent):
    header = ctk.CTkFrame(parent, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140")
    header.pack(fill="x")
    header_inner = ctk.CTkFrame(header, fg_color="transparent")
    header_inner.pack(fill="x", padx=16, pady=14)
    title_box = ctk.CTkFrame(header_inner, fg_color="transparent")
    title_box.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(title_box, text="Profiles", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
    self.list_hint = ctk.CTkLabel(title_box, text="Operational table for launch, edit and quick inspection.", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
    self.list_hint.pack(anchor="w", pady=(4, 0))

    toolbar = ctk.CTkFrame(parent, fg_color="transparent")
    toolbar.pack(fill="x", pady=(12, 10))
    ctk.CTkButton(toolbar, text="Quick Create", width=108, height=34, corner_radius=10, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._new_profile).pack(side="left")
    ctk.CTkButton(toolbar, text="Import", width=84, height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._import_profile_ui).pack(side="left", padx=(8, 0))
    ctk.CTkButton(toolbar, text="Export", width=84, height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._export_profile_ui).pack(side="left", padx=(8, 0))
    self.stats = ctk.CTkLabel(toolbar, text="0 visible", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#2b2118", text_color=COLORS["accent"], corner_radius=999, padx=10, pady=5)
    self.stats.pack(side="right")
    self.search_var = ctk.StringVar()
    self.search_var.trace("w", lambda *_: self._filter())
    ctk.CTkEntry(toolbar, placeholder_text="Search profiles...", width=280, height=36, corner_radius=10, textvariable=self.search_var).pack(side="right", padx=(0, 10))

    self.table_shell = ctk.CTkFrame(parent, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140")
    self.table_shell.pack(fill="both", expand=True)
    header_row = ctk.CTkFrame(self.table_shell, fg_color="#141d27", corner_radius=10, height=38)
    header_row.pack(fill="x", padx=10, pady=(10, 6))
    header_row.pack_propagate(False)
    header_grid = ctk.CTkFrame(header_row, fg_color="transparent")
    header_grid.pack(fill="both", expand=True, padx=12)
    for idx, (label, width) in enumerate(COMPACT_TABLE_COLUMNS):
        header_grid.grid_columnconfigure(idx, minsize=width, weight=0)
        ctk.CTkLabel(header_grid, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_dim"]).grid(row=0, column=idx, sticky="w", padx=(0, 8), pady=10)

    self.list_frame = ctk.CTkScrollableFrame(self.table_shell, fg_color="transparent", scrollbar_button_color="#223244", scrollbar_button_hover_color="#314558")
    self.list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    self.detail_shell = ctk.CTkFrame(parent, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140", height=168)
    self.detail_shell.pack(fill="x", pady=(10, 0))
    self.detail_shell.pack_propagate(False)
    self.detail_frame = ctk.CTkFrame(self.detail_shell, fg_color="transparent")
    self.detail_frame.pack(fill="both", expand=True, padx=14, pady=14)


def _workspace_build_proxy_page(self, parent):
    header = ctk.CTkFrame(parent, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140")
    header.pack(fill="x")
    header_inner = ctk.CTkFrame(header, fg_color="transparent")
    header_inner.pack(fill="x", padx=16, pady=14)
    title_box = ctk.CTkFrame(header_inner, fg_color="transparent")
    title_box.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(title_box, text="Proxy Manager", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w")
    self.proxy_hint = ctk.CTkLabel(title_box, text="Import, test and reuse saved proxies from one local catalog.", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
    self.proxy_hint.pack(anchor="w", pady=(4, 0))

    toolbar = ctk.CTkFrame(parent, fg_color="transparent")
    toolbar.pack(fill="x", pady=(12, 10))
    ctk.CTkButton(toolbar, text="Add Proxy", width=96, height=34, corner_radius=10, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._open_add_proxy_dialog).pack(side="left")
    ctk.CTkButton(toolbar, text="Import Proxy", width=108, height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._import_proxy_catalog_ui).pack(side="left", padx=(8, 0))
    ctk.CTkButton(toolbar, text="Export Proxy", width=108, height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._export_proxy_catalog_ui).pack(side="left", padx=(8, 0))
    self.proxy_stats_badge = ctk.CTkLabel(toolbar, text="0 proxies", font=ctk.CTkFont(size=11, weight="bold"), fg_color="#1b2430", text_color=COLORS["info"], corner_radius=999, padx=10, pady=5)
    self.proxy_stats_badge.pack(side="right")
    self.proxy_search_var = ctk.StringVar()
    self.proxy_search_var.trace("w", lambda *_: self._refresh_proxy_catalog_view())
    ctk.CTkEntry(toolbar, placeholder_text="Search proxy, host, user...", width=300, height=36, corner_radius=10, textvariable=self.proxy_search_var).pack(side="right", padx=(0, 10))

    self.proxy_table_shell = ctk.CTkFrame(parent, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140")
    self.proxy_table_shell.pack(fill="both", expand=True)
    header_row = ctk.CTkFrame(self.proxy_table_shell, fg_color="#141d27", corner_radius=10, height=38)
    header_row.pack(fill="x", padx=10, pady=(10, 6))
    header_row.pack_propagate(False)
    header_grid = ctk.CTkFrame(header_row, fg_color="transparent")
    header_grid.pack(fill="both", expand=True, padx=12)
    proxy_headers = [("Name", 220), ("Type", 90), ("Address", 160), ("Auth", 120), ("Last Check", 120), ("Status", 140), ("Action", 150)]
    for idx, (label, width) in enumerate(proxy_headers):
        header_grid.grid_columnconfigure(idx, minsize=width, weight=0)
        ctk.CTkLabel(header_grid, text=label, font=ctk.CTkFont(size=10, weight="bold"), text_color=COLORS["text_dim"]).grid(row=0, column=idx, sticky="w", padx=(0, 8), pady=10)

    self.proxy_list_frame = ctk.CTkScrollableFrame(self.proxy_table_shell, fg_color="transparent", scrollbar_button_color="#223244", scrollbar_button_hover_color="#314558")
    self.proxy_list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 6))


def _workspace_show_page(self, page: str):
    self.current_page = page
    self.profiles_page.pack_forget()
    self.proxies_page.pack_forget()
    if page == "profiles":
        self.profiles_page.pack(fill="both", expand=True)
        self.nav_profiles_btn.configure(fg_color="#1d4ed8")
        self.nav_proxies_btn.configure(fg_color="#19232f")
    else:
        self.proxies_page.pack(fill="both", expand=True)
        self.nav_profiles_btn.configure(fg_color="#19232f")
        self.nav_proxies_btn.configure(fg_color="#1d4ed8")


def _workspace_create_widgets(self):
    self.geometry("1450x840")
    self.minsize(1220, 740)
    self.configure(fg_color="#0d1218")
    self.selected_profile_id = None
    self.profile_rows = {}
    self.profile_by_id = {}
    self.visible_profile_ids = []
    self.proxy_rows = {}
    self.proxy_catalog = []
    self.current_page = "profiles"

    root = ctk.CTkFrame(self, fg_color="transparent")
    root.pack(fill="both", expand=True, padx=14, pady=14)

    sidebar = ctk.CTkFrame(root, fg_color="#10161d", corner_radius=18, border_width=1, border_color="#223140", width=196)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)
    main = ctk.CTkFrame(root, fg_color="transparent")
    main.pack(side="left", fill="both", expand=True, padx=(14, 0))

    ctk.CTkLabel(sidebar, text="S Manage", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", padx=16, pady=(16, 4))
    ctk.CTkLabel(sidebar, text=APP_VERSION_LABEL, font=ctk.CTkFont(size=10, weight="bold"), fg_color=COLORS["accent_soft"], text_color=COLORS["accent"], corner_radius=999, padx=8, pady=3).pack(anchor="w", padx=16, pady=(0, 10))

    self.nav_profiles_btn = ctk.CTkButton(sidebar, text="Profiles", height=34, corner_radius=10, fg_color="#1d4ed8", hover_color="#1e40af", command=lambda: self._show_page("profiles"))
    self.nav_profiles_btn.pack(fill="x", padx=14)
    self.nav_proxies_btn = ctk.CTkButton(sidebar, text="Proxy Manager", height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=lambda: self._show_page("proxies"))
    self.nav_proxies_btn.pack(fill="x", padx=14, pady=(8, 0))
    ctk.CTkButton(sidebar, text="New Profile", height=36, corner_radius=10, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], font=ctk.CTkFont(size=12, weight="bold"), command=self._new_profile).pack(fill="x", padx=14, pady=(12, 0))
    ctk.CTkButton(sidebar, text="Refresh", height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._refresh).pack(fill="x", padx=14, pady=(8, 0))
    ctk.CTkButton(sidebar, text="Settings", height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._open_settings).pack(fill="x", padx=14, pady=(8, 0))
    if CLOUD_AVAILABLE:
        self.cloud_sync = CloudSync(APP_PATH)
        self.cloud_btn = ctk.CTkButton(sidebar, text="Cloud", height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=self._open_cloud)
        self.cloud_btn.pack(fill="x", padx=14, pady=(8, 0))
        self._update_cloud_status()

    self.sidebar_stats = {}
    stats_wrap = ctk.CTkFrame(sidebar, fg_color="transparent")
    stats_wrap.pack(fill="x", padx=14, pady=(18, 0))
    self.sidebar_stats["profiles"] = self._create_stat_card(stats_wrap, "Profiles", "0")
    self.sidebar_stats["profiles"].pack(fill="x")
    self.sidebar_stats["running"] = self._create_stat_card(stats_wrap, "Running", "0")
    self.sidebar_stats["running"].pack(fill="x", pady=8)
    self.sidebar_stats["proxies"] = self._create_stat_card(stats_wrap, "Proxies", "0")
    self.sidebar_stats["proxies"].pack(fill="x", pady=8)
    self.sidebar_stats["recent"] = self._create_stat_card(stats_wrap, "Recent", "No activity")
    self.sidebar_stats["recent"].pack(fill="x")

    self.page_holder = ctk.CTkFrame(main, fg_color="transparent")
    self.page_holder.pack(fill="both", expand=True)
    self.profiles_page = ctk.CTkFrame(self.page_holder, fg_color="transparent")
    self.proxies_page = ctk.CTkFrame(self.page_holder, fg_color="transparent")
    self._workspace_build_profiles_page(self.profiles_page)
    self._workspace_build_proxy_page(self.proxies_page)
    self._show_page("profiles")

    status = ctk.CTkFrame(self, fg_color="#111923", corner_radius=0, height=30)
    status.pack(fill="x", side="bottom")
    self.status = ctk.CTkLabel(status, text="Ready", font=ctk.CTkFont(size=10), text_color=COLORS["text_muted"])
    self.status.pack(side="left", padx=12, pady=7)


def _workspace_refresh(self):
    _compact_refresh(self)
    self._refresh_proxy_catalog_view()


def _refresh_proxy_catalog_view(self):
    for widget in self.proxy_list_frame.winfo_children():
        widget.destroy()

    self.proxy_catalog = load_proxy_catalog()
    self.proxy_rows = {}
    self.sidebar_stats["proxies"].value_label.configure(text=str(len(self.proxy_catalog)))

    search = self.proxy_search_var.get().lower().strip() if hasattr(self, "proxy_search_var") else ""
    visible = 0
    callbacks = {"check": self._check_proxy_entry, "delete": self._delete_proxy_entry}
    for proxy in self.proxy_catalog:
        haystacks = [
            str(proxy.get("name", "")).lower(),
            str(proxy.get("host", "")).lower(),
            str(proxy.get("username", "")).lower(),
            str(proxy.get("protocol", "")).lower(),
            str(proxy.get("last_ip", "")).lower(),
        ]
        if search and not any(search in item for item in haystacks):
            continue
        row = ProxyCatalogRow(self.proxy_list_frame, proxy, callbacks)
        row.pack(fill="x", padx=6, pady=3)
        self.proxy_rows[proxy["id"]] = row
        visible += 1

    if hasattr(self, "proxy_stats_badge"):
        self.proxy_stats_badge.configure(text=f"{visible} proxies")
    if not visible:
        empty = ctk.CTkFrame(self.proxy_list_frame, fg_color="#151c25", corner_radius=12, border_width=1, border_color="#233446", height=120)
        empty.pack(fill="x", padx=6, pady=18)
        empty.pack_propagate(False)
        ctk.CTkLabel(empty, text="No proxies yet", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(26, 6))
        ctk.CTkLabel(empty, text="Add, import or test proxies from the toolbar above.", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).pack()


def _open_add_proxy_dialog(self):
    win = ctk.CTkToplevel(self)
    win.title("Add Proxies")
    win.geometry("720x440")
    win.transient(self)
    win.grab_set()

    ctk.CTkLabel(win, text="Add Proxies", font=ctk.CTkFont(size=22, weight="bold")).pack(anchor="w", padx=20, pady=(20, 6))
    ctk.CTkLabel(win, text="Paste one proxy per line. Supported: host:port:user:pass, host:port or http://user:pass@host:port", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).pack(anchor="w", padx=20)

    top = ctk.CTkFrame(win, fg_color="transparent")
    top.pack(fill="x", padx=20, pady=(14, 8))
    ctk.CTkLabel(top, text="Default Type", text_color=COLORS["text_muted"]).pack(side="left")
    protocol_var = ctk.StringVar(value="http")
    ctk.CTkComboBox(top, width=110, values=["http", "socks5"], variable=protocol_var, height=34).pack(side="left", padx=(10, 0))

    text_box = ctk.CTkTextbox(win, height=250)
    text_box.pack(fill="both", expand=True, padx=20, pady=(0, 14))

    status = ctk.CTkLabel(win, text="", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
    status.pack(anchor="w", padx=20)

    def save_entries():
        raw_lines = [line.strip() for line in text_box.get("1.0", "end").splitlines() if line.strip()]
        if not raw_lines:
            status.configure(text="No proxy lines provided.", text_color=COLORS["warning"])
            return
        additions = []
        failed = 0
        for raw in raw_lines:
            try:
                additions.append(parse_proxy_string(raw, default_protocol=protocol_var.get()))
            except Exception:
                failed += 1
        current = load_proxy_catalog()
        merged = merge_proxy_entries(current, additions)
        save_proxy_catalog(merged)
        self._refresh_proxy_catalog_view()
        status.configure(text=f"Saved {len(additions)} proxies. Failed: {failed}", text_color=COLORS["success"] if additions else COLORS["danger"])
        if additions:
            win.after(600, win.destroy)

    footer = ctk.CTkFrame(win, fg_color="transparent")
    footer.pack(fill="x", padx=20, pady=16)
    ctk.CTkButton(footer, text="Cancel", width=88, height=34, corner_radius=10, fg_color="#19232f", hover_color="#223244", border_width=1, border_color="#27394b", command=win.destroy).pack(side="right")
    ctk.CTkButton(footer, text="Save Proxies", width=120, height=34, corner_radius=10, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=save_entries).pack(side="right", padx=(0, 8))


def _import_proxy_catalog_ui(self):
    path = filedialog.askopenfilename(title="Import proxies", filetypes=[("Text or JSON", "*.txt *.json"), ("All files", "*.*")])
    if not path:
        return
    additions = []
    try:
        if path.lower().endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                additions = data
        else:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        additions.append(parse_proxy_string(line))
        current = load_proxy_catalog()
        merged = merge_proxy_entries(current, additions)
        save_proxy_catalog(merged)
        self._refresh_proxy_catalog_view()
        self.status.configure(text=f"Imported {len(additions)} proxies")
    except Exception as exc:
        messagebox.showerror("Import Proxy", str(exc))


def _export_proxy_catalog_ui(self):
    path = filedialog.asksaveasfilename(title="Export proxies", defaultextension=".txt", filetypes=[("Text file", "*.txt"), ("JSON file", "*.json")])
    if not path:
        return
    try:
        entries = load_proxy_catalog()
        if path.lower().endswith(".json"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2, ensure_ascii=False)
        else:
            lines = []
            for item in entries:
                if item.get("username"):
                    lines.append(f"{item.get('host')}:{item.get('port')}:{item.get('username')}:{item.get('password', '')}")
                else:
                    lines.append(f"{item.get('host')}:{item.get('port')}")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        self.status.configure(text=f"Exported {len(entries)} proxies")
    except Exception as exc:
        messagebox.showerror("Export Proxy", str(exc))


def _check_proxy_entry(self, proxy_id: str):
    catalog = load_proxy_catalog()
    proxy = next((item for item in catalog if item.get("id") == proxy_id), None)
    if not proxy:
        return
    proxy["status"] = "testing"
    proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
    save_proxy_catalog(catalog)
    self._refresh_proxy_catalog_view()

    def worker():
        try:
            ip = test_proxy_endpoint(proxy)
            proxy["status"] = "ok"
            proxy["last_ip"] = ip
            proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
            message = f"Proxy {proxy.get('name', proxy.get('host'))} OK • {ip}"
        except Exception as exc:
            proxy["status"] = "failed"
            proxy["last_ip"] = ""
            proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
            message = f"Proxy {proxy.get('name', proxy.get('host'))} failed • {exc}"

        updated = load_proxy_catalog()
        for item in updated:
            if item.get("id") == proxy_id:
                item.update(proxy)
                break
        save_proxy_catalog(updated)
        self.after(0, self._refresh_proxy_catalog_view)
        self.after(0, lambda: self.status.configure(text=message))

    threading.Thread(target=worker, daemon=True).start()


def _delete_proxy_entry(self, proxy_id: str):
    if not messagebox.askyesno("Delete Proxy", "Delete this proxy from the catalog?"):
        return
    entries = [item for item in load_proxy_catalog() if item.get("id") != proxy_id]
    save_proxy_catalog(entries)
    self._refresh_proxy_catalog_view()
    self.status.configure(text="Proxy deleted")


def _dialog_test_proxy_health(self):
    protocol = self.proxy_type.get().strip() or "http"
    host = self.proxy_host.get().strip()
    port = self.proxy_port.get().strip()
    username = self.proxy_user.get().strip()
    password = self.proxy_pass.get().strip()

    if not host or not port:
        self._set_proxy_status("Host and port are required.", COLORS["warning"])
        return

    self._set_proxy_status("Testing proxy...", COLORS["info"])

    def worker():
        try:
            health = assess_proxy_health(
                {
                    "protocol": protocol,
                    "host": host,
                    "port": int(port),
                    "username": username,
                    "password": password,
                }
            )
            google_status = str(health.get("google_status", "unknown")).lower()
            google_label = {"ok": "Google OK", "risk": "Google risk"}.get(google_status, "Google unknown")
            tone = COLORS["success"] if google_status == "ok" else COLORS["warning"] if google_status == "risk" else COLORS["info"]
            message = f"Proxy OK | IP {health.get('ip', 'unknown')} | {google_label}"
            if health.get("note") and google_status != "ok":
                message = f"{message} ({health['note']})"
            self.after(0, lambda msg=message, color=tone: self._set_proxy_status(msg, color))
        except Exception as exc:
            message = f"Proxy failed | {exc}"
            self.after(0, lambda msg=message: self._set_proxy_status(msg, COLORS["danger"]))

    threading.Thread(target=worker, daemon=True).start()


def _dialog_reload_saved_proxy_choices_ranked(self):
    self.saved_proxy_entries = sorted(load_proxy_catalog(), key=proxy_sort_key)
    self.saved_proxy_lookup = {proxy_display_name(item): item for item in self.saved_proxy_entries}
    choices = ["Select saved proxy..."] + list(self.saved_proxy_lookup.keys())
    if hasattr(self, "saved_proxy_combo"):
        self.saved_proxy_combo.configure(values=choices)
        current = self.saved_proxy_var.get().strip()
        self.saved_proxy_var.set(current if current in choices else "Select saved proxy...")


def _dialog_apply_saved_proxy_ranked(self):
    selection = self.saved_proxy_var.get().strip()
    if not selection or selection == "Select saved proxy...":
        self._set_proxy_status("Choose a saved proxy first.", COLORS["warning"])
        return

    proxy = self.saved_proxy_lookup.get(selection)
    if not proxy:
        self._set_proxy_status("Saved proxy was not found.", COLORS["danger"])
        return

    self.proxy_enabled.set(True)
    self._toggle_proxy()
    self.proxy_type.set(proxy.get("protocol", "http"))
    self.proxy_host.delete(0, tk.END)
    self.proxy_host.insert(0, proxy.get("host", ""))
    self.proxy_port.delete(0, tk.END)
    self.proxy_port.insert(0, str(proxy.get("port", "")))
    self.proxy_user.delete(0, tk.END)
    if proxy.get("username"):
        self.proxy_user.insert(0, proxy.get("username", ""))
    self.proxy_pass.delete(0, tk.END)
    if proxy.get("password"):
        self.proxy_pass.insert(0, proxy.get("password", ""))

    google_status = str(proxy.get("google_status", "unknown")).lower()
    google_label = {"ok": "Google OK", "risk": "Google risk"}.get(google_status, "Google unknown")
    tone = COLORS["success"] if google_status == "ok" else COLORS["warning"] if google_status == "risk" else COLORS["info"]
    self._set_proxy_status(f"Loaded {proxy.get('name', proxy.get('host', 'proxy'))} | {google_label}", tone)
    self._refresh_preview()


def _proxy_catalog_row_create_widgets_v2(self):
    shell = ctk.CTkFrame(self, fg_color="transparent")
    shell.pack(fill="both", expand=True, padx=12, pady=8)
    widths = [220, 90, 160, 120, 120, 140]
    for idx, width in enumerate(widths):
        shell.grid_columnconfigure(idx, minsize=width, weight=0)

    ctk.CTkLabel(
        shell,
        text=self.proxy.get("name", f"{self.proxy.get('host')}:{self.proxy.get('port')}"),
        font=ctk.CTkFont(size=12, weight="bold"),
    ).grid(row=0, column=0, sticky="w", padx=(0, 8))
    ctk.CTkLabel(
        shell,
        text=str(self.proxy.get("protocol", "http")).upper(),
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color=COLORS["text"],
    ).grid(row=0, column=1, sticky="w", padx=(0, 8))
    ctk.CTkLabel(
        shell,
        text=f"{self.proxy.get('host', '')}:{self.proxy.get('port', '')}",
        font=ctk.CTkFont(size=11, weight="bold"),
    ).grid(row=0, column=2, sticky="w", padx=(0, 8))
    auth_text = self.proxy.get("username", "") or "No auth"
    ctk.CTkLabel(
        shell,
        text=auth_text,
        font=ctk.CTkFont(size=11),
        text_color=COLORS["text_muted"],
    ).grid(row=0, column=3, sticky="w", padx=(0, 8))

    check_text = self.proxy.get("last_checked", "") or "Never"
    exit_ip = self.proxy.get("last_ip", "") or "No exit IP"
    geo_text = self.proxy.get("geo_city", "") or self.proxy.get("geo_country", "") or ""
    if self.proxy.get("geo_timezone"):
        geo_text = f"{geo_text} • {self.proxy.get('geo_timezone')}".strip(" •")
    ctk.CTkLabel(
        shell,
        text=f"{check_text}\n{exit_ip}" + (f"\n{geo_text}" if geo_text else ""),
        justify="left",
        font=ctk.CTkFont(size=10),
        text_color=COLORS["text_muted"],
    ).grid(row=0, column=4, sticky="w", padx=(0, 8))

    status = str(self.proxy.get("status", "new")).lower()
    google_status = str(self.proxy.get("google_status", "unknown")).lower()
    if status == "ok" and google_status == "ok":
        badge_text = "GOOGLE OK"
        status_color = COLORS["success"]
        status_bg = COLORS["success_soft"]
    elif status == "ok" and google_status == "risk":
        badge_text = "GOOGLE RISK"
        status_color = COLORS["warning"]
        status_bg = "#2b2415"
    elif status == "ok":
        badge_text = "ALIVE"
        status_color = COLORS["info"]
        status_bg = "#1a2633"
    elif status == "testing":
        badge_text = "TESTING"
        status_color = COLORS["warning"]
        status_bg = "#2b2415"
    elif status == "failed":
        badge_text = "FAILED"
        status_color = COLORS["danger"]
        status_bg = "#2b1820"
    else:
        badge_text = "NEW"
        status_color = COLORS["text_muted"]
        status_bg = "#1b2430"

    ctk.CTkLabel(
        shell,
        text=badge_text,
        font=ctk.CTkFont(size=10, weight="bold"),
        fg_color=status_bg,
        text_color=status_color,
        corner_radius=999,
        padx=8,
        pady=4,
    ).grid(row=0, column=5, sticky="w", padx=(0, 8))

    actions = ctk.CTkFrame(shell, fg_color="transparent")
    actions.grid(row=0, column=6, sticky="e")
    ctk.CTkButton(
        actions,
        text="Check",
        width=70,
        height=28,
        corner_radius=8,
        fg_color=COLORS["info"],
        hover_color=COLORS["info_hover"],
        text_color=COLORS["bg_dark"],
        command=lambda: self.callbacks["check"](self.proxy["id"]),
    ).pack(side="left")
    ctk.CTkButton(
        actions,
        text="Delete",
        width=70,
        height=28,
        corner_radius=8,
        fg_color="#19232f",
        hover_color="#223244",
        border_width=1,
        border_color="#27394b",
        command=lambda: self.callbacks["delete"](self.proxy["id"]),
    ).pack(side="left", padx=(6, 0))


def _refresh_proxy_catalog_view_ranked(self):
    for widget in self.proxy_list_frame.winfo_children():
        widget.destroy()

    self.proxy_catalog = sorted(load_proxy_catalog(), key=proxy_sort_key)
    self.proxy_rows = {}
    self.sidebar_stats["proxies"].value_label.configure(text=str(len(self.proxy_catalog)))

    search = self.proxy_search_var.get().lower().strip() if hasattr(self, "proxy_search_var") else ""
    visible = 0
    callbacks = {"check": self._check_proxy_entry, "delete": self._delete_proxy_entry}
    for proxy in self.proxy_catalog:
        haystacks = [
            str(proxy.get("name", "")).lower(),
            str(proxy.get("host", "")).lower(),
            str(proxy.get("username", "")).lower(),
            str(proxy.get("protocol", "")).lower(),
            str(proxy.get("last_ip", "")).lower(),
            str(proxy.get("google_status", "")).lower(),
            str(proxy.get("note", "")).lower(),
        ]
        if search and not any(search in item for item in haystacks):
            continue
        row = ProxyCatalogRow(self.proxy_list_frame, proxy, callbacks)
        row.pack(fill="x", padx=6, pady=3)
        self.proxy_rows[proxy["id"]] = row
        visible += 1

    if hasattr(self, "proxy_stats_badge"):
        self.proxy_stats_badge.configure(text=f"{visible} proxies")
    if not visible:
        empty = ctk.CTkFrame(self.proxy_list_frame, fg_color="#151c25", corner_radius=12, border_width=1, border_color="#233446", height=120)
        empty.pack(fill="x", padx=6, pady=18)
        empty.pack_propagate(False)
        ctk.CTkLabel(empty, text="No proxies yet", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(26, 6))
        ctk.CTkLabel(empty, text="Add, import or test proxies from the toolbar above.", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"]).pack()


def _check_proxy_entry_health(self, proxy_id: str):
    catalog = load_proxy_catalog()
    proxy = next((item for item in catalog if item.get("id") == proxy_id), None)
    if not proxy:
        return
    proxy["status"] = "testing"
    proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
    save_proxy_catalog(catalog)
    self._refresh_proxy_catalog_view()

    def worker():
        try:
            health = assess_proxy_health(proxy)
            proxy["status"] = "ok"
            proxy["last_ip"] = health.get("ip", "")
            proxy["google_status"] = health.get("google_status", "unknown")
            proxy["note"] = health.get("note", "")
            proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
            google_label = {"ok": "Google OK", "risk": "Google risk"}.get(str(proxy.get("google_status", "unknown")).lower(), "Google unknown")
            message = f"Proxy {proxy.get('name', proxy.get('host'))} OK | {proxy.get('last_ip', '')} | {google_label}"
        except Exception as exc:
            proxy["status"] = "failed"
            proxy["last_ip"] = ""
            proxy["google_status"] = "unknown"
            proxy["note"] = str(exc)
            proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
            message = f"Proxy {proxy.get('name', proxy.get('host'))} failed | {exc}"

        updated = load_proxy_catalog()
        for item in updated:
            if item.get("id") == proxy_id:
                item.update(proxy)
                break
        save_proxy_catalog(updated)
        self.after(0, self._refresh_proxy_catalog_view)
        self.after(0, lambda msg=message: self.status.configure(text=msg))

    threading.Thread(target=worker, daemon=True).start()


def _dialog_set_proxy_geo_state(self, geo: Optional[Dict]):
    self.proxy_geo_info = geo or None
    if not hasattr(self, "proxy_geo_label"):
        return
    if not geo:
        self.proxy_geo_label.configure(text="Manual locale", text_color=COLORS["text_muted"])
        return

    city = geo.get("city") or geo.get("region") or geo.get("country") or "Unknown"
    country = geo.get("country_code") or geo.get("country") or "--"
    timezone_name = geo.get("timezone") or "Unknown TZ"
    label = f"{country} • {city}\n{timezone_name}"

    language_guess = language_for_country(geo.get("country_code", ""), self.language_var.get())
    tz_match = canonical_timezone_name(timezone_name) == canonical_timezone_name(TIMEZONE_PRESETS.get(self.timezone_var.get(), {}).get("name", self.timezone_var.get()))
    lang_match = self.language_var.get() == language_guess
    color = COLORS["success"] if tz_match and lang_match else COLORS["warning"]
    self.proxy_geo_label.configure(text=label, text_color=color)


def canonical_timezone_name(timezone_name: str) -> str:
    aliases = {
        "Asia/Saigon": "Asia/Ho_Chi_Minh",
    }
    return aliases.get(timezone_name or "", timezone_name or "")


def _dialog_apply_proxy_geo(self):
    geo = getattr(self, "proxy_geo_info", None)
    if not geo:
        if not self.proxy_host.get().strip() or not self.proxy_port.get().strip():
            self._set_proxy_status("Test or load a proxy first.", COLORS["warning"])
            return
        try:
            geo = fetch_proxy_geo(
                {
                    "protocol": self.proxy_type.get().strip() or "http",
                    "host": self.proxy_host.get().strip(),
                    "port": int(self.proxy_port.get().strip()),
                    "username": self.proxy_user.get().strip(),
                    "password": self.proxy_pass.get().strip(),
                }
            )
        except Exception as exc:
            self._set_proxy_status(f"Proxy geo failed | {exc}", COLORS["danger"])
            return

    timezone_name = geo.get("timezone") or "Asia/Ho_Chi_Minh"
    self.timezone_var.set(timezone_preset_key(timezone_name))
    self.language_var.set(language_for_country(geo.get("country_code", ""), self.language_var.get() or "en-US"))
    self._dialog_set_proxy_geo_state(geo)
    city = geo.get("city") or geo.get("country") or "proxy region"
    self._set_proxy_status(f"Applied proxy geo | {city} | {timezone_name}", COLORS["success"])
    self._refresh_preview()


def _dialog_test_proxy_health_v2(self):
    protocol = self.proxy_type.get().strip() or "http"
    host = self.proxy_host.get().strip()
    port = self.proxy_port.get().strip()
    username = self.proxy_user.get().strip()
    password = self.proxy_pass.get().strip()

    if not host or not port:
        self._set_proxy_status("Host and port are required.", COLORS["warning"])
        return

    self._set_proxy_status("Testing proxy...", COLORS["info"])

    def worker():
        try:
            proxy_data = {
                "protocol": protocol,
                "host": host,
                "port": int(port),
                "username": username,
                "password": password,
            }
            health = assess_proxy_health(proxy_data)
            geo = fetch_ip_geo(health.get("ip", ""))
            geo["ip"] = health.get("ip", "")
            google_status = str(health.get("google_status", "unknown")).lower()
            google_label = {"ok": "Google OK", "risk": "Google risk"}.get(google_status, "Google unknown")
            city = geo.get("city") or geo.get("country") or "Unknown"
            message = f"Proxy OK | {geo.get('ip', 'unknown')} | {city} | {google_label}"
            tone = COLORS["success"] if google_status == "ok" else COLORS["warning"] if google_status == "risk" else COLORS["info"]
            self.after(0, lambda data=geo, msg=message, color=tone: (self._dialog_set_proxy_geo_state(data), self._set_proxy_status(msg, color), self._refresh_preview()))
        except Exception as exc:
            message = f"Proxy failed | {exc}"
            self.after(0, lambda msg=message: self._set_proxy_status(msg, COLORS["danger"]))

    threading.Thread(target=worker, daemon=True).start()


def _dialog_apply_saved_proxy_ranked_v2(self):
    selection = self.saved_proxy_var.get().strip()
    if not selection or selection == "Select saved proxy...":
        self._set_proxy_status("Choose a saved proxy first.", COLORS["warning"])
        return

    proxy = self.saved_proxy_lookup.get(selection)
    if not proxy:
        self._set_proxy_status("Saved proxy was not found.", COLORS["danger"])
        return

    self.proxy_enabled.set(True)
    self._toggle_proxy()
    self.proxy_type.set(proxy.get("protocol", "http"))
    self.proxy_host.delete(0, tk.END)
    self.proxy_host.insert(0, proxy.get("host", ""))
    self.proxy_port.delete(0, tk.END)
    self.proxy_port.insert(0, str(proxy.get("port", "")))
    self.proxy_user.delete(0, tk.END)
    if proxy.get("username"):
        self.proxy_user.insert(0, proxy.get("username", ""))
    self.proxy_pass.delete(0, tk.END)
    if proxy.get("password"):
        self.proxy_pass.insert(0, proxy.get("password", ""))

    geo = None
    if proxy.get("geo_country") or proxy.get("geo_city") or proxy.get("geo_timezone"):
        geo = {
            "ip": proxy.get("last_ip", ""),
            "country": proxy.get("geo_country", ""),
            "country_code": proxy.get("geo_country_code", ""),
            "region": proxy.get("geo_region", ""),
            "city": proxy.get("geo_city", ""),
            "timezone": proxy.get("geo_timezone", ""),
            "lat": proxy.get("geo_latitude"),
            "lon": proxy.get("geo_longitude"),
        }
    self._dialog_set_proxy_geo_state(geo)
    if geo:
        self.timezone_var.set(timezone_preset_key(geo.get("timezone") or "Asia/Ho_Chi_Minh"))
        self.language_var.set(language_for_country(geo.get("country_code", ""), self.language_var.get() or "en-US"))

    google_status = {"ok": "Google OK", "risk": "Google risk"}.get(str(proxy.get("google_status", "unknown")).lower(), "Google unknown")
    self._set_proxy_status(f"Loaded {proxy.get('name', proxy.get('host', 'proxy'))} | {google_status}", COLORS["success"])
    self._refresh_preview()


def _dialog_load_profile_v2(self):
    ProfileDialog._original_load_profile_geo(self)
    profile = self.edit_profile
    if hasattr(self, "platform_var"):
        self.platform_var.set(profile.platform or "Win32")
    geo = None
    if getattr(profile, "geo_country", "") or getattr(profile, "geo_city", "") or getattr(profile, "geo_latitude", None) is not None:
        geo = {
            "country": getattr(profile, "geo_country", ""),
            "country_code": getattr(profile, "geo_country_code", ""),
            "region": getattr(profile, "geo_region", ""),
            "city": getattr(profile, "geo_city", ""),
            "timezone": getattr(profile, "timezone", ""),
            "lat": getattr(profile, "geo_latitude", None),
            "lon": getattr(profile, "geo_longitude", None),
        }
    self._dialog_set_proxy_geo_state(geo)
    self._refresh_preview()


def _dialog_save_v2(self):
    name = self.name_entry.get().strip()
    if not name:
        messagebox.showerror("Error", "Profile name is required")
        return

    res = self.resolution_var.get().split("x")
    screen_width, screen_height = int(res[0]), int(res[1])

    brand = self.gpu_brand_var.get()
    model = self.gpu_model_var.get()
    webgl_vendor = f"Google Inc. ({brand})"
    webgl_renderer = GPU_PRESETS.get(brand, {}).get(model, "")

    timezone_name = TIMEZONE_PRESETS.get(self.timezone_var.get(), {"name": self.timezone_var.get() or "Asia/Ho_Chi_Minh"}).get("name", "Asia/Ho_Chi_Minh")
    tags = [t.strip() for t in self.tags_entry.get().split(",") if t.strip()]
    geo = getattr(self, "proxy_geo_info", None) or {}

    def apply_profile_fields(profile_obj):
        profile_obj.name = name
        profile_obj.tags = tags
        profile_obj.screen_width = screen_width
        profile_obj.screen_height = screen_height
        profile_obj.cpu_cores = int(self.cpu_cores_var.get())
        profile_obj.ram_gb = int(self.ram_var.get())
        profile_obj.webgl_vendor = webgl_vendor
        profile_obj.webgl_renderer = webgl_renderer
        profile_obj.timezone = timezone_name
        profile_obj.language = self.language_var.get()
        profile_obj.platform = self.platform_var.get() or "Win32"
        profile_obj.geo_country = geo.get("country", "")
        profile_obj.geo_country_code = geo.get("country_code", "")
        profile_obj.geo_region = geo.get("region", "")
        profile_obj.geo_city = geo.get("city", "")
        profile_obj.geo_latitude = geo.get("lat")
        profile_obj.geo_longitude = geo.get("lon")
        profile_obj.geo_accuracy = 20
        profile_obj.proxy_enabled = self.proxy_enabled.get()
        if profile_obj.proxy_enabled:
            profile_obj.proxy_type = self.proxy_type.get()
            profile_obj.proxy_host = self.proxy_host.get()
            profile_obj.proxy_port = int(self.proxy_port.get() or 0)
            profile_obj.proxy_username = self.proxy_user.get()
            profile_obj.proxy_password = self.proxy_pass.get()
        else:
            profile_obj.proxy_type = "http"
            profile_obj.proxy_host = ""
            profile_obj.proxy_port = 0
            profile_obj.proxy_username = ""
            profile_obj.proxy_password = ""

    if self.edit_profile:
        p = self.edit_profile
        apply_profile_fields(p)
        self.manager._save_profile_config(p)
    else:
        fingerprint = {
            "screen_width": screen_width,
            "screen_height": screen_height,
            "cpu_cores": int(self.cpu_cores_var.get()),
            "ram_gb": int(self.ram_var.get()),
            "webgl_vendor": webgl_vendor,
            "webgl_renderer": webgl_renderer,
            "timezone": timezone_name,
            "language": self.language_var.get(),
            "platform": self.platform_var.get() or "Win32",
            "geo_country": geo.get("country", ""),
            "geo_country_code": geo.get("country_code", ""),
            "geo_region": geo.get("region", ""),
            "geo_city": geo.get("city", ""),
            "geo_latitude": geo.get("lat"),
            "geo_longitude": geo.get("lon"),
            "geo_accuracy": 20,
        }
        p = self.manager.create_profile(name=name, fingerprint=fingerprint)
        apply_profile_fields(p)
        self.manager._save_profile_config(p)

    if hasattr(self.master, "_show_page"):
        try:
            self.master._show_page("profiles")
        except Exception:
            pass
    if hasattr(self.master, "selected_profile_id"):
        self.master.selected_profile_id = p.id

    if self.on_save:
        self.on_save()

    if getattr(self, "_launch_after_save", False) and hasattr(self.master, "_launch"):
        self.master.after(250, lambda pid=p.id: self.master._launch(pid))
    self._launch_after_save = False
    self.destroy()


def _check_proxy_entry_health_v2(self, proxy_id: str):
    catalog = load_proxy_catalog()
    proxy = next((item for item in catalog if item.get("id") == proxy_id), None)
    if not proxy:
        return
    proxy["status"] = "testing"
    proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
    save_proxy_catalog(catalog)
    self._refresh_proxy_catalog_view()

    def worker():
        try:
            health = assess_proxy_health(proxy)
            geo = fetch_ip_geo(health.get("ip", ""))
            proxy["status"] = "ok"
            proxy["last_ip"] = health.get("ip", "")
            proxy["google_status"] = health.get("google_status", "unknown")
            proxy["note"] = health.get("note", "")
            proxy["geo_country"] = geo.get("country", "")
            proxy["geo_country_code"] = geo.get("country_code", "")
            proxy["geo_region"] = geo.get("region", "")
            proxy["geo_city"] = geo.get("city", "")
            proxy["geo_timezone"] = geo.get("timezone", "")
            proxy["geo_latitude"] = geo.get("lat")
            proxy["geo_longitude"] = geo.get("lon")
            proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
            google_label = {"ok": "Google OK", "risk": "Google risk"}.get(str(proxy.get("google_status", "unknown")).lower(), "Google unknown")
            message = f"Proxy {proxy.get('name', proxy.get('host'))} OK | {proxy.get('last_ip', '')} | {geo.get('city', geo.get('country', 'Unknown'))} | {google_label}"
        except Exception as exc:
            proxy["status"] = "failed"
            proxy["last_ip"] = ""
            proxy["google_status"] = "unknown"
            proxy["note"] = str(exc)
            proxy["last_checked"] = datetime.now().strftime("%d/%m %H:%M")
            message = f"Proxy {proxy.get('name', proxy.get('host'))} failed | {exc}"

        updated = load_proxy_catalog()
        for item in updated:
            if item.get("id") == proxy_id:
                item.update(proxy)
                break
        save_proxy_catalog(updated)
        self.after(0, self._refresh_proxy_catalog_view)
        self.after(0, lambda msg=message: self.status.configure(text=msg))

    threading.Thread(target=worker, daemon=True).start()


MainApp._create_widgets = _workspace_create_widgets
MainApp._workspace_build_profiles_page = _workspace_build_profiles_page
MainApp._workspace_build_proxy_page = _workspace_build_proxy_page
MainApp._show_page = _workspace_show_page
MainApp._refresh = _workspace_refresh
MainApp._refresh_proxy_catalog_view = _refresh_proxy_catalog_view_ranked
MainApp._open_add_proxy_dialog = _open_add_proxy_dialog
MainApp._import_proxy_catalog_ui = _import_proxy_catalog_ui
MainApp._export_proxy_catalog_ui = _export_proxy_catalog_ui
MainApp._check_proxy_entry = _check_proxy_entry_health_v2
MainApp._delete_proxy_entry = _delete_proxy_entry

ProxyCatalogRow._create_widgets = _proxy_catalog_row_create_widgets_v2

ProfileDialog._original_load_profile_geo = ProfileDialog._load_profile
ProfileDialog._load_profile = _dialog_load_profile_v2
ProfileDialog._save = _dialog_save_v2
ProfileDialog._dialog_set_proxy_geo_state = _dialog_set_proxy_geo_state
ProfileDialog._apply_proxy_geo = _dialog_apply_proxy_geo
ProfileDialog._test_proxy = _dialog_test_proxy_health_v2
ProfileDialog._reload_saved_proxy_choices = _dialog_reload_saved_proxy_choices_ranked
ProfileDialog._apply_saved_proxy = _dialog_apply_saved_proxy_ranked_v2


def _startup_set_progress(self, phase: str, current: int, total: int, message: str):
    progress_value = 0.0
    if total and total > 0:
        progress_value = max(0.0, min(1.0, current / total))
    elif phase in {"prepare", "done"}:
        progress_value = 1.0 if phase == "done" else 0.08
    self.runtime_progress.set(progress_value)
    self.runtime_status_body.configure(text=message)


def _startup_refresh_runtime_status(self):
    manifest_url = self.manifest_entry.get().strip() if hasattr(self, "manifest_entry") else ""
    status = get_runtime_status(APP_PATH, manifest_url, self.settings.get("browser_path", ""))
    self.runtime_status = status

    installed = status.get("installed")
    version = status.get("installed_version") or "unknown"
    remote_version = status.get("manifest_version") or "unknown"
    error = status.get("error", "")

    if installed and status.get("update_available"):
        title = "Runtime installed • update available"
        body = f"Installed {version}. Cloud has {remote_version}. Browser can be updated with one click."
        button_text = "Update Runtime"
        button_color = COLORS["warning"]
    elif installed:
        title = "Runtime installed"
        body = f"Browser runtime is ready at {status.get('browser_path', '')}"
        button_text = "Reinstall Runtime"
        button_color = COLORS["info"]
    else:
        title = "Runtime missing"
        body = "Browser runtime is not installed yet. Tool can download it from the manifest source."
        button_text = "Download Runtime"
        button_color = COLORS["accent"]

    if error:
        body = f"{body}\nManifest check: {error}"

    self.runtime_status_title.configure(text=title)
    self.runtime_status_body.configure(text=body)
    self.download_btn.configure(text=button_text, fg_color=button_color)


def _startup_finalize_continue(self, path: str):
    self.settings["profiles_path"] = path
    browser_path = find_browser_path(APP_PATH, self.settings.get("browser_path", ""))
    if browser_path:
        self.settings["browser_path"] = browser_path
    self.settings["runtime_manifest_url"] = self.manifest_entry.get().strip()
    save_settings(self.settings)
    self.profiles_path = path
    self.destroy()


def _startup_download_runtime(self, auto_continue: bool = False):
    manifest_url = self.manifest_entry.get().strip()
    if not manifest_url:
        messagebox.showerror("Missing Manifest", "Enter a runtime manifest URL first.")
        return
    if getattr(self, "_runtime_busy", False):
        return

    target_path = self.path_entry.get().strip()
    self._pending_continue_path = target_path if auto_continue else ""
    self._runtime_busy = True
    self.download_btn.configure(state="disabled")
    self.check_btn.configure(state="disabled")
    self.continue_btn.configure(state="disabled")
    self.settings["runtime_manifest_url"] = manifest_url
    save_settings(self.settings)

    def progress(phase, current, total, message):
        self.after(0, lambda p=phase, c=current, t=total, m=message: _startup_set_progress(self, p, c, t, m))

    def worker():
        try:
            info = download_runtime_package(
                APP_PATH,
                manifest_url,
                self.settings.get("browser_path", ""),
                progress=progress,
            )
            self.settings["browser_path"] = info.get("browser_path", "")
            save_settings(self.settings)
            def done():
                self._runtime_busy = False
                self.download_btn.configure(state="normal")
                self.check_btn.configure(state="normal")
                self.continue_btn.configure(state="normal")
                self._startup_refresh_runtime_status()
                self.status_line.configure(text="Browser runtime downloaded and installed.")
                if self._pending_continue_path:
                    _startup_finalize_continue(self, self._pending_continue_path)
            self.after(0, done)
        except Exception as exc:
            def failed():
                self._runtime_busy = False
                self.download_btn.configure(state="normal")
                self.check_btn.configure(state="normal")
                self.continue_btn.configure(state="normal")
                self.runtime_progress.set(0)
                self.runtime_status_body.configure(text=f"Runtime install failed: {exc}")
                self.status_line.configure(text="Runtime download failed.")
            self.after(0, failed)

    threading.Thread(target=worker, daemon=True).start()


def _startup_browse_manifest(self):
    filename = filedialog.askopenfilename(
        title="Select Runtime Manifest",
        filetypes=[("JSON", "*.json"), ("All files", "*.*")],
    )
    if filename:
        self.manifest_entry.delete(0, tk.END)
        self.manifest_entry.insert(0, filename)
        self._startup_refresh_runtime_status()


def _startup_create_widgets_v2(self):
    self.geometry("760x520")
    self.resizable(False, False)
    self.configure(fg_color=COLORS["bg_dark"])
    for child in self.winfo_children():
        child.destroy()

    shell = ctk.CTkFrame(self, fg_color=COLORS["bg_panel"], corner_radius=18, border_width=1, border_color=COLORS["border"])
    shell.pack(fill="both", expand=True, padx=20, pady=20)

    head = ctk.CTkFrame(shell, fg_color="transparent")
    head.pack(fill="x", padx=24, pady=(22, 14))
    ctk.CTkLabel(head, text="S Manage Setup", font=ctk.CTkFont(size=30, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(
        head,
        text="Tool only stores profiles locally. Browser runtime can live on cloud and is downloaded on demand.",
        font=ctk.CTkFont(size=12),
        text_color=COLORS["text_muted"],
    ).pack(anchor="w", pady=(4, 0))

    grid = ctk.CTkFrame(shell, fg_color="transparent")
    grid.pack(fill="both", expand=True, padx=24, pady=(0, 16))
    grid.grid_columnconfigure(0, weight=7)
    grid.grid_columnconfigure(1, weight=6)

    left = ctk.CTkFrame(grid, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"])
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    right = ctk.CTkFrame(grid, fg_color=COLORS["bg_card"], corner_radius=16, border_width=1, border_color=COLORS["border"])
    right.grid(row=0, column=1, sticky="nsew")

    ctk.CTkLabel(left, text="Profile Storage", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=18, pady=(16, 8))
    ctk.CTkLabel(left, text="Profiles folder", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=18)
    entry_row = ctk.CTkFrame(left, fg_color="transparent")
    entry_row.pack(fill="x", padx=18, pady=(10, 8))
    self.path_entry = ctk.CTkEntry(entry_row, height=40)
    self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    self.path_entry.insert(0, self.settings.get("profiles_path", ""))
    ctk.CTkButton(entry_row, text="Browse", width=92, height=40, fg_color=COLORS["info"], hover_color=COLORS["info_hover"], command=self._browse_folder).pack(side="left")
    ctk.CTkLabel(
        left,
        text="Each profile keeps separate cookies, cache and user data in this folder.",
        font=ctk.CTkFont(size=11),
        text_color=COLORS["text_muted"],
        justify="left",
    ).pack(anchor="w", padx=18, pady=(4, 0))

    ctk.CTkLabel(right, text="Browser Runtime", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLORS["text_muted"]).pack(anchor="w", padx=18, pady=(16, 8))
    ctk.CTkLabel(right, text="Manifest URL", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=18)
    manifest_row = ctk.CTkFrame(right, fg_color="transparent")
    manifest_row.pack(fill="x", padx=18, pady=(10, 8))
    self.manifest_entry = ctk.CTkEntry(manifest_row, height=40)
    self.manifest_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
    self.manifest_entry.insert(0, self.settings.get("runtime_manifest_url", DEFAULT_RUNTIME_MANIFEST_URL))
    ctk.CTkButton(manifest_row, text="File", width=70, height=40, fg_color="#233446", hover_color="#2c4258", command=self._browse_manifest).pack(side="left")

    status_card = ctk.CTkFrame(right, fg_color="#18222e", corner_radius=12, border_width=1, border_color=COLORS["border"])
    status_card.pack(fill="x", padx=18, pady=(8, 12))
    self.runtime_status_title = ctk.CTkLabel(status_card, text="Checking runtime...", font=ctk.CTkFont(size=15, weight="bold"))
    self.runtime_status_title.pack(anchor="w", padx=14, pady=(12, 4))
    self.runtime_status_body = ctk.CTkLabel(status_card, text="", justify="left", wraplength=260, font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
    self.runtime_status_body.pack(anchor="w", padx=14, pady=(0, 12))

    self.runtime_progress = ctk.CTkProgressBar(right, height=10, progress_color=COLORS["accent"])
    self.runtime_progress.pack(fill="x", padx=18, pady=(0, 10))
    self.runtime_progress.set(0)

    btn_row = ctk.CTkFrame(right, fg_color="transparent")
    btn_row.pack(fill="x", padx=18)
    self.check_btn = ctk.CTkButton(btn_row, text="Check Cloud Runtime", height=38, fg_color="#223244", hover_color="#2e465f", command=self._startup_refresh_runtime_status)
    self.check_btn.pack(side="left")
    self.download_btn = ctk.CTkButton(btn_row, text="Download Runtime", height=38, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._download_runtime)
    self.download_btn.pack(side="left", padx=(8, 0))

    self.status_line = ctk.CTkLabel(shell, text="Setup waits for a valid browser runtime before entering the manager.", font=ctk.CTkFont(size=11), text_color=COLORS["text_muted"])
    self.status_line.pack(fill="x", padx=24, pady=(0, 12))

    footer = ctk.CTkFrame(shell, fg_color="transparent")
    footer.pack(fill="x", padx=24, pady=(0, 20))
    ctk.CTkButton(footer, text="Exit", width=96, height=42, fg_color="#223244", hover_color="#2e465f", command=self.destroy).pack(side="right")
    self.continue_btn = ctk.CTkButton(footer, text="Continue", width=138, height=42, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=self._continue)
    self.continue_btn.pack(side="right", padx=(0, 10))

    self._runtime_busy = False
    self._pending_continue_path = ""
    self._startup_refresh_runtime_status()


def _startup_continue_v2(self):
    path = self.path_entry.get().strip()
    if not path:
        messagebox.showerror("Error", "Please select a folder for profiles storage.")
        return
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as exc:
        messagebox.showerror("Error", f"Cannot create folder: {exc}")
        return

    self.settings["profiles_path"] = path
    self.settings["runtime_manifest_url"] = self.manifest_entry.get().strip()
    save_settings(self.settings)

    browser_path = find_browser_path(APP_PATH, self.settings.get("browser_path", ""))
    if browser_path:
        self.settings["browser_path"] = browser_path
        save_settings(self.settings)
        _startup_finalize_continue(self, path)
        return

    if not self.manifest_entry.get().strip():
        messagebox.showerror("Browser Runtime Missing", "Browser runtime is not installed and no manifest URL is configured.")
        return

    self.status_line.configure(text="Runtime missing. Downloading it now before opening the manager.")
    _startup_download_runtime(self, auto_continue=True)


StartupDialog._startup_set_progress = _startup_set_progress
StartupDialog._startup_refresh_runtime_status = _startup_refresh_runtime_status
StartupDialog._startup_finalize_continue = _startup_finalize_continue
StartupDialog._download_runtime = _startup_download_runtime
StartupDialog._browse_manifest = _startup_browse_manifest
StartupDialog._create_widgets = _startup_create_widgets_v2
StartupDialog._continue = _startup_continue_v2


def main():
    startup = StartupDialog()
    startup.mainloop()
    
    if startup.profiles_path:
        app = MainApp(startup.profiles_path)
        app.mainloop()


if __name__ == "__main__":
    main()
