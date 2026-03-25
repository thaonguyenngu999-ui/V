// Copyright 2014 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "third_party/blink/renderer/core/frame/navigator_concurrent_hardware.h"

#include <cstdlib>  // S Manage: for std::getenv, std::atoi

#include "base/system/sys_info.h"
#include "third_party/blink/renderer/platform/runtime_enabled_features.h"

namespace blink {

namespace {

// TODO(435582603): Hard-coding this to a common value is a reasonable start,
// but it likely makes sense to vary the hard-coded number by platform and
// form-factor in order to maintain plausibility over time.
constexpr unsigned kReducedHardwareConcurrencyValue = 8u;

}  // namespace

unsigned NavigatorConcurrentHardware::hardwareConcurrency() const {
  // S Manage: Override hardware concurrency via environment variable
  const char* override_val = std::getenv("SMANAGE_HARDWARE_CONCURRENCY");
  if (override_val) {
    int val = std::atoi(override_val);
    if (val > 0) {
      return static_cast<unsigned>(val);
    }
  }
  
  if (RuntimeEnabledFeatures::ReduceHardwareConcurrencyEnabled()) {
    return kReducedHardwareConcurrencyValue;
  }
  return static_cast<unsigned>(base::SysInfo::NumberOfProcessors());
}

}  // namespace blink
