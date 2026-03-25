# 🖥️ S Manage - Hướng Dẫn Sử Dụng GUI Manager

**Tài liệu hướng dẫn chi tiết về quản lý profiles và sử dụng GUI**

---

## 📑 Mục Lục

1. [Khởi Động](#1-khởi-động)
2. [Giao Diện Chính](#2-giao-diện-chính)
3. [Quản Lý Profiles](#3-quản-lý-profiles)
4. [Cấu Hình Fingerprint](#4-cấu-hình-fingerprint)
5. [GPU Presets](#5-gpu-presets)
6. [Timezone](#6-timezone)
7. [Proxy](#7-proxy)
8. [Chạy Profile](#8-chạy-profile)
9. [Settings](#9-settings)
10. [Tips & Tricks](#10-tips--tricks)

---

## 1. Khởi Động

### Cách 1: Chạy EXE
```
Double-click SManage.exe
```

### Cách 2: Chạy từ source
```powershell
cd F:\ChromiumSoncuto\manager
python gui_v3.py
```

### Lần đầu khởi động

1. **Chọn thư mục lưu profiles**
   - Có thể chọn bất kỳ thư mục nào
   - Khuyến nghị: `C:\Users\<tên>\Desktop\profiles` hoặc thư mục riêng
   - Thư mục này sẽ chứa tất cả data của profiles

2. **Giao diện chính sẽ hiện ra**
   - Lần sau khởi động sẽ tự động dùng thư mục đã chọn
   - Có thể đổi trong Settings

---

## 2. Giao Diện Chính

```
┌─────────────────────────────────────────────────────────────────┐
│  🛡️ S Manage                              [Settings] [Refresh] │
├─────────────────────────────────────────────────────────────────┤
│  [➕ New Profile]  [📋 Duplicate]  [✏️ Edit]  [🗑️ Delete]       │
├─────────────────────────────────────────────────────────────────┤
│  #  │ Name      │ GPU           │ Status  │ Actions            │
│  1  │ Profile 1 │ RTX 3060      │ Stopped │ [▶ Start] [⬛ Stop]│
│  2  │ Profile 2 │ RX 580        │ Running │ [▶ Start] [⬛ Stop]│
│  3  │ Profile 3 │ Intel UHD     │ Stopped │ [▶ Start] [⬛ Stop]│
├─────────────────────────────────────────────────────────────────┤
│  Total: 3 profiles │ Running: 1 │ Version: 3.0                 │
└─────────────────────────────────────────────────────────────────┘
```

### Các thành phần

| Thành phần | Mô tả |
|------------|-------|
| **Header** | Logo, Settings, Refresh |
| **Toolbar** | Các nút tạo/sửa/xóa profile |
| **Profile List** | Danh sách tất cả profiles |
| **Status Bar** | Thống kê và version |

---

## 3. Quản Lý Profiles

### 3.1 Tạo Profile Mới

1. Click **[➕ New Profile]**
2. Nhập tên profile (hoặc để auto-generate)
3. Cấu hình fingerprint (xem mục 4)
4. Click **[Save]**

### 3.2 Duplicate Profile

1. Chọn profile cần copy trong danh sách
2. Click **[📋 Duplicate]**
3. Profile mới được tạo với cùng config
4. Chỉnh sửa nếu cần

### 3.3 Edit Profile

1. Chọn profile trong danh sách
2. Click **[✏️ Edit]** hoặc double-click
3. Thay đổi config
4. Click **[Save]**

### 3.4 Delete Profile

1. Chọn profile trong danh sách
2. Click **[🗑️ Delete]**
3. Confirm xóa
4. ⚠️ **Lưu ý:** Xóa profile sẽ xóa cả cookies/data

### 3.5 Cấu trúc thư mục Profile

```
profiles_folder/
├── profiles.json              # Danh sách profiles
└── profile_a1b2c3d4/         # Folder của mỗi profile
    ├── config.json           # Fingerprint config
    └── UserData/             # Chrome user data
        ├── Default/
        │   ├── Cookies
        │   ├── History
        │   ├── Login Data
        │   └── ...
        └── ...
```

---

## 4. Cấu Hình Fingerprint

### Dialog Config

```
┌─────────────────────────────────────────────┐
│  Edit Profile: Profile 1                    │
├─────────────────────────────────────────────┤
│  Name:        [Profile 1              ]     │
│                                             │
│  ── GPU ──                                  │
│  Brand:       [NVIDIA ▼]                    │
│  Model:       [RTX 3060 ▼]                  │
│                                             │
│  ── Screen ──                               │
│  Width:       [1920]                        │
│  Height:      [1080]                        │
│                                             │
│  ── Timezone ──                             │
│  Zone:        [Vietnam (UTC+7) ▼]           │
│                                             │
│  ── Proxy ──                                │
│  Proxy:       [socks5://user:pass@ip:port]  │
│                                             │
│  ── Language ──                             │
│  Language:    [en-US,en ▼]                  │
│                                             │
│           [Cancel]  [Save]                  │
└─────────────────────────────────────────────┘
```

### Các trường config

| Trường | Mô tả | Ví dụ |
|--------|-------|-------|
| **Name** | Tên hiển thị | "Facebook Account 1" |
| **GPU Brand** | Hãng GPU | NVIDIA, AMD, Intel |
| **GPU Model** | Model cụ thể | RTX 3060, RX 580 |
| **Screen Width** | Độ rộng màn hình | 1920, 1366, 2560 |
| **Screen Height** | Độ cao màn hình | 1080, 768, 1440 |
| **Timezone** | Múi giờ | Vietnam (UTC+7) |
| **Proxy** | Proxy server | socks5://user:pass@ip:port |
| **Language** | Ngôn ngữ | en-US, vi-VN |

### Fingerprint cố định (từ Chromium)

| Fingerprint | Giá trị | Ghi chú |
|-------------|---------|---------|
| CPU Cores | 8 | Hardcoded trong Chromium |
| RAM | 8 GB | Hardcoded trong Chromium |
| Platform | Win32 | Native |

---

## 5. GPU Presets

### NVIDIA

| Model | WebGL Renderer String |
|-------|----------------------|
| GTX 1050 Ti | ANGLE (NVIDIA, NVIDIA GeForce GTX 1050 Ti Direct3D11 vs_5_0 ps_5_0, D3D11) |
| GTX 1650 | ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| GTX 1660 Ti | ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RTX 2060 | ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RTX 3060 | ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RTX 3070 | ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RTX 3080 | ANGLE (NVIDIA, NVIDIA GeForce RTX 3080 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RTX 4060 | ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RTX 4070 | ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RTX 4080 | ANGLE (NVIDIA, NVIDIA GeForce RTX 4080 Direct3D11 vs_5_0 ps_5_0, D3D11) |

### AMD

| Model | WebGL Renderer String |
|-------|----------------------|
| RX 580 | ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RX 5600 XT | ANGLE (AMD, AMD Radeon RX 5600 XT Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RX 6600 XT | ANGLE (AMD, AMD Radeon RX 6600 XT Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RX 6700 XT | ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RX 6800 XT | ANGLE (AMD, AMD Radeon RX 6800 XT Direct3D11 vs_5_0 ps_5_0, D3D11) |
| RX 7900 XTX | ANGLE (AMD, AMD Radeon RX 7900 XTX Direct3D11 vs_5_0 ps_5_0, D3D11) |
| Radeon Graphics | ANGLE (AMD, AMD Radeon Graphics Direct3D11 vs_5_0 ps_5_0, D3D11) |

### Intel

| Model | WebGL Renderer String |
|-------|----------------------|
| HD Graphics 530 | ANGLE (Intel, Intel(R) HD Graphics 530 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| UHD Graphics 620 | ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| UHD Graphics 630 | ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| UHD Graphics 770 | ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11) |
| Iris Xe Graphics | ANGLE (Intel, Intel(R) Iris Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11) |

---

## 6. Timezone

### Presets có sẵn

| Tên | Timezone | UTC Offset |
|-----|----------|------------|
| Vietnam (UTC+7) | Asia/Ho_Chi_Minh | +07:00 |
| Thailand (UTC+7) | Asia/Bangkok | +07:00 |
| Singapore (UTC+8) | Asia/Singapore | +08:00 |
| Japan (UTC+9) | Asia/Tokyo | +09:00 |
| US East (UTC-5) | America/New_York | -05:00 |
| US West (UTC-8) | America/Los_Angeles | -08:00 |
| UK (UTC+0) | Europe/London | +00:00 |
| Germany (UTC+1) | Europe/Berlin | +01:00 |
| Australia (UTC+10) | Australia/Sydney | +10:00 |

### Timezone ảnh hưởng đến

- `new Date().getTimezoneOffset()`
- `Intl.DateTimeFormat().resolvedOptions().timeZone`
- Các trang web check IP location

---

## 7. Proxy

### Định dạng hỗ trợ

```
# HTTP Proxy
http://ip:port
http://user:pass@ip:port

# SOCKS5 Proxy
socks5://ip:port
socks5://user:pass@ip:port
```

### Ví dụ

```
# Proxy không auth
http://192.168.1.1:8080
socks5://proxy.example.com:1080

# Proxy có auth
http://myuser:mypass@192.168.1.1:8080
socks5://user123:pass456@proxy.example.com:1080
```

### Lưu ý

- Proxy chỉ áp dụng cho browser, không ảnh hưởng GUI
- Để trống nếu không dùng proxy
- Test proxy trước khi sử dụng
- WebRTC đã được disable để tránh leak IP

---

## 8. Chạy Profile

### Start Profile

1. Chọn profile trong danh sách
2. Click **[▶ Start]**
3. Browser sẽ mở với fingerprint đã config
4. Status chuyển thành "Running"

### Stop Profile

1. Chọn profile đang chạy
2. Click **[⬛ Stop]**
3. Browser sẽ đóng
4. Status chuyển thành "Stopped"

### Chạy nhiều Profile cùng lúc

- ✅ Có thể chạy nhiều profile đồng thời
- Mỗi profile có user data riêng biệt
- Mỗi profile có fingerprint riêng biệt
- RAM cần thiết: ~300-500MB mỗi profile

### Lưu ý khi chạy

1. **Đợi browser mở hoàn toàn** trước khi làm gì
2. **CDP injection** mất 2-3 giây để activate
3. **Đóng browser bình thường** (click X) để lưu cookies
4. **Không kill process** bằng Task Manager

---

## 9. Settings

### Mở Settings

Click **[⚙️ Settings]** ở góc phải header

### Các tùy chọn

| Setting | Mô tả |
|---------|-------|
| **Profiles Path** | Thư mục lưu profiles |
| **Browser Path** | Đường dẫn đến chrome.exe |
| **Start URL** | URL mở khi start profile |
| **Auto Refresh** | Tự động refresh danh sách |

### Thay đổi Browser Path

1. Mở Settings
2. Click **[Browse]** bên cạnh Browser Path
3. Chọn file chrome.exe
4. Click **[Save]**

---

## 10. Tips & Tricks

### 10.1 Tối ưu hiệu suất

```
✅ Đóng các profile không dùng
✅ Xóa cache định kỳ trong browser
✅ Sử dụng SSD thay HDD
✅ RAM 16GB+ nếu chạy nhiều profile
```

### 10.2 Bảo mật Fingerprint

```
✅ Mỗi profile dùng GPU khác nhau
✅ Mix NVIDIA, AMD, Intel
✅ Timezone phù hợp với IP/Proxy
✅ Không dùng cùng proxy cho nhiều profile
```

### 10.3 Tránh bị detect

```
✅ Không chạy quá nhiều profile cùng lúc
✅ Để thời gian giữa các hành động
✅ Sử dụng proxy chất lượng
✅ Clear cookies nếu bị ban
```

### 10.4 Backup Profiles

```powershell
# Backup toàn bộ profiles
Copy-Item "C:\path\to\profiles" "D:\backup\profiles_backup" -Recurse

# Backup 1 profile cụ thể
Copy-Item "C:\path\to\profiles\profile_abc123" "D:\backup\" -Recurse
```

### 10.5 Import/Export Profile

```
Hiện tại chưa có tính năng import/export.
Workaround: Copy thư mục profile thủ công.
```

### 10.6 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| F5 | Refresh danh sách |
| Ctrl+N | New Profile |
| Delete | Delete selected profile |
| Enter | Start selected profile |
| Escape | Close dialog |

---

## 📋 Quick Reference

### Tạo profile mới
```
[➕ New Profile] → Đặt tên → Chọn GPU → Chọn Timezone → [Save]
```

### Chạy profile
```
Chọn profile → [▶ Start] → Đợi browser mở
```

### Edit fingerprint
```
Chọn profile → [✏️ Edit] → Thay đổi config → [Save] → Restart profile
```

### Dùng proxy
```
[Edit] → Nhập proxy vào ô Proxy → [Save] → Start profile
```

---

## ❓ FAQ

### Q: Tại sao CPU và RAM không đổi được?
**A:** CPU (8 cores) và RAM (8GB) được hardcode trong Chromium source. Để thay đổi cần rebuild Chromium.

### Q: Profile có lưu cookies không?
**A:** Có. Tất cả cookies, history, login được lưu trong UserData folder của mỗi profile.

### Q: Chạy được bao nhiêu profile cùng lúc?
**A:** Tùy RAM. Mỗi profile cần ~300-500MB RAM. Với 16GB RAM có thể chạy 10-20 profile.

### Q: Fingerprint có unique không?
**A:** Mỗi profile có WebGL GPU, timezone, proxy riêng. CPU/RAM giống nhau (8/8).

### Q: Làm sao biết đã pass fingerprint test?
**A:** Mở https://iphey.com hoặc https://pixelscan.net và kiểm tra.

---

**Cập nhật lần cuối: January 2026**
**Version: 3.0**
