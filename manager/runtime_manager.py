"""
Browser runtime management for cloud-hosted browser packages.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Optional


DEFAULT_RUNTIME_MANIFEST_URL = (
    "https://raw.githubusercontent.com/thaonguyenngu999-ui/V/main/cloud/runtime-manifest.json"
)
RUNTIME_DIRNAME = "browser"
RUNTIME_METADATA = "runtime.json"

ProgressCallback = Optional[Callable[[str, int, int, str], None]]


def _app_root(app_path: str | Path) -> Path:
    path = Path(app_path).resolve()
    if path.name.lower() == "manager":
        return path.parent
    return path


def _runtime_dir(app_path: str | Path) -> Path:
    return _app_root(app_path) / RUNTIME_DIRNAME


def _runtime_metadata_path(app_path: str | Path) -> Path:
    return _runtime_dir(app_path) / RUNTIME_METADATA


def _browser_path_candidates(app_path: str | Path, configured: Optional[str] = None) -> list[Path]:
    root = _app_root(app_path)
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend(
        [
            _runtime_dir(root) / "chrome.exe",
            root / "chrome.exe",
            root / "browser" / "chrome.exe",
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def find_browser_path(app_path: str | Path, configured: Optional[str] = None) -> Optional[str]:
    for candidate in _browser_path_candidates(app_path, configured):
        if candidate.exists():
            return str(candidate.resolve())
    return None


def load_manifest(manifest_url: str) -> Dict:
    if not manifest_url:
        raise ValueError("Manifest URL is empty")

    parsed = urllib.parse.urlparse(manifest_url)
    if parsed.scheme in ("http", "https", "file"):
        with urllib.request.urlopen(manifest_url, timeout=30) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)

    manifest_path = Path(manifest_url).expanduser()
    with open(manifest_path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def load_local_runtime_info(app_path: str | Path) -> Dict:
    metadata_path = _runtime_metadata_path(app_path)
    if not metadata_path.exists():
        return {}
    try:
        with open(metadata_path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except Exception:
        return {}


def save_local_runtime_info(app_path: str | Path, info: Dict):
    runtime_dir = _runtime_dir(app_path)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with open(_runtime_metadata_path(app_path), "w", encoding="utf-8") as file_handle:
        json.dump(info, file_handle, indent=2, ensure_ascii=False)


def get_runtime_status(
    app_path: str | Path,
    manifest_url: str = "",
    configured_browser_path: Optional[str] = None,
) -> Dict:
    browser_path = find_browser_path(app_path, configured_browser_path)
    local_info = load_local_runtime_info(app_path)
    status = {
        "installed": bool(browser_path),
        "browser_path": browser_path,
        "installed_version": local_info.get("browser_version", ""),
        "manifest_url": manifest_url or "",
        "manifest_version": "",
        "download_url": "",
        "update_available": False,
        "error": "",
    }
    if not manifest_url:
        return status
    try:
        manifest = load_manifest(manifest_url)
        status["manifest_version"] = str(manifest.get("browser_version", "")).strip()
        status["download_url"] = str(manifest.get("download_url", "")).strip()
        if status["manifest_version"]:
            status["update_available"] = status["manifest_version"] != status["installed_version"]
        return status
    except Exception as exc:
        status["error"] = str(exc)
        return status


def _report(progress: ProgressCallback, phase: str, current: int, total: int, message: str):
    if progress:
        progress(phase, current, total, message)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        while True:
            chunk = file_handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _download_to_file(url: str, dest: Path, progress: ProgressCallback):
    req = urllib.request.Request(url, headers={"User-Agent": "SManage Runtime Installer/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response, open(dest, "wb") as file_handle:
        total = int(response.headers.get("Content-Length", "0") or 0)
        current = 0
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            file_handle.write(chunk)
            current += len(chunk)
            _report(progress, "download", current, total, f"Downloading runtime {current}/{total or '?'} bytes")


def _resolve_extract_root(extract_dir: Path) -> Path:
    if (extract_dir / "chrome.exe").exists():
        return extract_dir
    if (extract_dir / "browser" / "chrome.exe").exists():
        return extract_dir / "browser"
    subdirs = [path for path in extract_dir.iterdir() if path.is_dir()]
    if len(subdirs) == 1:
        if (subdirs[0] / "chrome.exe").exists():
            return subdirs[0]
        if (subdirs[0] / "browser" / "chrome.exe").exists():
            return subdirs[0] / "browser"
    raise RuntimeError("Extracted runtime does not contain chrome.exe")


def download_and_install(
    app_path: str | Path,
    manifest_url: str,
    configured_browser_path: Optional[str] = None,
    progress: ProgressCallback = None,
) -> Dict:
    manifest = load_manifest(manifest_url)
    download_url = str(manifest.get("download_url", "")).strip()
    browser_version = str(manifest.get("browser_version", "")).strip()
    if not download_url:
        raise RuntimeError("Manifest missing download_url")

    runtime_dir = _runtime_dir(app_path)
    runtime_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="smanage-runtime-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        archive_path = temp_dir / "runtime.zip"
        _report(progress, "prepare", 0, 1, "Loading runtime manifest")
        _download_to_file(download_url, archive_path, progress)

        expected_sha = str(manifest.get("sha256", "")).strip().lower()
        if expected_sha:
            actual_sha = _sha256_file(archive_path)
            if actual_sha != expected_sha:
                raise RuntimeError("Runtime checksum mismatch")

        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        _report(progress, "extract", 0, 1, "Extracting runtime package")
        if not zipfile.is_zipfile(archive_path):
            raise RuntimeError("Only ZIP runtime packages are supported right now")
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.namelist()
            total_members = len(members)
            for index, member in enumerate(members, start=1):
                archive.extract(member, extract_dir)
                _report(progress, "extract", index, total_members, f"Extracting {index}/{total_members} files")

        source_root = _resolve_extract_root(extract_dir)
        backup_dir = runtime_dir.with_name(f"{runtime_dir.name}.bak")
        if backup_dir.exists():
            shutil.rmtree(backup_dir, ignore_errors=True)
        if runtime_dir.exists():
            runtime_dir.replace(backup_dir)

        try:
            shutil.copytree(source_root, runtime_dir, dirs_exist_ok=True)
        except Exception:
            if runtime_dir.exists():
                shutil.rmtree(runtime_dir, ignore_errors=True)
            if backup_dir.exists():
                backup_dir.replace(runtime_dir)
            raise
        else:
            if backup_dir.exists():
                shutil.rmtree(backup_dir, ignore_errors=True)

        browser_path = runtime_dir / "chrome.exe"
        if not browser_path.exists():
            raise RuntimeError("Installed runtime missing chrome.exe")

        info = {
            "browser_version": browser_version,
            "download_url": download_url,
            "manifest_url": manifest_url,
            "installed_at": datetime.now().isoformat(),
            "browser_path": str(browser_path.resolve()),
        }
        save_local_runtime_info(app_path, info)
        _report(progress, "done", 1, 1, "Runtime installed")
        return info
