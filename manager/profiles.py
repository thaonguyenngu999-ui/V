"""
S Manage - Browser Profile Manager
Quan ly profiles cho browser S Manage
"""

import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fingerprint import FingerprintGenerator
from fingerprint_utils import (
    DEFAULT_CHROME_VERSION,
    DEFAULT_PLATFORM,
    DEFAULT_PLATFORM_VERSION,
    language_list,
    normalize_device_memory,
    normalize_gpu_config,
    normalize_profile_cpu_cores,
    normalize_profile_ram_gb,
    timezone_offset_for_name,
)


@dataclass
class ProfileConfig:
    """Cau hinh cua mot profile"""

    id: str
    name: str
    created_at: str
    last_used: Optional[str] = None

    user_agent: Optional[str] = None
    screen_width: int = 1920
    screen_height: int = 1080
    timezone: str = "Asia/Ho_Chi_Minh"
    language: str = "vi-VN,vi"
    platform: str = DEFAULT_PLATFORM
    geo_country: str = ""
    geo_country_code: str = ""
    geo_region: str = ""
    geo_city: str = ""
    geo_latitude: Optional[float] = None
    geo_longitude: Optional[float] = None
    geo_accuracy: int = 20

    cpu_cores: int = 8
    ram_gb: int = 8

    webgl_vendor: str = "Google Inc. (NVIDIA)"
    webgl_renderer: str = (
        "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)"
    )

    proxy_enabled: bool = False
    proxy_type: str = "http"
    proxy_host: str = ""
    proxy_port: int = 0
    proxy_username: str = ""
    proxy_password: str = ""

    notes: str = ""
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

        self.cpu_cores = normalize_profile_cpu_cores(
            getattr(self, "cpu_cores", None) or getattr(self, "hardware_concurrency", None) or 8
        )
        self.ram_gb = normalize_profile_ram_gb(
            getattr(self, "ram_gb", None) or getattr(self, "device_memory", None) or 8
        )
        _, self.webgl_vendor, self.webgl_renderer = normalize_gpu_config(
            getattr(self, "webgl_vendor", None),
            getattr(self, "webgl_renderer", None),
        )
        self.platform = self.platform or DEFAULT_PLATFORM


