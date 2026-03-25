"""
Stage-based build runner with explicit progress logging.
"""

from __future__ import annotations

import sys
import time
from datetime import timedelta

import build_package as build


def run_stage(label: str, func) -> bool:
    started = time.monotonic()
    build.log_phase(f"{label}: start")
    result = func()
    duration = timedelta(seconds=int(time.monotonic() - started))
    build.log_phase(f"{label}: done result={result} duration={duration}")
    return result is not False


def main() -> int:
    if not run_stage("1/4 check_requirements", build.check_requirements):
        return 1
    if not run_stage("2/4 build_exe", build.build_exe):
        return 1
    if not run_stage("3/4 package_release", build.package_release):
        return 1
    if not run_stage("4/4 create_portable", build.create_portable):
        return 1
    build.log_phase("rebuild complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
