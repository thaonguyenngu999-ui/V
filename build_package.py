"""
S Manage - Build Script
Creates standalone executable for distribution
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent.resolve()
MANAGER_DIR = BASE_DIR / "manager"
BROWSER_DIR = BASE_DIR / "browser"
OUTPUT_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"

sys.path.insert(0, str(MANAGER_DIR))
from app_meta import APP_NAME, APP_VERSION_LABEL, RELEASE_NAME  # noqa: E402


MANAGER_FILES = [
    "app_meta.py",
    "profiles.py",
    "fingerprint.py",
    "fingerprint_utils.py",
    "browser_launcher.py",
    "playwright_attach.py",
    "runtime_manager.py",
]

ROOT_HELPERS = [
    "build_release_with_progress.py",
    "build_runtime_package.py",
    "launch_profile_for_playwright.py",
    "playwright_smoke_test.py",
]


def log_phase(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def remove_output_path(path: Path):
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def summarize_tree(root: Path) -> tuple[int, int]:
    file_count = 0
    total_bytes = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        file_count += 1
        total_bytes += path.stat().st_size
    return file_count, total_bytes


def format_bytes(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{num_bytes} B"


def copytree_with_progress(src: Path, dst: Path, label: str):
    total_files, total_bytes = summarize_tree(src)
    copied_files = 0
    copied_bytes = 0
    last_percent = -1

    for path in sorted(src.rglob("*")):
        target = dst / path.relative_to(src)
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied_files += 1
        copied_bytes += path.stat().st_size

        percent = int((copied_bytes / total_bytes) * 100) if total_bytes else 100
        if percent != last_percent and (percent % 5 == 0 or copied_files == total_files):
            log_phase(
                f"{label}: {percent:3d}% ({copied_files}/{total_files} files, "
                f"{format_bytes(copied_bytes)}/{format_bytes(total_bytes)})"
            )
            last_percent = percent


def zip_directory_with_progress(base_dir: Path, source_dir: Path, zip_path: Path):
    files = [path for path in sorted(source_dir.rglob("*")) if path.is_file()]
    total_files = len(files)
    total_bytes = sum(path.stat().st_size for path in files)
    zipped_files = 0
    zipped_bytes = 0
    last_percent = -1

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(base_dir))
            zipped_files += 1
            zipped_bytes += path.stat().st_size
            percent = int((zipped_bytes / total_bytes) * 100) if total_bytes else 100
            if percent != last_percent and (percent % 5 == 0 or zipped_files == total_files):
                log_phase(
                    f"ZIP progress: {percent:3d}% ({zipped_files}/{total_files} files, "
                    f"{format_bytes(zipped_bytes)}/{format_bytes(total_bytes)})"
                )
                last_percent = percent


def check_requirements():
    """Check and install required packages"""
    log_phase("Checking requirements...")
    required = ["customtkinter", "pyinstaller", "pillow"]

    for pkg in required:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  OK {pkg}")
        except ImportError:
            print(f"  Installing {pkg}...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                check=False,
                capture_output=True,
            )


def build_exe():
    """Build executable with PyInstaller"""
    log_phase("Building executable...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale_path in [
        OUTPUT_DIR / "SManage",
        OUTPUT_DIR / "SManage-Release",
        OUTPUT_DIR / "SManage-Portable",
        OUTPUT_DIR / f"{RELEASE_NAME}.zip",
    ]:
        remove_output_path(stale_path)

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=SManage",
        "--onedir",
        "--windowed",
        "--icon=icon.ico" if (MANAGER_DIR / "icon.ico").exists() else "",
        f"--distpath={OUTPUT_DIR}",
        f"--workpath={BUILD_DIR}",
        "--add-data",
        f"{MANAGER_DIR / 'profiles.py'};.",
        "--add-data",
        f"{MANAGER_DIR / 'fingerprint.py'};.",
        "--add-data",
        f"{MANAGER_DIR / 'fingerprint_utils.py'};.",
        "--add-data",
        f"{MANAGER_DIR / 'browser_launcher.py'};.",
        "--add-data",
        f"{MANAGER_DIR / 'playwright_attach.py'};.",
        "--add-data",
        f"{MANAGER_DIR / 'runtime_manager.py'};.",
        "--add-data",
        f"{MANAGER_DIR / 'app_meta.py'};.",
        "--hidden-import=customtkinter",
        "--hidden-import=PIL",
        "--hidden-import=app_meta",
        "--hidden-import=fingerprint_utils",
        "--hidden-import=playwright_attach",
        "--hidden-import=runtime_manager",
        "--collect-all=customtkinter",
        str(MANAGER_DIR / "gui_v3.py"),
    ]

    cmd = [part for part in cmd if part]
    print(f"  Running: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        cwd=str(MANAGER_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        if any(token in line for token in ["INFO:", "ERROR:", "WARNING:", "Building", "Analysis", "EXE", "COLLECT"]):
            log_phase(f"PyInstaller: {line}")
        else:
            print(line)

    result_code = process.wait()
    if result_code != 0:
        log_phase("Build failed")
        return False

    log_phase("Executable built")
    return True


def package_release():
    """Create final release package"""
    log_phase("Creating release package...")

    release_dir = OUTPUT_DIR / "SManage-Release"
    release_dir.mkdir(exist_ok=True)

    exe_dir = OUTPUT_DIR / "SManage"
    if exe_dir.exists():
        copytree_with_progress(exe_dir, release_dir / "manager", "Copy EXE")

    if BROWSER_DIR.exists():
        log_phase("Copying browser files into release package...")
        copytree_with_progress(BROWSER_DIR, release_dir / "browser", "Copy browser")

    manager_dir = release_dir / "manager"
    manager_dir.mkdir(exist_ok=True)
    for filename in MANAGER_FILES:
        src = MANAGER_DIR / filename
        if src.exists():
            shutil.copy(src, manager_dir)

    for filename in ROOT_HELPERS:
        src = BASE_DIR / filename
        if src.exists():
            shutil.copy(src, release_dir)

    launcher = """@echo off
