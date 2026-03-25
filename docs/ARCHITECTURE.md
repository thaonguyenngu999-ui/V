# Kiến trúc ChromiumSoncuto

## Tổng quan

ChromiumSoncuto là một bản mod của Chromium với khả năng kiểm soát hoàn toàn browser fingerprint. Dự án được thiết kế theo các nguyên tắc:

1. **Nhất quán (Consistency)**: Mọi fingerprint vector phải đồng bộ logic
2. **Kiểm soát (Controllability)**: Mọi giá trị có thể cấu hình
3. **Persistence**: Profile được lưu và load lại
4. **Stealth**: Không để lại dấu vết automation

## Cấu trúc thư mục

```
ChromiumSoncuto/
├── src/
│   └── fingerprint_controller/    # Core modules
│       ├── fingerprint_config.h   # Profile configuration
│       ├── fingerprint_config.cc  # Profile implementation
│       ├── canvas_spoof.h         # Canvas fingerprint
│       ├── webgl_spoof.h          # WebGL fingerprint
│       ├── audio_spoof.h          # Audio fingerprint
│       ├── navigator_spoof.h      # Navigator/Screen
│       ├── media_devices_spoof.h  # MediaDevices
│       ├── font_spoof.h           # Font enumeration
│       └── anti_detection.h       # Anti-bot bypass
├── patches/
│   ├── fingerprint/               # Fingerprint patches
│   ├── anti-detection/            # Anti-bot patches
│   └── network/                   # TLS/HTTP patches
├── profiles/                      # JSON profiles
├── build/                         # Build scripts
└── docs/                          # Documentation
```

## Module chính

### 1. FingerprintController (fingerprint_config.h/cc)

Singleton controller quản lý toàn bộ fingerprint configuration.

```cpp
class FingerprintController {
public:
    static FingerprintController& GetInstance();
    
    bool LoadProfile(const std::string& path);
    const FingerprintProfile* GetProfile() const;
    bool SaveProfile(const std::string& path) const;
};
```

**Structs cấu hình:**
- `ScreenConfig`: width, height, colorDepth, devicePixelRatio
- `HardwareConfig`: hardwareConcurrency, deviceMemory, platform
- `WebGLConfig`: vendor, renderer, GPU parameters
- `CanvasConfig`: noise seed, intensity
- `AudioConfig`: noise seed, sample rate
- `TimezoneConfig`: timezone, locale, language
- `NavigatorConfig`: userAgent, platform, webdriver
- `ClientHintsConfig`: brand, version, platform
- `FontConfig`: available fonts list
- `MediaDevicesConfig`: audio/video devices
- `BatteryConfig`: charging state
- `NetworkConfig`: connection type

### 2. Canvas Spoofing (canvas_spoof.h)

Inject noise vào Canvas API để tạo fingerprint nhất quán.

```cpp
void ApplyCanvasNoise(uint8_t* data, int width, int height,
                      uint64_t seed, double intensity);
```

**Thuật toán:**
1. Hash nội dung canvas để tạo seed (nếu consistent mode)
2. Dùng Xorshift128+ PRNG với seed
3. Apply noise cực nhỏ (0.0001) vào RGB channels
4. Giữ nguyên alpha channel

**Hooks:**
- `toDataURL()`
- `toBlob()`
- `getImageData()`
- WebGL `readPixels()`

### 3. WebGL Spoofing (webgl_spoof.h)

Spoof WebGL parameters và debug info.

```cpp
class WebGLSpoofController {
    std::string GetParameterString(uint32_t pname) const;
    int GetParameterInt(uint32_t pname) const;
};
```

**GPU Presets:**
- NVIDIA RTX 3060, 4070
- AMD RX 6700 XT
- Intel UHD 630
- Apple M1, M2

**Spoofed parameters:**
- `VENDOR`, `RENDERER`
- `UNMASKED_VENDOR_WEBGL`, `UNMASKED_RENDERER_WEBGL`
- `MAX_TEXTURE_SIZE`, `MAX_RENDERBUFFER_SIZE`
- `MAX_VERTEX_ATTRIBS`, `MAX_VARYING_VECTORS`
- Và nhiều parameters khác

### 4. Audio Spoofing (audio_spoof.h)

Inject noise vào Web Audio API.

```cpp
class AudioNoiseInjector {
    void ApplyNoise(float* data, size_t length);
};
```

**Hooks:**
- `AudioContext.sampleRate`
- `AnalyserNode.getFloatFrequencyData()`
- `AnalyserNode.getByteFrequencyData()`
- `OfflineAudioContext.startRendering()`
- `OscillatorNode.frequency`

### 5. Navigator Spoofing (navigator_spoof.h)

Spoof Navigator và Screen properties.

```cpp
class NavigatorSpoof {
    std::string HookUserAgent() const;
    std::string HookPlatform() const;
    int HookHardwareConcurrency() const;
    double HookDeviceMemory() const;
    bool HookWebdriver() const;  // Always false
};
```

