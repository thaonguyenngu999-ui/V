# Per-Profile CPU/RAM Configuration

## Giải thích vấn đề

Hiện tại CPU và RAM đã được **hardcode** trong Chromium source:
- `navigator_concurrent_hardware.cc`: return 8u (8 cores)
- `navigator_device_memory.cc`: return 8.0f (8GB)

Để mỗi profile có CPU/RAM khác nhau, cần sửa code để đọc từ một nguồn external.

## Giải pháp 1: Shared Memory (Đề xuất)

### Ý tưởng
Browser process đọc config từ profile, ghi vào shared memory.
Renderer process đọc từ shared memory (không bị chặn bởi sandbox).

### Các file cần sửa

#### 1. Tạo shared memory helper: `chromium/src/components/smanage/fingerprint_config.h`

```cpp
#ifndef COMPONENTS_SMANAGE_FINGERPRINT_CONFIG_H_
#define COMPONENTS_SMANAGE_FINGERPRINT_CONFIG_H_

#include <windows.h>
#include <cstdint>

namespace smanage {

struct FingerprintConfig {
    uint32_t cpu_cores;
    float device_memory;
    char webgl_vendor[256];
    char webgl_renderer[512];
};

inline bool ReadConfig(FingerprintConfig* config) {
    HANDLE hMapFile = OpenFileMappingA(
        FILE_MAP_READ,
        FALSE,
        "SManageFingerprintConfig"
    );
    
    if (hMapFile == NULL) {
        // Default values
        config->cpu_cores = 8;
        config->device_memory = 8.0f;
        return false;
    }
    
    FingerprintConfig* pConfig = (FingerprintConfig*)MapViewOfFile(
        hMapFile,
        FILE_MAP_READ,
        0, 0,
        sizeof(FingerprintConfig)
    );
    
    if (pConfig != NULL) {
        *config = *pConfig;
        UnmapViewOfFile(pConfig);
    }
    
    CloseHandle(hMapFile);
    return true;
}

}  // namespace smanage

#endif
```

#### 2. Sửa `navigator_concurrent_hardware.cc`

```cpp
#include "components/smanage/fingerprint_config.h"

unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {
    smanage::FingerprintConfig config;
    smanage::ReadConfig(&config);
    return config.cpu_cores > 0 ? config.cpu_cores : 8u;
}
```

#### 3. Sửa `navigator_device_memory.cc`

```cpp
#include "components/smanage/fingerprint_config.h"

float NavigatorDeviceMemory::deviceMemory() const {
    smanage::FingerprintConfig config;
    smanage::ReadConfig(&config);
    return config.device_memory > 0 ? config.device_memory : 8.0f;
}
```

#### 4. Sửa browser_launcher.py để tạo shared memory

```python
import ctypes
from ctypes import wintypes
import mmap
import struct

def create_fingerprint_shared_memory(cpu_cores: int, device_memory: float):
    """Create Windows shared memory with fingerprint config"""
    
    # Shared memory name (must match C++ code)
    name = "SManageFingerprintConfig"
    
    # Create shared memory
    size = 4 + 4 + 256 + 512  # cpu(4) + mem(4) + vendor(256) + renderer(512)
    
    # Pack data
    data = struct.pack('If256s512s',
        cpu_cores,
        device_memory,
        b'Google Inc.',
        b'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)'
    )
    
    # Create named shared memory
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    
    FILE_MAP_WRITE = 0x0002
    PAGE_READWRITE = 0x04
    
    hMapFile = kernel32.CreateFileMappingW(
        wintypes.HANDLE(-1),  # INVALID_HANDLE_VALUE
        None,                  # Default security
        PAGE_READWRITE,
        0, size,
        name
    )
    
    if hMapFile:
        pBuf = kernel32.MapViewOfFile(hMapFile, FILE_MAP_WRITE, 0, 0, size)
        if pBuf:
            ctypes.memmove(pBuf, data, len(data))
            # Don't unmap - keep alive while browser runs
            return hMapFile
    
    return None
```

### Rebuild Chromium

```batch
cd E:\chromium\src
gn gen out/Release
autoninja -C out/Release chrome
```

## Giải pháp 2: Command Line Switch + IPC (Phức tạp hơn)

Cần sửa nhiều file hơn để truyền giá trị từ browser process sang renderer qua Mojo IPC.

## Giải pháp 3: File-based (Đơn giản nhất nhưng có thể phát hiện)

Lưu config vào temp file, renderer đọc file. Nhưng sandbox có thể chặn.

---

## Lưu ý

Với cách hiện tại (hardcode 8 cores, 8GB):
- ✅ Pass Iphey
- ✅ Pass Pixelscan  
- ✅ Không bị phát hiện

Nếu muốn per-profile khác nhau, cần rebuild Chromium với giải pháp Shared Memory.

## Giá trị phổ biến nên dùng

| Loại máy | CPU Cores | RAM |
|----------|-----------|-----|
| Laptop phổ thông | 4 | 8 |
| Laptop gaming | 6-8 | 16 |
| Desktop phổ thông | 4-6 | 8-16 |
| Desktop gaming | 8-16 | 16-32 |
| Mac M1 | 8 | 8-16 |

Nên random trong khoảng **4-8 cores** và **8-16 GB** để trông tự nhiên.
