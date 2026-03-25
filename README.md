# 🛡️ S Manage - Antidetect Browser

**Custom Chromium-based antidetect browser with native fingerprint spoofing**

Version: 3.2 | Chromium: 146.0.7680.76 | Build Date: March 2026

---

## 📋 Tổng Quan

S Manage là trình duyệt antidetect được build từ source Chromium với các patch native để spoof fingerprint. Khác với các giải pháp dựa trên extension hoặc JavaScript injection, S Manage thay đổi fingerprint ở tầng C++ core của Chromium, giúp bypass các hệ thống detect tiên tiến.

### ✅ Đã Test Pass
- **Iphey.com** - 100% Pass
- **Pixelscan.net** - 100% Pass
- **BrowserLeaks** - Hardware info spoofed
- **CreepJS** - Consistent fingerprint

---

## 🎯 Tính Năng

### Hardware Spoofing (Native - Hardcoded trong Chromium)

| Fingerprint | Giá trị | Vị trí patch |
|-------------|---------|--------------|
| CPU Cores | 8 | `navigator_concurrent_hardware.cc` |
| RAM | 8 GB | `navigator_device_memory.cc` |
| Platform | Win32 | Native |

### WebGL GPU Spoofing (ANGLE Environment Variables)

Hỗ trợ các preset GPU:

**NVIDIA:**
- GTX 1050 Ti, GTX 1650, GTX 1660 Ti
- RTX 2060, RTX 3060, RTX 3070, RTX 3080
- RTX 4060, RTX 4070, RTX 4080

**AMD:**
- RX 580, RX 5600 XT, RX 6600 XT
- RX 6700 XT, RX 6800 XT, RX 7900 XTX
- Radeon Graphics (APU)

**Intel:**
- HD Graphics 530, UHD Graphics 620/630/770
- Iris Xe Graphics

### Các tính năng khác
- ✅ Per-profile fingerprint config
- ✅ Timezone spoofing với presets
- ✅ Proxy support (HTTP/SOCKS5)
- ✅ User-Agent spoofing
- ✅ Screen resolution spoofing
- ✅ Language/Locale spoofing
- ✅ WebRTC IP leak protection
- ✅ CDP injection cho dynamic fingerprint

---

## 📦 Cấu Trúc Release

```
SManage-v3.0/
├── SManage.exe          # GUI Application (16 MB)
├── Start SManage.bat    # Launcher script
├── browser_launcher.py  # Browser launcher module
├── fingerprint.py       # Fingerprint generator
├── profiles.py          # Profile manager
└── browser/             # Chromium browser (~450 MB)
    ├── chrome.exe
    ├── chrome.dll
    └── ...
```

---

## 🚀 Hướng Dẫn Sử Dụng

### Cài đặt

1. **Giải nén** `SManage-v3.0.zip` vào thư mục bất kỳ
2. **Chạy** `SManage.exe` hoặc double-click `Start SManage.bat`

### Sử dụng

1. **Chọn thư mục profiles** khi khởi động lần đầu
2. **Tạo profile mới**: Click nút "➕ New Profile"
3. **Cấu hình fingerprint**:
   - Chọn GPU preset (NVIDIA/AMD/Intel)
   - Chọn Timezone
   - Nhập Proxy (nếu cần)
4. **Start profile**: Click "▶ Start"
5. **Stop profile**: Click "⬛ Stop"

### Yêu cầu hệ thống

- Windows 10/11 (64-bit)
- RAM: 4GB+ (khuyến nghị 8GB)
- Disk: 500MB+ free space
- Không cần cài Python hoặc dependencies

---

## 🔧 Chi Tiết Kỹ Thuật

### Chromium Patches

#### 1. CPU Cores Spoofing
**File:** `third_party/blink/renderer/core/frame/navigator_concurrent_hardware.cc`

```cpp
unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {
  // S Manage: Hardcoded CPU cores
  return 8u;
}
```

#### 2. RAM Spoofing
**File:** `third_party/blink/renderer/core/frame/navigator_device_memory.cc`

```cpp
float NavigatorDeviceMemory::deviceMemory() const {
  // S Manage: Hardcoded device memory
  return 8.0f;
}
```

#### 3. WebGL GPU Spoofing
Sử dụng ANGLE environment variables:
- `ANGLE_GL_VENDOR` - GPU vendor (Google Inc. (NVIDIA/AMD/Intel))
- `ANGLE_GL_RENDERER` - Full GPU string

### Browser Launch Arguments

```
--no-sandbox                    # Required for copied browser
--remote-debugging-port=XXXXX   # CDP connection
--remote-allow-origins=*        # Allow CDP
--force-webrtc-ip-handling-policy=disable_non_proxied_udp
--webrtc-ip-handling-policy=disable_non_proxied_udp
--disable-features=WebRtcHideLocalIpsWithMdns
--no-first-run
--no-default-browser-check
--disable-sync
--disable-translate
```

### CDP Fingerprint Injection

Sử dụng Chrome DevTools Protocol để inject JavaScript fingerprint overrides:
- Canvas fingerprint noise
- AudioContext fingerprint
- WebGL parameters
- Timezone override
- Navigator properties

---

## 📁 Profile Data Structure

