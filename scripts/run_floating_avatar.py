"""
JARVIS Floating Desktop Avatar Launcher
Launches a compact, always-on-top, frameless floating virtual AI face on the Windows desktop.
"""

import os
import sys
import time
import subprocess
import ctypes
from typing import Optional

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1


def find_browser_executable() -> Optional[str]:
    """Finds installed Microsoft Edge or Google Chrome executable."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def set_window_always_on_top(window_title: str):
    """Sets matching window to HWND_TOPMOST using Windows User32 API."""
    user32 = ctypes.windll.user32
    found_hwnd = None

    def enum_windows_callback(hwnd, extra):
        nonlocal found_hwnd
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.lower()
            if window_title.lower() in title or "jarvis" in title:
                found_hwnd = hwnd
                return False
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    cb = WNDENUMPROC(enum_windows_callback)
    user32.EnumWindows(cb, 0)

    if found_hwnd:
        # Set HWND_TOPMOST (-1)
        user32.SetWindowPos(
            found_hwnd,
            HWND_TOPMOST,
            0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW
        )
        print(f"[JARVIS] Pinned Avatar window (HWND: {found_hwnd}) to Always-On-Top on Desktop.")
        return True
    return False


def launch_avatar_widget(url: str = "http://localhost:5173/?mode=widget", width: int = 320, height: int = 400):
    """Launches the floating avatar widget window."""
    browser_exe = find_browser_executable()
    if not browser_exe:
        print("[JARVIS] Error: No compatible browser found for app mode window.")
        return False

    print(f"[JARVIS] Spawning Floating Desktop Avatar with {os.path.basename(browser_exe)}...")
    user_data_dir = os.path.join(os.path.expandvars("%TEMP%"), "jarvis_avatar_edge_profile")
    cmd = [
        browser_exe,
        f"--app={url}",
        f"--user-data-dir={user_data_dir}",
        f"--window-size={width},{height}",
        "--window-position=1550,600",
        "--disable-extensions",
        "--disable-background-networking"
    ]

    proc = subprocess.Popen(cmd)

    # Allow window to map, then pin to topmost
    time.sleep(1.8)
    for _ in range(6):
        if set_window_always_on_top("jarvis"):
            break
        time.sleep(0.8)

    print("[JARVIS] Floating Avatar Face is now visible on your desktop screen.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        print("[JARVIS] Avatar widget closed.")


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173/?mode=widget"
    launch_avatar_widget(target_url)
