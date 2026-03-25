# 📖 Hướng Dẫn Chi Tiết - S Manage Antidetect Browser

**Tài liệu hướng dẫn build, chỉnh sửa và phát triển S Manage**

---

## 📑 Mục Lục

1. [Môi Trường Hiện Tại](#1-môi-trường-hiện-tại)
2. [Build Chromium](#2-build-chromium)
3. [Patch Fingerprint](#3-patch-fingerprint)
4. [Build GUI Manager](#4-build-gui-manager)
5. [Tạo Release Package](#5-tạo-release-package)
6. [Chỉnh Sửa Fingerprint](#6-chỉnh-sửa-fingerprint)
7. [Thêm Tính Năng Mới](#7-thêm-tính-năng-mới)
8. [Debug & Troubleshooting](#8-debug--troubleshooting)

---

## 1. Môi Trường Hiện Tại

### ✅ Đã cài đặt sẵn

| Component | Version | Path |
|-----------|---------|------|
| Windows | 11 64-bit | - |
| Visual Studio | 2022 | C:\Program Files\Microsoft Visual Studio\2022 |
| depot_tools | Latest | Trong PATH |
| Python | 3.12 | C:\Program Files\Python312 |
| Chromium Source | 146.0.7680.76 | E:\chromium\src |

### Python packages đã cài
```
customtkinter
websocket-client
pyinstaller
```

### Cấu trúc project hiện tại
```
F:\ChromiumSoncuto\
├── browser/           # Chromium đã build và patch
├── manager/           # GUI source code
│   ├── gui_v3.py
│   ├── browser_launcher.py
│   ├── fingerprint.py
│   └── profiles.py
├── dist/              # Release packages
│   ├── SManage-v3.0/
│   └── SManage-v3.0.zip
├── README.md
└── HUONGDAN.md
```

### Nếu cần cài môi trường mới (máy khác)

<details>
<summary>📦 Click để xem hướng dẫn cài đặt môi trường từ đầu</summary>

**Yêu cầu phần cứng:**
- **CPU**: 8+ cores (build nhanh hơn)
- **RAM**: 16GB+ (tối thiểu 8GB nhưng sẽ chậm)
- **Disk**: 100GB+ free space (SSD khuyến nghị)
- **OS**: Windows 10/11 64-bit

**Cài đặt Visual Studio 2022:**

1. Download từ https://visualstudio.microsoft.com/
2. Chọn workload: **"Desktop development with C++"**
3. Trong Individual components, chọn thêm:
   - Windows 10/11 SDK (latest)
   - C++ ATL for latest build tools
   - C++ MFC for latest build tools

**Cài đặt depot_tools:**

```powershell
cd C:\
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git
# Thêm C:\depot_tools vào PATH
```

**Cài đặt Python packages:**

```powershell
pip install customtkinter websocket-client pyinstaller
```

</details>

---

## 2. Build Chromium

> ⚠️ **Lưu ý:** Chromium source mặc định theo script tại `E:\chromium\src`
> Browser đã build sẵn tại `F:\ChromiumSoncuto\browser\`
> Chỉ cần rebuild nếu muốn thay đổi fingerprint hardcoded

### 2.1 Nếu cần fetch source code mới

```powershell
# Tạo thư mục
mkdir C:\chromium
cd C:\chromium

# Fetch (mất 1-2 giờ tùy internet)
fetch chromium

# Vào thư mục source
cd src
```

### 2.2 Checkout version cụ thể

```powershell
# Xem version hiện tại
git describe --tags

# Checkout version mong muốn
git checkout 146.0.7680.76

# Sync dependencies
gclient sync -D
```

### 2.3 Apply patches (xem mục 3)

### 2.4 Generate build files

```powershell
# Release build (khuyến nghị)
gn gen out/Release --args="is_debug=false is_component_build=false target_cpu=\"x64\" symbol_level=0"

# Debug build (để debug)
gn gen out/Debug --args="is_debug=true is_component_build=true target_cpu=\"x64\""
```

**Build args giải thích:**
- `is_debug=false` - Build release, không có debug symbols
- `is_component_build=false` - Build static, không DLL riêng
- `target_cpu="x64"` - Build 64-bit
- `symbol_level=0` - Không tạo debug symbols (build nhỏ hơn)

### 2.5 Build

```powershell
# Build chrome (mất 2-6 giờ lần đầu)
autoninja -C out/Release chrome

# Build với số jobs cụ thể (nếu máy yếu)
autoninja -C out/Release chrome -j 4
```

### 2.6 Copy output

```powershell
# Files cần copy từ out/Release/ vào browser/
- chrome.exe
- chrome.dll
- chrome_elf.dll
- icudtl.dat
- libEGL.dll
- libGLESv2.dll
- d3dcompiler_47.dll
- dxcompiler.dll
- dxil.dll
- vk_swiftshader.dll
- vulkan-1.dll
- eventlog_provider.dll
- chrome_wer.dll
- *.pak files
- *.bin files
- locales/ folder
- MEIPreload/ folder
- resources/ folder
```

---

## 3. Patch Fingerprint

### 3.1 CPU Cores (hardwareConcurrency)

**File:** `third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc`

**Tìm function:**
```cpp
unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {
```

**Thay đổi thành:**
```cpp
unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {
  // S Manage: Return fixed CPU cores
  // Thay đổi số 8 thành số cores mong muốn
  return 8u;
  
  // Code gốc (comment lại):
  // unsigned int hardware_concurrency = ...
}
```

### 3.2 RAM (deviceMemory)

**File:** `third_party/blink/renderer/core/frame/navigator_device_memory.cc`

**Tìm function:**
```cpp
float NavigatorDeviceMemory::deviceMemory() const {
```

**Thay đổi thành:**
```cpp
float NavigatorDeviceMemory::deviceMemory() const {
  // S Manage: Return fixed device memory (GB)
  // Thay đổi 8.0f thành số GB mong muốn (1, 2, 4, 8, 16, 32)
  return 8.0f;
  
  // Code gốc (comment lại):
  // return ApproximatedDeviceMemory::GetApproximatedDeviceMemory();
}
```

### 3.3 Rebuild sau khi patch

```powershell
# Chỉ rebuild các file thay đổi (nhanh hơn)
autoninja -C out/Release chrome
```

---

## 4. Build GUI Manager

### 4.1 Cấu trúc files

```
manager/
├── gui_v3.py              # Main GUI application
├── browser_launcher.py    # Browser launcher với CDP
├── fingerprint.py         # Fingerprint generator
├── profiles.py            # Profile management
└── dist/                  # Output folder
```

### 4.2 Test GUI

```powershell
cd F:\ChromiumSoncuto\manager
python gui_v3.py
```

### 4.3 Build EXE

```powershell
cd F:\ChromiumSoncuto\manager

# Build EXE (windowed mode - không console)
python -m PyInstaller --onefile --windowed --name SManage \
  --collect-all customtkinter \
  --hidden-import websocket \
  gui_v3.py

# Build EXE (với console - để debug)
python -m PyInstaller --onefile --console --name SManage_Debug \
  --collect-all customtkinter \
  --hidden-import websocket \
  gui_v3.py
```

**Output:** `dist/SManage.exe`

### 4.4 Giải thích PyInstaller options

| Option | Mô tả |
|--------|-------|
| `--onefile` | Đóng gói thành 1 file EXE |
| `--windowed` | Không hiện console window |
| `--console` | Hiện console (để debug) |
| `--name` | Tên file output |
| `--collect-all` | Thu thập tất cả files của package |
| `--hidden-import` | Import module ẩn |
| `--icon` | Icon cho EXE |

---

## 5. Tạo Release Package

### 5.1 Script tạo release

```powershell
# Kill processes
taskkill /F /IM chrome.exe 2>$null
taskkill /F /IM SManage.exe 2>$null

# Tạo thư mục release
$releaseDir = "F:\ChromiumSoncuto\dist\SManage-v3.0"
Remove-Item $releaseDir -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $releaseDir -Force

# Copy EXE
Copy-Item "F:\ChromiumSoncuto\manager\dist\SManage.exe" $releaseDir

# Copy Python modules (cần cho import)
Copy-Item "F:\ChromiumSoncuto\manager\browser_launcher.py" $releaseDir
Copy-Item "F:\ChromiumSoncuto\manager\fingerprint.py" $releaseDir
Copy-Item "F:\ChromiumSoncuto\manager\profiles.py" $releaseDir

# Copy browser (dùng xcopy để giữ permissions)
xcopy "F:\ChromiumSoncuto\browser" "$releaseDir\browser\" /E /I /H /Y /Q

# Tạo start script
@"
@echo off
start "" "%~dp0SManage.exe"
"@ | Out-File -FilePath "$releaseDir\Start SManage.bat" -Encoding ASCII

# Tạo ZIP
$zipPath = "F:\ChromiumSoncuto\dist\SManage-v3.0.zip"
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Compress-Archive -Path "$releaseDir\*" -DestinationPath $zipPath -CompressionLevel Optimal

Write-Host "Release created: $zipPath"
```

### 5.2 Cấu trúc release

```
SManage-v3.0/
├── SManage.exe              # ~16 MB
├── Start SManage.bat        # Launcher
├── browser_launcher.py      # Launcher module
├── fingerprint.py           # Fingerprint module
├── profiles.py              # Profile module
└── browser/                 # ~450 MB
    ├── chrome.exe
    ├── chrome.dll
    └── ...
```

### 5.3 Test release

```powershell
# Test chạy từ release folder
& "F:\ChromiumSoncuto\dist\SManage-v3.0\SManage.exe"
```

---

## 6. Chỉnh Sửa Fingerprint

### 6.1 Thay đổi CPU/RAM (cần rebuild Chromium)

1. Mở file patch (xem mục 3)
2. Thay đổi giá trị return
3. Rebuild: `autoninja -C out/Release chrome`
4. Copy chrome.exe và chrome.dll mới vào browser/
5. Rebuild GUI và tạo release mới

### 6.2 Thêm GPU preset mới

**File:** `manager/gui_v3.py`

**Tìm:** `GPU_PRESETS = {`

**Thêm:**
```python
GPU_PRESETS = {
    "NVIDIA": {
        # Thêm GPU mới vào đây
        "RTX 5090": "ANGLE (NVIDIA, NVIDIA GeForce RTX 5090 Direct3D11 vs_5_0 ps_5_0, D3D11)",
        # ...
    },
    # ...
}
```

### 6.3 Thêm Timezone mới

**File:** `manager/gui_v3.py`

**Tìm:** `TIMEZONE_PRESETS = {`

**Thêm:**
```python
TIMEZONE_PRESETS = {
    # Thêm timezone mới
    "India (UTC+5:30)": {"name": "Asia/Kolkata", "offset": -330},
    # offset = -(hours * 60) - minutes
    # UTC+5:30 = -(5*60 + 30) = -330
}
```

### 6.4 Thay đổi User-Agent mặc định

**File:** `manager/fingerprint.py`

**Tìm:** `USER_AGENTS = [`

**Thêm/sửa User-Agent mong muốn.**

---

## 7. Thêm Tính Năng Mới

### 7.1 Thêm fingerprint mới qua CDP

**File:** `manager/browser_launcher.py`

**Tìm function:** `_build_injection_script`

**Thêm JavaScript injection:**
```python
def _build_injection_script(self, fingerprint: Dict) -> str:
    script = """
    (function() {
        // Thêm code spoof mới ở đây
        Object.defineProperty(navigator, 'newProperty', {
            get: function() { return 'spoofed_value'; }
        });
    })();
    """
    return script
```

### 7.2 Thêm Chrome flag mới

**File:** `manager/browser_launcher.py`

**Tìm:** `args = [`

**Thêm:**
```python
args = [
    # ... existing args
    "--new-flag-here",
]
```

### 7.3 Thêm UI element mới

**File:** `manager/gui_v3.py`

**Tìm class:** `ProfileManagerApp`

**Thêm widget trong `_create_widgets` hoặc `_show_config_dialog`**

---

## 8. Debug & Troubleshooting

### 8.1 Browser không mở

**Nguyên nhân:** Sandbox permission error

**Giải pháp:** Đảm bảo `--no-sandbox` trong browser_launcher.py

```python
args = [
    str(self.browser_path),
    "--no-sandbox",  # QUAN TRỌNG
    # ...
]
```

### 8.2 EXE không tìm thấy browser

**Nguyên nhân:** Path detection sai

**Debug:**
```python
# Thêm vào gui_v3.py
print(f"[DEBUG] APP_PATH = {APP_PATH}")
print(f"[DEBUG] Browser exists: {os.path.exists(browser_path)}")
```

**Build với console:**
```powershell
python -m PyInstaller --onefile --console --name SManage_Debug ...
```

### 8.3 CDP injection không hoạt động

**Nguyên nhân:** Browser chưa sẵn sàng

**Giải pháp:** Tăng delay trong `_inject_fingerprint`:
```python
def _inject_fingerprint(self, fingerprint: Dict):
    time.sleep(3)  # Tăng từ 2 lên 3 giây
    # ...
```

### 8.4 Chromium build lỗi

**Lỗi thường gặp:**

1. **"gn: command not found"**
   - Đảm bảo depot_tools trong PATH

2. **"Visual Studio not found"**
   - Cài VS 2022 với C++ workload
   - Chạy: `set DEPOT_TOOLS_WIN_TOOLCHAIN=0`

3. **"Out of memory"**
   - Giảm jobs: `autoninja -C out/Release chrome -j 2`
   - Đóng các ứng dụng khác

4. **"File not found" khi build**
   - Chạy: `gclient sync -D`

### 8.5 Logs và Debug

**Chrome debug log:**
```
browser/debug.log
```

**Bật verbose logging:**
```python
args = [
    # ...
    "--enable-logging",
    "--v=1",
]
```

---

## 📝 Checklist Release Mới

```
[ ] Patch Chromium source (nếu cần)
[ ] Build Chromium: autoninja -C out/Release chrome
[ ] Copy browser files vào browser/
[ ] Test browser trực tiếp
[ ] Cập nhật gui_v3.py (nếu cần)
[ ] Cập nhật browser_launcher.py (nếu cần)
[ ] Test GUI: python gui_v3.py
[ ] Build EXE: PyInstaller ...
[ ] Tạo release folder
[ ] Copy tất cả files
[ ] Test release folder
[ ] Tạo ZIP
[ ] Test extract và chạy từ thư mục mới
[ ] Cập nhật README.md
[ ] Cập nhật version number
```

---

## 🔗 Tài Liệu Tham Khảo

- Chromium Source: https://chromium.googlesource.com/chromium/src
- Chromium Build: https://chromium.googlesource.com/chromium/src/+/main/docs/windows_build_instructions.md
- depot_tools: https://commondatastorage.googleapis.com/chrome-infra-docs/flat/depot_tools/docs/html/depot_tools_tutorial.html
- CustomTkinter: https://github.com/TomSchimansky/CustomTkinter
- Chrome DevTools Protocol: https://chromedevtools.github.io/devtools-protocol/
- PyInstaller: https://pyinstaller.org/en/stable/

---

## 📞 Quick Reference

### Commands hay dùng

```powershell
# Build Chromium
autoninja -C out/Release chrome

# Build GUI EXE
python -m PyInstaller --onefile --windowed --name SManage --collect-all customtkinter --hidden-import websocket gui_v3.py

# Test GUI
python gui_v3.py

# Kill processes
taskkill /F /IM chrome.exe
taskkill /F /IM SManage.exe

# Copy browser
xcopy "browser" "dist\SManage-v3.0\browser\" /E /I /H /Y /Q

# Create ZIP
Compress-Archive -Path "dist\SManage-v3.0\*" -DestinationPath "dist\SManage-v3.0.zip"
```

### Files quan trọng

| File | Mô tả |
|------|-------|
| `navigator_concurrent_hardware.cc` | CPU cores |
| `navigator_device_memory.cc` | RAM |
| `gui_v3.py` | Main GUI |
| `browser_launcher.py` | Browser launcher |
| `fingerprint.py` | Fingerprint generator |
| `profiles.py` | Profile manager |

---

**Cập nhật lần cuối: January 2026**
**Version: 3.0**