**Đảm bảo consistency:**
- UA phải match với platform
- hardwareConcurrency hợp lý (2-128)
- deviceMemory trong các giá trị cho phép
- Client hints phải match với UA

### 6. MediaDevices Spoofing (media_devices_spoof.h)

Spoof danh sách thiết bị media.

```cpp
class MediaDevicesSpoof {
    std::vector<SpoofedMediaDeviceInfo> EnumerateDevices() const;
};
```

**Features:**
- Device IDs nhất quán theo master seed
- Group IDs cho related devices
- Realistic device labels theo platform

### 7. Font Spoofing (font_spoof.h)

Kiểm soát font enumeration.

```cpp
class FontSpoofController {
    std::vector<std::string> GetPlatformFonts() const;
    bool FontExists(const std::string& font_family) const;
};
```

**Font lists:**
- Windows 10/11 fonts
- macOS fonts
- Linux fonts

### 8. Anti-Detection (anti_detection.h)

Bypass các kỹ thuật phát hiện bot.

```cpp
class WebDriverBypass {
    void PatchNavigatorWebdriver();
    void RemoveCdcVariables();
};

class HeadlessDetectionBypass {
    void PatchWindowChrome();
    void PatchNavigatorPlugins();
};
```

**Bypasses:**
- `navigator.webdriver` = false
- Remove `cdc_*` variables
- Realistic `window.chrome` object
- Proper plugins list
- Proper outerWidth/outerHeight
- Permission policy spoofing

## Flow Diagram

```
                    ┌─────────────────────┐
                    │   Profile JSON      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ FingerprintController│
                    │    (Singleton)      │
                    └──────────┬──────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │  Canvas   │       │   WebGL   │       │   Audio   │
    │   Spoof   │       │   Spoof   │       │   Spoof   │
    └───────────┘       └───────────┘       └───────────┘
          │                    │                    │
          ├────────────────────┼────────────────────┤
          │                    │                    │
          ▼                    ▼                    ▼
    ┌───────────┐       ┌───────────┐       ┌───────────┐
    │ Navigator │       │   Media   │       │   Font    │
    │   Spoof   │       │  Devices  │       │   Spoof   │
    └───────────┘       └───────────┘       └───────────┘
          │                    │                    │
          └────────────────────┼────────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Anti-Detection    │
                    │      Patches        │
                    └─────────────────────┘
```

## Noise Generation

Sử dụng **Xorshift128+ PRNG** với deterministic seed:

```cpp
class NoiseGenerator {
    uint64_t state_[2];
    
    uint64_t Next() {
        uint64_t s1 = state_[0];
        const uint64_t s0 = state_[1];
        state_[0] = s0;
        s1 ^= s1 << 23;
        state_[1] = s1 ^ s0 ^ (s1 >> 17) ^ (s0 >> 26);
        return state_[1] + s0;
    }
};
```

**Tại sao Xorshift128+?**
- Nhanh (chỉ cần bitwise operations)
- Deterministic (cùng seed → cùng output)
- Đủ random cho mục đích noise

## Seed Hierarchy

```
Master Seed (profile)
    │
    ├── Canvas Seed = Hash("canvas", master_seed)
    │
    ├── Audio Seed = Hash("audio", master_seed)
    │
    ├── Device ID Seed = Hash(device_type + index, master_seed)
    │
    └── Group ID Seed = Hash(group_type + index, master_seed)
```

## TLS Fingerprint

Patch network stack để match Chrome TLS fingerprint:

**JA3 Components:**
1. SSL Version: TLS 1.3
2. Cipher Suites: Chrome 120 order
3. Extensions: Chrome 120 order
4. Elliptic Curves: X25519, P-256, P-384
5. EC Point Formats: uncompressed

## Profile JSON Structure

```json
{
    "profile_id": "uuid",
    "profile_name": "name",
    "master_seed": 123456789,
    
    "screen": { ... },
    "hardware": { ... },
    "webgl": { ... },
    "canvas": { ... },
    "audio": { ... },
    "timezone": { ... },
    "navigator": { ... },
    "client_hints": { ... },
    "fonts": { ... },
    "media_devices": { ... },
    "battery": { ... },
    "network": { ... }
}
```

## Consistency Rules

1. **Platform Matching**:
   - `navigator.platform` ↔ `userAgent` OS
   - `client_hints.platform` ↔ `navigator.platform`

2. **Hardware Matching**:
   - `deviceMemory` ∈ {0.25, 0.5, 1, 2, 4, 8, 16, 32, 64}
   - `hardwareConcurrency` ∈ [1, 128]

3. **Screen Matching**:
   - `availWidth` ≤ `width`
   - `availHeight` ≤ `height`

4. **Mobile Matching**:
   - `client_hints.mobile` ↔ touch support ↔ screen size

## Security Considerations

- Fingerprint chỉ dùng cho testing/research
- Không bypass security controls
- Không sử dụng cho fraud
- Tuân thủ ToS của websites
