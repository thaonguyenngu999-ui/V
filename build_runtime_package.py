"""
Create a standalone browser runtime package and manifest for cloud distribution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


BASE_DIR = Path(__file__).parent.resolve()
BROWSER_DIR = BASE_DIR / "browser"
DIST_DIR = BASE_DIR / "dist"
CLOUD_DIR = BASE_DIR / "cloud"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file_handle:
        while True:
            chunk = file_handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def zip_browser(source_dir: Path, zip_path: Path):
    files = [path for path in sorted(source_dir.rglob("*")) if path.is_file()]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(source_dir))


def main():
    parser = argparse.ArgumentParser(description="Build cloud browser runtime package")
    parser.add_argument("--browser-version", required=True, help="Browser runtime version")
    parser.add_argument(
        "--download-url",
        default="https://github.com/thaonguyenngu999-ui/V/releases/download/runtime-146.0.7680.76/browser-win-x64.zip",
        help="Public URL that clients should download",
    )
    parser.add_argument(
        "--output",
        default=str(DIST_DIR / "browser-win-x64.zip"),
        help="Output zip path",
    )
    parser.add_argument(
        "--manifest",
        default=str(CLOUD_DIR / "runtime-manifest.json"),
        help="Manifest output path",
    )
    args = parser.parse_args()

    source_dir = BROWSER_DIR
    if not source_dir.exists():
        raise SystemExit(f"Browser directory not found: {source_dir}")

    zip_path = Path(args.output).resolve()
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_browser(source_dir, zip_path)
    sha256 = sha256_file(zip_path)

    manifest = {
        "channel": "stable",
        "browser_version": args.browser_version,
        "platform": "win-x64",
        "archive_type": "zip",
        "download_url": args.download_url,
        "sha256": sha256,
        "size_bytes": zip_path.stat().st_size,
        "entry": "flat",
    }

    manifest_path = Path(args.manifest).resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as file_handle:
        json.dump(manifest, file_handle, indent=2)

    print(f"Runtime zip: {zip_path}")
    print(f"SHA256: {sha256}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
