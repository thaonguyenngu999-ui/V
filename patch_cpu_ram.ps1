$concurrencyFile = "E:\chromium\src\third_party\blink\renderer\core\frame\navigator_concurrent_hardware.cc"
$memoryFile = "E:\chromium\src\third_party\blink\renderer\core\frame\navigator_device_memory.cc"

Write-Host "=== Reading files ===" -ForegroundColor Green

# Read concurrency file
$concurrency = Get-Content $concurrencyFile -Raw
Write-Host "=== navigator_concurrent_hardware.cc ===" -ForegroundColor Yellow
Write-Host $concurrency

Write-Host "`n=== navigator_device_memory.cc ===" -ForegroundColor Yellow
$memory = Get-Content $memoryFile -Raw
Write-Host $memory

# Patch concurrency - use command line switch instead of env var
$newConcurrency = @'
// Copyright 2014 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "third_party/blink/renderer/core/frame/navigator_concurrent_hardware.h"

#include "base/command_line.h"
#include "base/strings/string_number_conversions.h"
#include "base/system/sys_info.h"

namespace blink {

unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {
  // S Manage: Override via command line switch
  const base::CommandLine* cmd = base::CommandLine::ForCurrentProcess();
  if (cmd->HasSwitch("hardware-concurrency")) {
    unsigned value = 0;
    if (base::StringToUint(cmd->GetSwitchValueASCII("hardware-concurrency"), &value) && value > 0) {
      return value;
    }
  }
  // Default: return actual value
  return static_cast<unsigned>(base::SysInfo::NumberOfProcessors());
}

}  // namespace blink
'@

# Patch memory
$newMemory = @'
// Copyright 2014 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "third_party/blink/renderer/core/frame/navigator_device_memory.h"

#include "base/command_line.h"
#include "base/strings/string_number_conversions.h"
#include "third_party/blink/public/common/device_memory/approximated_device_memory.h"

namespace blink {

float NavigatorDeviceMemory::deviceMemory() const {
  // S Manage: Override via command line switch
  const base::CommandLine* cmd = base::CommandLine::ForCurrentProcess();
  if (cmd->HasSwitch("device-memory")) {
    double value = 0;
    if (base::StringToDouble(cmd->GetSwitchValueASCII("device-memory"), &value) && value > 0) {
      return static_cast<float>(value);
    }
  }
  // Default: return approximated value
  return ApproximatedDeviceMemory::GetApproximatedDeviceMemory();
}

}  // namespace blink
'@

Write-Host "`n=== Patching files ===" -ForegroundColor Green
$newConcurrency | Set-Content $concurrencyFile -NoNewline
Write-Host "Patched navigator_concurrent_hardware.cc"

$newMemory | Set-Content $memoryFile -NoNewline
Write-Host "Patched navigator_device_memory.cc"

Write-Host "`n=== Done ===" -ForegroundColor Green