class ProfileManager:
    """Quan ly cac browser profiles"""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)
        self.load_config()
        self.fingerprint_gen = FingerprintGenerator()
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self):
        """Load cau hinh tu file"""
        with open(self.config_path, "r", encoding="utf-8") as file_handle:
            config = json.load(file_handle)

        self.browser_path = Path(config["browser_path"])
        self.profiles_dir = Path(config["profiles_dir"])
        self.default_args = config.get("default_args", [])

    def profile_dir(self, profile_id: str) -> Path:
        return self.profiles_dir / f"profile_{profile_id}"

    def user_data_dir(self, profile_id: str) -> Path:
        return self.profile_dir(profile_id) / "UserData"

    def create_profile(self, name: str, fingerprint: Optional[Dict] = None) -> ProfileConfig:
        """Tao profile moi"""
        profile_id = str(uuid.uuid4())[:8]
        normalized = self._normalize_profile_input(fingerprint or self.fingerprint_gen.generate())

        profile = ProfileConfig(
            id=profile_id,
            name=name,
            created_at=datetime.now().isoformat(),
            **normalized,
        )

        profile_path = self.profile_dir(profile_id)
        profile_path.mkdir(parents=True, exist_ok=True)
        self.user_data_dir(profile_id).mkdir(exist_ok=True)

        self._save_profile_config(profile)
        print(f"[+] Created profile: {name} (ID: {profile_id})")
        return profile

    def _normalize_profile_input(self, data: Dict) -> Dict:
        normalized = dict(data)

        normalized["user_agent"] = self._normalize_user_agent(normalized.get("user_agent"))
        normalized["cpu_cores"] = normalize_profile_cpu_cores(
            normalized.get("cpu_cores", normalized.get("hardware_concurrency", 8))
        )
        normalized["ram_gb"] = normalize_profile_ram_gb(
            normalized.get("ram_gb", normalized.get("device_memory", 8))
        )
        _, normalized["webgl_vendor"], normalized["webgl_renderer"] = normalize_gpu_config(
            normalized.get("webgl_vendor"),
            normalized.get("webgl_renderer"),
        )
        normalized["platform"] = normalized.get("platform") or DEFAULT_PLATFORM

        normalized.pop("hardware_concurrency", None)
        normalized.pop("device_memory", None)
        normalized.pop("languages", None)
        normalized.pop("timezone_offset", None)
        normalized.pop("chrome_version", None)
        normalized.pop("chrome_major", None)
        normalized.pop("platform_version", None)

        return normalized

    def _save_profile_config(self, profile: ProfileConfig):
        """Luu config cua profile"""
        config_file = self.profile_dir(profile.id) / "config.json"
        with open(config_file, "w", encoding="utf-8") as file_handle:
            json.dump(asdict(profile), file_handle, indent=2, ensure_ascii=False)

    def load_profile(self, profile_id: str) -> Optional[ProfileConfig]:
        """Load profile tu file"""
        config_file = self.profile_dir(profile_id) / "config.json"
        if not config_file.exists():
            return None

        with open(config_file, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        return ProfileConfig(**data)

    def list_profiles(self) -> List[ProfileConfig]:
        """Liet ke tat ca profiles"""
        profiles = []
        for folder in self.profiles_dir.iterdir():
            if folder.is_dir() and folder.name.startswith("profile_"):
                profile_id = folder.name.replace("profile_", "")
                profile = self.load_profile(profile_id)
                if profile:
                    profiles.append(profile)
        return sorted(profiles, key=lambda profile: profile.created_at, reverse=True)

    def find_profile(self, profile_ref: str) -> Optional[ProfileConfig]:
        """Find profile by id or exact name"""
        direct = self.load_profile(profile_ref)
        if direct:
            return direct

        lowered = profile_ref.strip().lower()
        for profile in self.list_profiles():
            if profile.name.strip().lower() == lowered:
                return profile
        return None

    def delete_profile(self, profile_id: str) -> bool:
        """Xoa profile"""
        profile_path = self.profile_dir(profile_id)
        if profile_path.exists():
            shutil.rmtree(profile_path)
            print(f"[-] Deleted profile: {profile_id}")
            return True
        return False

    def clone_profile(self, profile_id: str, new_name: str) -> Optional[ProfileConfig]:
        """Clone profile"""
        source = self.load_profile(profile_id)
        if not source:
            return None

        fingerprint = {
            "user_agent": source.user_agent,
            "screen_width": source.screen_width,
            "screen_height": source.screen_height,
            "timezone": source.timezone,
            "language": source.language,
            "platform": source.platform,
            "geo_country": source.geo_country,
            "geo_country_code": source.geo_country_code,
            "geo_region": source.geo_region,
            "geo_city": source.geo_city,
            "geo_latitude": source.geo_latitude,
            "geo_longitude": source.geo_longitude,
            "geo_accuracy": source.geo_accuracy,
            "cpu_cores": source.cpu_cores,
            "ram_gb": source.ram_gb,
            "webgl_vendor": source.webgl_vendor,
            "webgl_renderer": source.webgl_renderer,
        }

        new_profile = self.create_profile(new_name, fingerprint)

        source_data = self.user_data_dir(profile_id)
        dest_data = self.user_data_dir(new_profile.id)
        if source_data.exists() and any(source_data.iterdir()):
            shutil.rmtree(dest_data)
            shutil.copytree(source_data, dest_data)

        print(f"[+] Cloned profile: {source.name} -> {new_name}")
        return new_profile

    def build_fingerprint(self, profile: ProfileConfig) -> Dict:
        """Build runtime fingerprint for launcher/CDP injection"""
        user_agent = self._normalize_user_agent(profile.user_agent)
        chrome_version = self._extract_chrome_version(user_agent)
        chrome_major = chrome_version.split(".")[0]
        languages = language_list(profile.language)
        primary_language = languages[0] if languages else "en-US"

        return {
            "screen_width": profile.screen_width,
            "screen_height": profile.screen_height,
            "platform": profile.platform or DEFAULT_PLATFORM,
            "language": primary_language,
            "languages": languages,
            "hardware_concurrency": normalize_profile_cpu_cores(profile.cpu_cores),
            "device_memory": normalize_device_memory(profile.ram_gb),
            "timezone": profile.timezone,
            "timezone_offset": timezone_offset_for_name(profile.timezone),
            "webgl_vendor": profile.webgl_vendor,
            "webgl_renderer": profile.webgl_renderer,
            "user_agent": user_agent,
            "chrome_version": chrome_version,
            "chrome_major": chrome_major,
            "platform_version": DEFAULT_PLATFORM_VERSION,
            "geo_country": profile.geo_country,
            "geo_country_code": profile.geo_country_code,
            "geo_region": profile.geo_region,
            "geo_city": profile.geo_city,
            "geo_latitude": profile.geo_latitude,
            "geo_longitude": profile.geo_longitude,
            "geo_accuracy": profile.geo_accuracy,
        }

    def build_proxy_url(self, profile: ProfileConfig) -> Optional[str]:
        """Build proxy URL if profile has proxy enabled"""
        if not profile.proxy_enabled or not profile.proxy_host:
            return None
        if profile.proxy_username:
            return (
                f"{profile.proxy_type}://{profile.proxy_username}:{profile.proxy_password}"
                f"@{profile.proxy_host}:{profile.proxy_port}"
            )
        return f"{profile.proxy_type}://{profile.proxy_host}:{profile.proxy_port}"

    def launch_profile(
        self,
        profile_id: str,
        start_url: str = "about:blank",
        return_launcher: bool = False,
        debug_port: Optional[int] = None,
        debug_host: str = "127.0.0.1",
    ):
        """Khoi dong browser voi profile (su dung CDP injection)"""
        from browser_launcher import BrowserLauncher

        profile = self.load_profile(profile_id)
        if not profile:
            print(f"[!] Profile not found: {profile_id}")
            return None

        profile.last_used = datetime.now().isoformat()
        profile.user_agent = self._normalize_user_agent(profile.user_agent)
        self._save_profile_config(profile)

        launcher = BrowserLauncher(str(self.browser_path))
        process = launcher.launch(
            str(self.user_data_dir(profile_id)),
            self.build_fingerprint(profile),
            proxy=self.build_proxy_url(profile),
            start_url=start_url,
            debug_port=debug_port,
            debug_host=debug_host,
        )

        if return_launcher:
            return process, launcher, profile
        return process

    def launch_profile_for_playwright(
        self,
        profile_id: str,
        start_url: str = "about:blank",
        timeout_seconds: float = 15.0,
        debug_port: Optional[int] = None,
        debug_host: str = "127.0.0.1",
    ) -> Optional[Dict]:
        """Launch a profile and return CDP metadata for Playwright attach"""
        launched = self.launch_profile(
            profile_id,
            start_url=start_url,
            return_launcher=True,
            debug_port=debug_port,
            debug_host=debug_host,
        )
        if not launched:
            return None

        process, launcher, profile = launched
        debug_info = launcher.wait_for_debugging_endpoint(timeout_seconds=timeout_seconds)
        if not debug_info:
            return {
                "process": process,
                "launcher": launcher,
                "profile": profile,
                "debug_port": launcher.debug_port,
                "cdp_endpoint": launcher.get_cdp_http_url(),
                "browser_ws_url": None,
            }

        debug_info.update(
            {
                "process": process,
                "launcher": launcher,
                "profile": profile,
            }
        )
        return debug_info

    def export_profile(self, profile_id: str, export_path: str) -> bool:
        """Export profile ra file zip"""
        profile_path = self.profile_dir(profile_id)
        if not profile_path.exists():
            return False

        archive_path = Path(export_path)
        archive_base = archive_path.with_suffix("") if archive_path.suffix.lower() == ".zip" else archive_path
        final_archive = shutil.make_archive(str(archive_base), "zip", profile_path)
        print(f"[+] Exported to: {final_archive}")
        return True

    def import_profile(self, zip_path: str, new_name: Optional[str] = None) -> Optional[ProfileConfig]:
        """Import profile tu file zip"""
        if not os.path.exists(zip_path):
            return None

        new_id = str(uuid.uuid4())[:8]
        profile_path = self.profile_dir(new_id)
        shutil.unpack_archive(zip_path, profile_path)

        profile = self.load_profile(new_id)
        if profile:
            profile.id = new_id
            if new_name:
                profile.name = new_name
            profile.created_at = datetime.now().isoformat()
            self._save_profile_config(profile)

        print(f"[+] Imported profile: {profile.name}")
        return profile

    @staticmethod
    def _extract_chrome_version(user_agent: str) -> str:
        marker = "Chrome/"
        if marker in user_agent:
            version = user_agent.split(marker, 1)[1].split(" ", 1)[0]
            if version:
                return version
        return FingerprintGenerator.LATEST_CHROME_VERSION

    @staticmethod
    def _normalize_user_agent(user_agent: Optional[str]) -> str:
        if not user_agent:
            return FingerprintGenerator().generate_user_agent(DEFAULT_CHROME_VERSION)

        updated = re.sub(r"Chrome/[\d.]+", f"Chrome/{DEFAULT_CHROME_VERSION}", user_agent, count=1)
        if updated != user_agent:
            return updated
        return FingerprintGenerator().generate_user_agent(DEFAULT_CHROME_VERSION)


if __name__ == "__main__":
    manager = ProfileManager("config.json")

    print("\n=== Profiles ===")
    profiles = manager.list_profiles()
    for profile in profiles:
        print(f"  [{profile.id}] {profile.name} - Created: {profile.created_at[:10]}")

    if not profiles:
        print("\n=== Creating test profile ===")
        profile = manager.create_profile("Test Profile 1")
        print(f"  User-Agent: {profile.user_agent}")
        print(f"  Screen: {profile.screen_width}x{profile.screen_height}")
        print(f"  CPU/RAM: {profile.cpu_cores} cores / {profile.ram_gb} GB")
        print(f"  WebGL: {profile.webgl_renderer}")

        print("\n=== Launching ===")
        manager.launch_profile(profile.id)
