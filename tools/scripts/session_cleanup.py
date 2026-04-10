"""Kill stale claude.exe processes older than 8 hours.

Replaces session_cleanup.ps1 -- Python is lighter than PowerShell under
memory pressure and consistent with the rest of the Jarvis stack.
"""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes

STALE_HOURS = 8

kernel32 = ctypes.WinDLL("kernel32")
psapi = ctypes.WinDLL("psapi")

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_TERMINATE = 0x0001
FILETIME = wintypes.FILETIME


def main() -> None:
    # Current time in 100-ns ticks
    now_ft = FILETIME()
    kernel32.GetSystemTimeAsFileTime(ctypes.byref(now_ft))
    now_100ns = (now_ft.dwHighDateTime << 32) | now_ft.dwLowDateTime
    cutoff_100ns = STALE_HOURS * 3600 * 10_000_000

    # Enumerate processes
    arr = (ctypes.c_ulong * 4096)()
    size = ctypes.c_ulong()
    psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(size))
    count = size.value // ctypes.sizeof(ctypes.c_ulong)

    killed = 0
    for i in range(count):
        pid = arr[i]
        if pid == 0:
            continue

        h = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE, False, pid
        )
        if not h:
            continue

        try:
            # Check process name
            buf = (ctypes.c_char * 260)()
            sz = ctypes.c_ulong(260)
            if not kernel32.QueryFullProcessImageNameA(h, 0, buf, ctypes.byref(sz)):
                continue
            name = os.path.basename(buf.value.decode("ascii", errors="replace")).lower()
            if name != "claude.exe":
                continue

            # Check age
            ct, et, kt, ut = FILETIME(), FILETIME(), FILETIME(), FILETIME()
            if not kernel32.GetProcessTimes(
                h,
                ctypes.byref(ct),
                ctypes.byref(et),
                ctypes.byref(kt),
                ctypes.byref(ut),
            ):
                continue

            create_100ns = (ct.dwHighDateTime << 32) | ct.dwLowDateTime
            age_100ns = now_100ns - create_100ns
            age_hours = age_100ns / (3600 * 10_000_000)

            if age_100ns < cutoff_100ns:
                continue

            print(f"Killing PID {pid} ({age_hours:.1f}h old)")
            if kernel32.TerminateProcess(h, 1):
                killed += 1
        finally:
            kernel32.CloseHandle(h)

    if killed:
        print(f"Killed {killed} stale claude session(s).")
    else:
        print("No stale sessions found (all under 8h old).")


if __name__ == "__main__":
    main()
