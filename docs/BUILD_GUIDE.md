# Hướng dẫn Build ChromiumSoncuto

## Yêu cầu hệ thống

### Windows
- Windows 10/11 64-bit
- Visual Studio 2022 với "Desktop development with C++" workload
- Windows 10 SDK (10.0.22621.0 trở lên)
- 100GB dung lượng đĩa trống
- 16GB RAM (khuyến nghị 32GB)
- Git
- Python 3.8+

### macOS
- macOS 12 (Monterey) trở lên
- Xcode 14+
- Command Line Tools
- 100GB dung lượng đĩa trống
- 16GB RAM

### Linux (Ubuntu 20.04+)
- Các package build essentials
- 100GB dung lượng đĩa trống
- 16GB RAM

## Bước 1: Cài đặt depot_tools

```bash
# Clone depot_tools
git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git

# Thêm vào PATH (Windows PowerShell)
$env:PATH = "C:\path\to\depot_tools;$env:PATH"

# Thêm vào PATH (Linux/macOS)
export PATH="/path/to/depot_tools:$PATH"
```

## Bước 2: Clone Chromium source

```bash
# Tạo thư mục làm việc
mkdir chromium && cd chromium

# Fetch Chromium (mất vài giờ)
fetch --nohooks chromium

# Checkout version cụ thể
cd src
git checkout 146.0.7680.76

# Sync dependencies
gclient sync --with_branch_heads --with_tags
```

## Bước 3: Clone ChromiumSoncuto

```bash
# Clone ChromiumSoncuto vào thư mục riêng
cd ..
git clone https://github.com/user/ChromiumSoncuto.git
```

## Bước 4: Apply patches

```bash
# Chạy script apply patches
cd ChromiumSoncuto
python build/apply_patches.py --chromium-src=/path/to/chromium/src

# Kiểm tra patches đã apply
python build/apply_patches.py --chromium-src=/path/to/chromium/src --dry-run
```

## Bước 5: Copy source files

```bash
# Copy fingerprint controller vào Chromium
cp -r src/fingerprint_controller /path/to/chromium/src/chromiumsoncuto/

# Hoặc trên Windows
xcopy /E /I src\fingerprint_controller C:\path\to\chromium\src\chromiumsoncuto\fingerprint_controller
```

## Bước 6: Cập nhật BUILD.gn

Thêm vào `/path/to/chromium/src/BUILD.gn`:

```gn
source_set("chromiumsoncuto") {
  sources = [
    "chromiumsoncuto/fingerprint_controller/fingerprint_config.cc",
    "chromiumsoncuto/fingerprint_controller/fingerprint_config.h",
    "chromiumsoncuto/fingerprint_controller/canvas_spoof.h",
    "chromiumsoncuto/fingerprint_controller/webgl_spoof.h",
    "chromiumsoncuto/fingerprint_controller/audio_spoof.h",
    "chromiumsoncuto/fingerprint_controller/navigator_spoof.h",
    "chromiumsoncuto/fingerprint_controller/media_devices_spoof.h",
    "chromiumsoncuto/fingerprint_controller/font_spoof.h",
    "chromiumsoncuto/fingerprint_controller/anti_detection.h",
  ]
  
  deps = [
    "//base",
    "//third_party/rapidjson",
  ]
}
```

## Bước 7: Build

```bash
# Chạy script build
python ChromiumSoncuto/build/build.py --chromium-src=/path/to/chromium/src --target=Release

# Hoặc build thủ công
cd /path/to/chromium/src
gn gen out/Release
ninja -C out/Release chrome
```

## Bước 8: Chạy

```bash
# Windows
out\Release\chrome.exe --chromiumsoncuto-profile=path/to/profile.json

# Linux/macOS
./out/Release/chrome --chromiumsoncuto-profile=path/to/profile.json
```

## Tạo Profile

```bash
# Sử dụng profile generator
python build/generate_profile.py \
    --os Windows \
    --os-version 10.0 \
--chrome-version 146.0.7680.76 \
    --gpu nvidia_rtx_3060 \
    --timezone vietnam \
    --screen fhd \
    --output my_profile.json
```

## Troubleshooting

### Lỗi "patch does not apply"
```bash
# Revert và apply lại
python build/apply_patches.py --chromium-src=/path/to/chromium/src --revert
python build/apply_patches.py --chromium-src=/path/to/chromium/src
```

### Lỗi build
```bash
# Clean và build lại
gn clean out/Release
gn gen out/Release
ninja -C out/Release chrome
```

### Lỗi "file not found"
Đảm bảo đã copy source files vào đúng vị trí trong Chromium source tree.

## Cập nhật Chromium version

1. Checkout version mới:
   ```bash
   git checkout <new_version>
   gclient sync
   ```

2. Kiểm tra patches có apply được không:
   ```bash
   python build/apply_patches.py --chromium-src=/path/to/chromium/src --dry-run
   ```

3. Nếu có conflict, cập nhật patches cho version mới.

## Các flag dòng lệnh

| Flag | Mô tả |
|------|-------|
| `--chromiumsoncuto-profile` | Đường dẫn tới file profile JSON |
| `--chromiumsoncuto-seed` | Master seed cho fingerprint |
| `--chromiumsoncuto-debug` | Bật debug logging |
| `--disable-chromiumsoncuto` | Tắt toàn bộ fingerprint spoofing |

## Lưu ý bảo mật

- **KHÔNG** sử dụng cho mục đích bất hợp pháp
- Profile chỉ nên dùng cho testing và research
- Luôn tuân thủ ToS của các website