```
profiles_folder/
├── profiles.json           # Profile list
└── profile_XXXXXXXX/       # Per-profile folder
    ├── config.json         # Fingerprint config
    └── UserData/           # Chrome user data
        ├── Default/
        ├── Cookies
        └── ...
```

### Profile Config (config.json)

```json
{
  "id": "a1b2c3d4",
  "name": "Profile 1",
  "user_agent": "Mozilla/5.0...",
  "platform": "Win32",
  "hardware_concurrency": 8,
  "device_memory": 8,
  "screen_width": 1920,
  "screen_height": 1080,
  "webgl_vendor": "Google Inc. (NVIDIA)",
  "webgl_renderer": "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060...)",
  "timezone": "Asia/Ho_Chi_Minh",
  "language": "en-US,en",
  "proxy": "socks5://user:pass@host:port",
  "created_at": "2026-01-22T20:00:00",
  "last_used": "2026-01-22T22:00:00"
}
```

---

## 🛠️ Build từ Source

### Yêu cầu
- Windows 10/11
- Visual Studio 2022 với C++ workload
- 100GB+ disk space
- 16GB+ RAM

### Các bước build Chromium

```bash
# 1. Clone depot_tools
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git

# 2. Add to PATH
set PATH=%PATH%;C:\path\to\depot_tools

# 3. Fetch Chromium source
mkdir chromium && cd chromium
fetch chromium

# 4. Checkout version
cd src
git checkout 146.0.7680.76
gclient sync

# 5. Apply patches (xem mục Chromium Patches ở trên)

# 6. Generate build files
gn gen out/Release --args="is_debug=false is_component_build=false target_cpu=\"x64\""

# 7. Build (takes 2-6 hours)
autoninja -C out/Release chrome

# 8. Copy output từ out/Release/ vào browser/
```

### Build GUI (Python)

```bash
cd manager
pip install customtkinter websocket-client pyinstaller

# Build EXE
python -m PyInstaller --onefile --windowed --name SManage \
  --collect-all customtkinter --hidden-import websocket gui_v3.py
```

---

## 📂 Cấu Trúc Source Code

```
ChromiumSoncuto/
├── README.md                    # This file
├── browser/                     # Built Chromium browser
│   ├── chrome.exe
│   ├── chrome.dll
│   └── ...
├── manager/                     # GUI Manager source
│   ├── gui_v3.py               # Main GUI application
│   ├── browser_launcher.py     # Browser launcher with CDP
│   ├── fingerprint.py          # Fingerprint generator
│   ├── profiles.py             # Profile management
│   └── dist/                   # Built EXE
└── dist/                       # Release packages
    ├── SManage-v3.0/           # Release folder
    └── SManage-v3.0.zip        # Release ZIP (~260 MB)
```

---

## ⚠️ Lưu Ý Quan Trọng

### Security
- `--no-sandbox` được sử dụng để browser hoạt động khi copy folder
- Chỉ sử dụng cho mục đích automation/testing
- Không sử dụng để truy cập các trang nhạy cảm (banking, etc.)

### Fingerprint Limitations
- CPU và RAM được hardcode là 8 cores / 8GB cho tất cả profiles
- Để thay đổi giá trị này, cần rebuild Chromium từ source
- WebGL GPU có thể thay đổi per-profile qua ANGLE env vars

### Compatibility
- ✅ Windows 10/11 64-bit
- ❌ Windows 7/8 (không hỗ trợ)
- ❌ macOS/Linux (cần build riêng)

### Known Issues
- CustomTkinter có thể hiện warning "invalid command name" - không ảnh hưởng chức năng
- CDP injection cần 2-3 giây để activate sau khi browser khởi động

---

## 📝 Changelog

### v3.0 (January 2026)
- ✅ Chromium 146.0.7680.76
- ✅ Native CPU/RAM spoofing (hardcoded in C++)
- ✅ WebGL GPU spoofing với 20+ presets
- ✅ GUI v3 với CustomTkinter - giao diện mới
- ✅ Per-profile fingerprint config
- ✅ Timezone presets (9 zones)
- ✅ Proxy support (HTTP/SOCKS5)
- ✅ EXE packaging với PyInstaller (~16 MB)
- ✅ Pass Iphey + Pixelscan 100%

### v2.0
- CDP fingerprint injection
- Profile management
- Basic GUI

### v1.0
- Initial release
- Basic browser launch

---

## 🔍 Troubleshooting

### Browser không mở
1. Kiểm tra folder `browser/` có đầy đủ files không
2. Thử chạy `browser/chrome.exe` trực tiếp
3. Đảm bảo giải nén đầy đủ, không chạy từ trong ZIP

### Profile không lưu cookies
1. Đảm bảo đóng browser trước khi đóng SManage
2. Kiểm tra thư mục profiles có quyền write

### Fingerprint không đổi
1. Đảm bảo đã click Save sau khi edit
2. Restart profile (Stop → Start)

---

## 📄 License

Private project - All rights reserved

---

## 🤝 Credits

- Chromium Project - https://chromium.org
- CustomTkinter - https://github.com/TomSchimansky/CustomTkinter
- ANGLE Project - WebGL implementation
- PyInstaller - EXE packaging

---

**Made with ❤️ for the antidetect community**

**S Manage v3.0 - January 2026**
