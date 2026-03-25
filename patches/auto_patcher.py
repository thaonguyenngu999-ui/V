#!/usr/bin/env python3
"""
S Manage - Auto Patcher for Chromium Source
Apply fingerprint spoofing patches automatically
"""

import os
import re
import shutil
from pathlib import Path

CHROMIUM_SRC = Path(r"E:\chromium\src")

PATCHES = {
    # ============================================
    # PATCH 1: Hardware Concurrency (CPU cores)
    # ============================================
    "navigator_concurrent_hardware.cc": {
        "path": CHROMIUM_SRC / "third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc",
        "search": r"unsigned NavigatorConcurrentHardware::hardwareConcurrency\(\) const \{",
        "replace": '''unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {
  // S Manage: Override hardware concurrency
  const char* override_val = std::getenv("SMANAGE_HARDWARE_CONCURRENCY");
  if (override_val) {
    return static_cast<unsigned>(std::atoi(override_val));
  }
''',
        "add_include": '#include <cstdlib>'
    },
    
    # ============================================
    # PATCH 2: Device Memory (RAM)
    # ============================================
    "navigator_device_memory.cc": {
        "path": CHROMIUM_SRC / "third_party/blink/renderer/core/frame/navigator_device_memory.cc",
        "search": r"float NavigatorDeviceMemory::deviceMemory\(\) const \{",
        "replace": '''float NavigatorDeviceMemory::deviceMemory() const {
  // S Manage: Override device memory
  const char* override_val = std::getenv("SMANAGE_DEVICE_MEMORY");
  if (override_val) {
    return static_cast<float>(std::atof(override_val));
  }
''',
        "add_include": '#include <cstdlib>'
    },
}

# WebGL patch is more complex - needs manual or separate handling
WEBGL_PATCH = '''
// ============================================
// MANUAL PATCH for WebGL
// File: third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc
// ============================================

Find the getParameter function and add this logic:

case GL_VENDOR:
case WebGLDebugRendererInfo::UNMASKED_VENDOR_WEBGL: {
  const char* override_val = std::getenv("SMANAGE_WEBGL_VENDOR");
  if (override_val) {
    return WebGLAny(script_state, String::FromUTF8(override_val));
  }
  // ... keep original code
}

case GL_RENDERER:  
case WebGLDebugRendererInfo::UNMASKED_RENDERER_WEBGL: {
  const char* override_val = std::getenv("SMANAGE_WEBGL_RENDERER");
  if (override_val) {
    return WebGLAny(script_state, String::FromUTF8(override_val));
  }
  // ... keep original code
}
'''


def backup_file(filepath: Path) -> Path:
    """Create backup of original file"""
    backup = filepath.with_suffix(filepath.suffix + '.backup')
    if not backup.exists():
        shutil.copy(filepath, backup)
        print(f"  Backed up: {backup.name}")
    return backup


def apply_patch(name: str, patch_info: dict) -> bool:
    """Apply a single patch"""
    filepath = patch_info['path']
    
    if not filepath.exists():
        print(f"[!] File not found: {filepath}")
        return False
    
    print(f"\n[*] Patching {name}...")
    
    # Backup
    backup_file(filepath)
    
    # Read content
    content = filepath.read_text(encoding='utf-8')
    
    # Check if already patched
    if 'SMANAGE_' in content:
        print(f"  Already patched, skipping")
        return True
    
    # Add include if needed
    if 'add_include' in patch_info:
        include = patch_info['add_include']
        if include not in content:
            # Add after first #include
            content = re.sub(
                r'(#include [^\n]+\n)',
                rf'\1{include}\n',
                content,
                count=1
            )
            print(f"  Added include: {include}")
    
    # Apply patch
    search = patch_info['search']
    replace = patch_info['replace']
    
    if re.search(search, content):
        content = re.sub(search, replace, content, count=1)
        filepath.write_text(content, encoding='utf-8')
        print(f"  ✓ Patched successfully")
        return True
    else:
        print(f"  [!] Pattern not found, may need manual patching")
        return False


def main():
    print("=" * 50)
    print("S Manage - Chromium Auto Patcher")
    print("=" * 50)
    
    if not CHROMIUM_SRC.exists():
        print(f"[!] Chromium source not found at: {CHROMIUM_SRC}")
        print("    Please update CHROMIUM_SRC path")
        return
    
    print(f"[*] Chromium source: {CHROMIUM_SRC}")
    
    # Apply auto patches
    success = 0
    failed = 0
    
    for name, patch_info in PATCHES.items():
        if apply_patch(name, patch_info):
            success += 1
        else:
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {success} patched, {failed} failed")
    print("=" * 50)
    
    # Print manual patches needed
    print("\n[!] MANUAL PATCHES REQUIRED:")
    print(WEBGL_PATCH)
    
    print("\n[*] After patching, rebuild with:")
    print("    cd E:\\chromium\\src")
    print("    autoninja -C out\\Release chrome")


if __name__ == "__main__":
    main()
