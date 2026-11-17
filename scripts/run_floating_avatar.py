"""
JARVIS Floating Desktop Avatar Launcher
Creates an always-on-top, floating biometric AI face directly on the Windows 11 desktop.
"""

import os
import sys
import time
import subprocess
import ctypes
import ctypes.wintypes
from typing import Optional

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.SetWindowPos.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.UINT
]
user32.SetWindowPos.restype = ctypes.wintypes.BOOL


def get_screen_bounds():
    """Returns the primary monitor dimensions in logical pixels."""
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return w, h


def find_browser_executable() -> Optional[str]:
    """Finds installed Google Chrome or Microsoft Edge executable."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def pin_avatar_window_topmost():
    """Finds the JARVIS Avatar window and pins it to HWND_TOPMOST."""
    h_def = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    if h_def:
        user32.SetThreadDesktop(h_def)

    found_hwnd = None

    def enum_cb(hwnd, extra):
        nonlocal found_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value
                if "JARVIS" in title and "Google Chrome" not in title:
                    found_hwnd = hwnd
                    return False
        return True

    WNDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumDesktopWindows(h_def, WNDENUM(enum_cb), 0)

    if found_hwnd:
        res = user32.SetWindowPos(
            ctypes.wintypes.HWND(found_hwnd),
            ctypes.wintypes.HWND(HWND_TOPMOST),
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )
        user32.SetForegroundWindow(ctypes.wintypes.HWND(found_hwnd))
        print(f"[JARVIS] Pinned Avatar window (HWND: {found_hwnd}) to Always-On-Top (Status: {res}).")
        return True
    return False


def main():
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173/?mode=widget"
    browser_exe = find_browser_executable()
    if not browser_exe:
        print("[JARVIS] Error: No compatible Chrome or Edge browser found.")
        sys.exit(1)

    screen_w, screen_h = get_screen_bounds()
    width = 370
    height = 470
    pos_x = max(20, screen_w - width - 26)
    pos_y = max(20, screen_h - height - 54)

    user_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".avatar_chrome_data"
    )

    print(f"[JARVIS] Screen detected: {screen_w}x{screen_h}.")
    print(f"[JARVIS] Spawning Floating Desktop Avatar at ({pos_x}, {pos_y}) [{width}x{height}]...")

    cmd = [
        browser_exe,
        f"--app={target_url}",
        f"--user-data-dir={user_data_dir}",
        f"--window-size={width},{height}",
        f"--window-position={pos_x},{pos_y}",
        "--disable-features=Translate,OptimizationHints",
        "--no-first-run",
        "--no-default-browser-check"
    ]

    proc = subprocess.Popen(cmd)

    # Pin to TopMost once window is mapped
    for _ in range(8):
        time.sleep(1.0)
        if pin_avatar_window_topmost():
            break

    print("[JARVIS] Floating Avatar Face is now active on your desktop screen.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("[JARVIS] Avatar widget closed.")


if __name__ == "__main__":
    main()
