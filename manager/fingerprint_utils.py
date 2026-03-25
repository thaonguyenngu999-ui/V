"""
Shared fingerprint presets and normalization helpers.
"""

from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple

DEFAULT_CHROME_VERSION = "146.0.7680.76"
DEFAULT_PLATFORM = "Win32"
DEFAULT_PLATFORM_VERSION = "10.0.0"
DEFAULT_GPU_BRAND = "NVIDIA"
DEFAULT_TIMEZONE_LABEL = "Vietnam (UTC+7)"

CPU_CORE_CHOICES = [2, 4, 6, 8, 10, 12, 16, 24, 32]
PROFILE_RAM_CHOICES = [2, 4, 8, 16, 32, 64]
DEVICE_MEMORY_BUCKETS = [0.25, 0.5, 1, 2, 4, 8, 16, 32, 64]

GPU_PRESETS: Dict[str, Dict[str, str]] = {
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


def brand_to_vendor(brand: str) -> str:
    return f"Google Inc. ({brand})"


def gpu_models_for_brand(brand: str) -> Iterable[str]:
    return GPU_PRESETS.get(brand, {}).keys()


def default_gpu_model(brand: str = DEFAULT_GPU_BRAND) -> str:
    models = list(gpu_models_for_brand(brand))
    if not models:
        models = list(gpu_models_for_brand(DEFAULT_GPU_BRAND))
    return models[0]


def default_gpu_renderer(brand: str = DEFAULT_GPU_BRAND) -> str:
    model = default_gpu_model(brand)
    return GPU_PRESETS.get(brand, GPU_PRESETS[DEFAULT_GPU_BRAND])[model]


def coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def coerce_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def nearest_choice(value, choices, default):
    numeric = coerce_float(value, float(default))
    return min(choices, key=lambda choice: (abs(choice - numeric), choice))


def normalize_profile_cpu_cores(value, default: int = 8) -> int:
    normalized = nearest_choice(value, CPU_CORE_CHOICES, default)
    return max(1, int(normalized))


def normalize_profile_ram_gb(value, default: int = 8) -> int:
    normalized = nearest_choice(value, PROFILE_RAM_CHOICES, default)
    return int(normalized)


def normalize_device_memory(value, default: float = 8) -> float:
    normalized = nearest_choice(value, DEVICE_MEMORY_BUCKETS, default)
    if float(normalized).is_integer():
        return int(normalized)
    return float(normalized)


def infer_gpu_brand(webgl_vendor: Optional[str], webgl_renderer: Optional[str]) -> str:
    combined = " ".join(part for part in [webgl_vendor or "", webgl_renderer or ""] if part).upper()
    for brand in GPU_PRESETS:
        if brand.upper() in combined:
            return brand
    return DEFAULT_GPU_BRAND


def find_gpu_model_by_renderer(webgl_renderer: Optional[str]) -> Optional[Tuple[str, str]]:
    if not webgl_renderer:
        return None
    for brand, models in GPU_PRESETS.items():
        for model_name, renderer in models.items():
            if renderer == webgl_renderer:
                return brand, model_name
    return None


def normalize_gpu_config(
    webgl_vendor: Optional[str],
    webgl_renderer: Optional[str],
) -> Tuple[str, str, str]:
    matched = find_gpu_model_by_renderer(webgl_renderer)
    if matched:
        brand, _ = matched
        return brand, brand_to_vendor(brand), webgl_renderer

    brand = infer_gpu_brand(webgl_vendor, webgl_renderer)
    renderer = default_gpu_renderer(brand)
    return brand, brand_to_vendor(brand), renderer


def normalize_language(language: Optional[str], default: str = "en-US,en") -> str:
    raw = (language or default).strip()
    return raw or default


def language_list(language: Optional[str]) -> list[str]:
    raw = normalize_language(language)
    items = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk or chunk in items:
            continue
        items.append(chunk)
        base = chunk.split("-")[0]
        if base and base not in items:
            items.append(base)
    return items or ["en-US", "en"]


def timezone_offset_for_name(timezone_name: Optional[str], default: int = -420) -> int:
    if not timezone_name:
        return default
    for preset in TIMEZONE_PRESETS.values():
        if preset["name"] == timezone_name:
            return preset["offset"]
    return default
