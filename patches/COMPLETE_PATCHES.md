# S Manage - Complete Fingerprint Patches for Chromium
# Apply ALL patches before rebuilding

## ============================================
## PATCH 1: WebGL GPU Spoofing
## File: gpu/config/gpu_info.cc
## ============================================

Add at top:
```cpp
#include <cstdlib>
```

Find `GPUInfo` struct initialization and add override:
```cpp
// After getting real GPU info, check for override
const char* override_vendor = std::getenv("SMANAGE_WEBGL_VENDOR");
const char* override_renderer = std::getenv("SMANAGE_WEBGL_RENDERER");

if (override_vendor) {
    gpu_info.gl_vendor = override_vendor;
}
if (override_renderer) {
    gpu_info.gl_renderer = override_renderer;
}
```

## ============================================
## PATCH 2: Hardware Concurrency (CPU cores)
## File: third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc
## ============================================

Find function `hardwareConcurrency()`:
```cpp
unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {
  // Add override check
  const char* override = std::getenv("SMANAGE_HARDWARE_CONCURRENCY");
  if (override) {
    return static_cast<unsigned>(std::atoi(override));
  }
  
  // Original code below...
  return std::max(1u, base::SysInfo::NumberOfProcessors());
}
```

## ============================================
## PATCH 3: Device Memory (RAM)
## File: third_party/blink/renderer/core/frame/navigator_device_memory.cc
## ============================================

Find function `deviceMemory()`:
```cpp
float NavigatorDeviceMemory::deviceMemory() const {
  // Add override check
  const char* override = std::getenv("SMANAGE_DEVICE_MEMORY");
  if (override) {
    return static_cast<float>(std::atof(override));
  }
  
  // Original code below...
  return ApproximatedDeviceMemory::GetApproximatedDeviceMemory();
}
```

## ============================================
## PATCH 4: Platform/UserAgentData
## File: third_party/blink/renderer/core/frame/navigator_ua_data.cc
## ============================================

Find `NavigatorUAData::platform()`:
```cpp
String NavigatorUAData::platform() const {
  const char* override = std::getenv("SMANAGE_PLATFORM");
  if (override) {
    return String(override);
  }
  // Original code...
}
```

Find `NavigatorUAData::platformVersion()`:
```cpp
String NavigatorUAData::platformVersion() const {
  const char* override = std::getenv("SMANAGE_PLATFORM_VERSION");
  if (override) {
    return String(override);
  }
  // Original code...
}
```

## ============================================
## PATCH 5: Screen Resolution (backup for CDP fail)
## File: third_party/blink/renderer/core/frame/screen.cc
## ============================================

```cpp
int Screen::width() const {
  const char* override = std::getenv("SMANAGE_SCREEN_WIDTH");
  if (override) {
    return std::atoi(override);
  }
  // Original code...
}

int Screen::height() const {
  const char* override = std::getenv("SMANAGE_SCREEN_HEIGHT");
  if (override) {
    return std::atoi(override);
  }
  // Original code...
}
```

## ============================================
## PATCH 6: Fonts (Optional - complex)
## ============================================
Skip for now - fonts are hard to spoof and less critical

## ============================================
## BUILD INSTRUCTIONS
## ============================================

1. Apply all patches above to E:\chromium\src

2. Rebuild:
```bash
cd E:\chromium\src
autoninja -C out\Release chrome
```

3. After build, copy to F:\ChromiumSoncuto\browser

4. Launch with environment variables:
```bash
set SMANAGE_WEBGL_VENDOR=Google Inc. (NVIDIA)
set SMANAGE_WEBGL_RENDERER=ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)
set SMANAGE_HARDWARE_CONCURRENCY=8
set SMANAGE_DEVICE_MEMORY=8
set SMANAGE_SCREEN_WIDTH=1920
set SMANAGE_SCREEN_HEIGHT=1080
chrome.exe
```

## ============================================
## ALTERNATIVE: Single config file approach
## ============================================

Instead of env vars, read from config file:
- Create F:\ChromiumSoncuto\profiles\profile_xxx\fingerprint.json
- Browser reads this file on startup
- More complex but cleaner