cd /d "%~dp0manager"
start SManage.exe
"""
    (release_dir / "Start SManage.bat").write_text(launcher, encoding="utf-8")

    readme = f"""# {APP_NAME} - Antidetect Browser Manager

## Quick Start
1. Run "Start SManage.bat"
2. Select a folder to store profiles
3. Create profiles and start browsing

## Features
- Unique fingerprint per profile (GPU, CPU, RAM, Screen, Timezone)
- Playwright attach helper and sample smoke test
- Proxy support (HTTP/SOCKS5)
- CDP endpoint export with custom port support

## Requirements
- Windows 10/11 64-bit
- 4GB RAM minimum

## Version
{APP_VERSION_LABEL}
"""
    (release_dir / "README.txt").write_text(readme, encoding="utf-8")

    log_phase(f"Release package created: {release_dir}")
    zip_path = OUTPUT_DIR / f"{RELEASE_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()
    log_phase("Creating ZIP archive with progress...")
    zip_directory_with_progress(OUTPUT_DIR, release_dir, zip_path)
    log_phase(f"ZIP created: {zip_path}")
    return True


def create_portable():
    """Create portable version (no exe, just Python scripts)"""
    log_phase("Creating portable version...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    portable_dir = OUTPUT_DIR / "SManage-Portable"
    portable_dir.mkdir(exist_ok=True)

    manager_dest = portable_dir / "manager"
    manager_dest.mkdir(exist_ok=True)

    for filename in ["gui_v3.py", *MANAGER_FILES]:
        src = MANAGER_DIR / filename
        if src.exists():
            shutil.copy(src, manager_dest)

    for filename in ROOT_HELPERS:
        src = BASE_DIR / filename
        if src.exists():
            shutil.copy(src, portable_dir)

    if BROWSER_DIR.exists():
        copytree_with_progress(BROWSER_DIR, portable_dir / "browser", "Copy portable browser")

    launcher = """@echo off
cd /d "%~dp0manager"
python gui_v3.py
pause
"""
    (portable_dir / "Start SManage.bat").write_text(launcher, encoding="utf-8")

    reqs = """customtkinter>=5.0.0
pillow>=9.0.0
playwright>=1.52.0
"""
    (portable_dir / "requirements.txt").write_text(reqs, encoding="utf-8")

    install = """@echo off
echo Installing dependencies...
pip install -r requirements.txt
echo Done!
pause
"""
    (portable_dir / "Install Dependencies.bat").write_text(install, encoding="utf-8")

    log_phase(f"Portable version created: {portable_dir}")
    return True


def main():
    print("=" * 50)
    print("  S Manage - Build & Package Script")
    print("=" * 50)

    print(f"\nBase: {BASE_DIR}")
    print(f"Manager: {MANAGER_DIR}")
    print(f"Browser: {BROWSER_DIR}")

    print("\nOptions:")
    print("1. Build EXE (PyInstaller)")
    print("2. Create Portable (Python scripts)")
    print("3. Both")

    choice = input("\nSelect [1/2/3]: ").strip()

    if choice == "1":
        check_requirements()
        build_exe()
        package_release()
    elif choice == "2":
        create_portable()
    elif choice == "3":
        check_requirements()
        build_exe()
        package_release()
        create_portable()
    else:
        log_phase("Creating portable version...")
        create_portable()

    log_phase("Done")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
