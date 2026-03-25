#!/usr/bin/env python3
"""
S Manage - Apply Chromium Patches
Copy patched files to Chromium source directory
"""

import shutil
from pathlib import Path

CHROMIUM_SRC = Path(r"E:\chromium\src")
PATCHES_DIR = Path(r"F:\ChromiumSoncuto\patches\files")

PATCHES = [
    {
        "name": "Hardware Concurrency (CPU cores)",
        "source": PATCHES_DIR / "navigator_concurrent_hardware.cc",
        "target": CHROMIUM_SRC / "third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc",
    },
    {
        "name": "Device Memory (RAM)",
        "source": PATCHES_DIR / "navigator_device_memory.cc",
        "target": CHROMIUM_SRC / "third_party/blink/renderer/core/frame/navigator_device_memory.cc",
    },
    {
        "name": "WebGL Renderer Info",
        "source": PATCHES_DIR / "webgl_rendering_context_base.patch",
        "target": CHROMIUM_SRC / "third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc",
        "is_patch": True,  # Cần áp dụng patch thay vì copy
    },
]


def backup_file(filepath: Path):
    """Create backup of original file"""
    backup = filepath.with_suffix(filepath.suffix + '.original')
    if not backup.exists():
        shutil.copy(filepath, backup)
        print(f"  [Backup] {backup.name}")


def apply_patches():
    print("=" * 60)
    print("S Manage - Chromium Patcher")
    print("=" * 60)
    
    if not CHROMIUM_SRC.exists():
        print(f"[ERROR] Chromium source not found: {CHROMIUM_SRC}")
        return False
    
    print(f"[*] Chromium: {CHROMIUM_SRC}")
    print(f"[*] Patches: {PATCHES_DIR}")
    print()
    
    for patch in PATCHES:
        print(f"[*] {patch['name']}...")
        
        target = patch['target']
        source = patch['source']
        
        if not target.exists():
            print(f"  [ERROR] Target not found: {target}")
            continue
        
        if patch.get('is_patch'):
            print(f"  [MANUAL] Apply WebGL patch manually - see instructions below")
            continue
        
        if not source.exists():
            print(f"  [ERROR] Patch file not found: {source}")
            continue
        
        # Backup original
        backup_file(target)
        
        # Copy patched file
        shutil.copy(source, target)
        print(f"  [OK] Patched!")
    
    print()
    print("=" * 60)
    print("MANUAL PATCH REQUIRED for WebGL:")
    print("=" * 60)
    print("""
File: E:\\chromium\\src\\third_party\\blink\\renderer\\modules\\webgl\\webgl_rendering_context_base.cc

1. Add at top of file (after other #includes):
   #include <cstdlib>

2. Find this code (around line 4148):

    case WebGLDebugRendererInfo::kUnmaskedRendererWebgl:
      if (ExtensionEnabled(kWebGLDebugRendererInfoName)) {
        ...
        return WebGLAny(script_state,
                        String(ContextGL()->GetString(GL_RENDERER)));
      }

3. Replace with:

    case WebGLDebugRendererInfo::kUnmaskedRendererWebgl:
      if (ExtensionEnabled(kWebGLDebugRendererInfoName)) {
        // S Manage: Override WebGL renderer
        const char* override_renderer = std::getenv("SMANAGE_WEBGL_RENDERER");
        if (override_renderer) {
          return WebGLAny(script_state, String(override_renderer));
        }
        if (IdentifiabilityStudySettings::Get()->ShouldSampleType(
                blink::IdentifiableSurface::Type::kWebGLParameter)) {
          RecordIdentifiableGLParameterDigest(
              pname, IdentifiabilityBenignStringToken(
                         String(ContextGL()->GetString(GL_RENDERER))));
        }
        return WebGLAny(script_state,
                        String(ContextGL()->GetString(GL_RENDERER)));
      }

4. Similarly for kUnmaskedVendorWebgl (around line 4163):

    case WebGLDebugRendererInfo::kUnmaskedVendorWebgl:
      if (ExtensionEnabled(kWebGLDebugRendererInfoName)) {
        // S Manage: Override WebGL vendor
        const char* override_vendor = std::getenv("SMANAGE_WEBGL_VENDOR");
        if (override_vendor) {
          return WebGLAny(script_state, String(override_vendor));
        }
        if (IdentifiabilityStudySettings::Get()->ShouldSampleType(
                blink::IdentifiableSurface::Type::kWebGLParameter)) {
          RecordIdentifiableGLParameterDigest(
              pname, IdentifiabilityBenignStringToken(
                         String(ContextGL()->GetString(GL_VENDOR))));
        }
        return WebGLAny(script_state,
                        String(ContextGL()->GetString(GL_VENDOR)));
      }
""")
    
    print()
    print("=" * 60)
    print("After patching, rebuild with:")
    print("  cd E:\\chromium\\src")
    print("  autoninja -C out\\Release chrome")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    apply_patches()
