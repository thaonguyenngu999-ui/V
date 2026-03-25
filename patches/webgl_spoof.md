# S Manage - WebGL Spoofing Patch
# Apply this patch to Chromium source before building

## File to modify: gpu/config/gpu_info.cc

Find and modify the function that returns GPU info.
Add environment variable check to override values.

```cpp
// Add at top of file
#include <cstdlib>

// In the function that gets GPU info, add:
const char* fake_vendor = std::getenv("SMANAGE_GPU_VENDOR");
const char* fake_renderer = std::getenv("SMANAGE_GPU_RENDERER");

if (fake_vendor && fake_renderer) {
    gpu_info.gl_vendor = fake_vendor;
    gpu_info.gl_renderer = fake_renderer;
}
```

## Alternative: Modify WebGL directly

File: third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc

In function `WebGLRenderingContextBase::getParameter`:

```cpp
case GL_RENDERER:
case WebGLDebugRendererInfo::UNMASKED_RENDERER_WEBGL: {
    const char* override = std::getenv("SMANAGE_GPU_RENDERER");
    if (override) {
        return WebGLAny(script_state, String(override));
    }
    // ... original code
}

case GL_VENDOR:
case WebGLDebugRendererInfo::UNMASKED_VENDOR_WEBGL: {
    const char* override = std::getenv("SMANAGE_GPU_VENDOR");
    if (override) {
        return WebGLAny(script_state, String(override));
    }
    // ... original code
}
```

## Build commands after patching:

```bash
cd E:\chromium\src
gn gen out/Release --args="is_debug=false is_component_build=false"
autoninja -C out/Release chrome
```

Build time: ~4-5 hours
