"""
Fingerprint Generator
Tao fingerprint ngau nhien cho browser profiles
"""

import random
from typing import Dict, List

from fingerprint_utils import (
    DEFAULT_CHROME_VERSION,
    DEFAULT_PLATFORM,
    DEFAULT_PLATFORM_VERSION,
    GPU_PRESETS,
    TIMEZONE_PRESETS,
    brand_to_vendor,
    language_list,
    normalize_device_memory,
    normalize_profile_cpu_cores,
    normalize_profile_ram_gb,
)


class FingerprintGenerator:
    """Tao fingerprint ngau nhien"""

    LATEST_CHROME_VERSION = DEFAULT_CHROME_VERSION

    CHROME_VERSIONS = [DEFAULT_CHROME_VERSION]

    WINDOWS_VERSIONS = [
        "Windows NT 10.0",
    ]

    RESOLUTIONS = [
        (1920, 1080),
        (1366, 768),
        (1536, 864),
        (1440, 900),
        (1600, 900),
        (2560, 1440),
        (1280, 720),
        (1680, 1050),
    ]

    TIMEZONES = [(data["name"], data["offset"]) for data in TIMEZONE_PRESETS.values()]

    LANGUAGES = [
        "vi-VN,vi,en-US,en",
        "en-US,en",
        "en-GB,en",
    ]

    WEBGL_VENDORS = [brand_to_vendor(brand) for brand in GPU_PRESETS]
    WEBGL_RENDERERS = {
        brand_to_vendor(brand): list(renderers.values())
        for brand, renderers in GPU_PRESETS.items()
    }

    HARDWARE_CONCURRENCY = [2, 4, 6, 8, 10, 12, 16, 24, 32]
    DEVICE_MEMORY = [2, 4, 8, 16, 32, 64]
    PLATFORMS = [DEFAULT_PLATFORM]

    OS_VERSIONS = {
        "Windows NT 10.0": DEFAULT_PLATFORM_VERSION,
    }

    def generate_user_agent(self, chrome_version: str = None) -> str:
        """Tao User Agent ngau nhien"""
        if not chrome_version:
            chrome_version = random.choice(self.CHROME_VERSIONS)
        windows = random.choice(self.WINDOWS_VERSIONS)
        return (
            f"Mozilla/5.0 ({windows}; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        )

    def generate(self) -> Dict:
        """Tao fingerprint ngau nhien"""
        vendor = random.choice(self.WEBGL_VENDORS)
        renderer = random.choice(self.WEBGL_RENDERERS[vendor])
        width, height = random.choice(self.RESOLUTIONS)
        timezone, tz_offset = random.choice(self.TIMEZONES)
        language = random.choice(self.LANGUAGES)
        cpu_cores = normalize_profile_cpu_cores(random.choice(self.HARDWARE_CONCURRENCY))
        ram_gb = normalize_profile_ram_gb(random.choice(self.DEVICE_MEMORY))

        chrome_version = random.choice(self.CHROME_VERSIONS)
        chrome_major = chrome_version.split(".")[0]

        return {
            "user_agent": self.generate_user_agent(chrome_version),
            "chrome_version": chrome_version,
            "chrome_major": chrome_major,
            "platform_version": DEFAULT_PLATFORM_VERSION,
            "screen_width": width,
            "screen_height": height,
            "timezone": timezone,
            "timezone_offset": tz_offset,
            "language": language,
            "languages": language_list(language),
            "platform": DEFAULT_PLATFORM,
            "webgl_vendor": vendor,
            "webgl_renderer": renderer,
            "hardware_concurrency": cpu_cores,
            "device_memory": normalize_device_memory(ram_gb),
            "cpu_cores": cpu_cores,
            "ram_gb": ram_gb,
        }

    def generate_similar(self, base: Dict) -> Dict:
        """Tao fingerprint tuong tu (chi thay doi 1-2 thuoc tinh)"""
        result = base.copy()

        changes = random.randint(1, 2)
        attrs_to_change = random.sample(
            ["user_agent", "screen_width", "timezone", "webgl_renderer", "hardware_concurrency", "device_memory"],
            changes,
        )

        for attr in attrs_to_change:
            if attr == "user_agent":
                result["user_agent"] = self.generate_user_agent()
            elif attr == "screen_width":
                w, h = random.choice(self.RESOLUTIONS)
                result["screen_width"] = w
                result["screen_height"] = h
            elif attr == "timezone":
                timezone, tz_offset = random.choice(self.TIMEZONES)
                result["timezone"] = timezone
                result["timezone_offset"] = tz_offset
            elif attr == "webgl_renderer":
                vendor = result.get("webgl_vendor", random.choice(self.WEBGL_VENDORS))
                result["webgl_renderer"] = random.choice(
                    self.WEBGL_RENDERERS.get(vendor, self.WEBGL_RENDERERS[brand_to_vendor("NVIDIA")])
                )
            elif attr == "hardware_concurrency":
                cpu_cores = normalize_profile_cpu_cores(random.choice(self.HARDWARE_CONCURRENCY))
                result["hardware_concurrency"] = cpu_cores
                result["cpu_cores"] = cpu_cores
            elif attr == "device_memory":
                ram_gb = normalize_profile_ram_gb(random.choice(self.DEVICE_MEMORY))
                result["device_memory"] = normalize_device_memory(ram_gb)
                result["ram_gb"] = ram_gb

        return result

    def get_templates(self) -> List[Dict]:
        """Lay danh sach templates fingerprint"""
        return [
            {
                "name": "Vietnam - Desktop",
                "fingerprint": {
                    "user_agent": self.generate_user_agent(self.LATEST_CHROME_VERSION),
                    "screen_width": 1920,
                    "screen_height": 1080,
                    "timezone": "Asia/Ho_Chi_Minh",
                    "timezone_offset": -420,
                    "language": "vi-VN,vi,en-US,en",
                    "languages": language_list("vi-VN,vi,en-US,en"),
                    "platform": DEFAULT_PLATFORM,
                    "webgl_vendor": brand_to_vendor("NVIDIA"),
                    "webgl_renderer": GPU_PRESETS["NVIDIA"]["GTX 1650"],
                    "hardware_concurrency": 8,
                    "device_memory": 8,
                    "cpu_cores": 8,
                    "ram_gb": 8,
                },
            },
            {
                "name": "USA - Desktop",
                "fingerprint": {
                    "user_agent": self.generate_user_agent(self.LATEST_CHROME_VERSION),
                    "screen_width": 1920,
                    "screen_height": 1080,
                    "timezone": "America/New_York",
                    "timezone_offset": 300,
                    "language": "en-US,en",
                    "languages": language_list("en-US,en"),
                    "platform": DEFAULT_PLATFORM,
                    "webgl_vendor": brand_to_vendor("NVIDIA"),
                    "webgl_renderer": GPU_PRESETS["NVIDIA"]["RTX 3060"],
                    "hardware_concurrency": 8,
                    "device_memory": 8,
                    "cpu_cores": 8,
                    "ram_gb": 8,
                },
            },
            {
                "name": "UK - Laptop",
                "fingerprint": {
                    "user_agent": self.generate_user_agent(self.LATEST_CHROME_VERSION),
                    "screen_width": 1366,
                    "screen_height": 768,
                    "timezone": "Europe/London",
                    "timezone_offset": 0,
                    "language": "en-GB,en",
                    "languages": language_list("en-GB,en"),
                    "platform": DEFAULT_PLATFORM,
                    "webgl_vendor": brand_to_vendor("Intel"),
                    "webgl_renderer": GPU_PRESETS["Intel"]["UHD Graphics 620"],
                    "hardware_concurrency": 4,
                    "device_memory": 8,
                    "cpu_cores": 4,
                    "ram_gb": 8,
                },
            },
        ]


if __name__ == "__main__":
    generator = FingerprintGenerator()

    print("=== Random Fingerprint ===")
    fingerprint = generator.generate()
    for key, value in fingerprint.items():
        print(f"  {key}: {value}")

    print("\n=== Templates ===")
    for template in generator.get_templates():
        print(f"  - {template['name']}")
