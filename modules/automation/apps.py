"""
Windows Application Lifecycle & Window Management Engine
Controls application startup, shutdown, and window manipulation via Win32 APIs and psutil.
"""

import subprocess
import os
import logging
from typing import List, Dict, Any, Optional
import psutil

# Safe import of pywin32
try:
    import win32gui
    import win32con
    import win32process
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

logger = logging.getLogger("jarvis.automation.apps")


class ApplicationManager:
    KNOWN_APP_COMMANDS = {
        "vs code": "code",
        "vscode": "code",
        "chrome": "chrome",
        "firefox": "firefox",
        "edge": "msedge",
        "notepad": "notepad",
        "calculator": "calc",
        "terminal": "wt",
        "powershell": "powershell",
        "cmd": "cmd",
        "spotify": "spotify",
        "explorer": "explorer"
    }

    @classmethod
    def launch(cls, app_name: str, args: Optional[str] = None) -> Dict[str, Any]:
        """Launches an application with optional arguments."""
        clean_name = app_name.lower().strip()
        cmd = cls.KNOWN_APP_COMMANDS.get(clean_name, app_name)
        full_command = f"{cmd} {args}" if args else cmd

        try:
            # Use detached process so it doesn't block JARVIS
            proc = subprocess.Popen(
                full_command,
                shell=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
            )
            logger.info(f"Launched application '{app_name}' (PID: {proc.pid})")
            return {
                "success": True,
                "app_name": app_name,
                "command": full_command,
                "pid": proc.pid
            }
        except Exception as e:
            logger.error(f"Failed to launch '{app_name}': {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @classmethod
    def close(cls, app_name: str, force: bool = False) -> Dict[str, Any]:
        """Terminates active processes matching the application name."""
        clean_name = app_name.lower().strip().replace(".exe", "")
        terminated = []

        for proc in psutil.process_iter(['pid', 'name']):
            try:
                p_name = proc.info['name'].lower().replace(".exe", "")
                if clean_name in p_name:
                    p = psutil.Process(proc.info['pid'])
                    if force:
                        p.kill()
                    else:
                        p.terminate()
                    terminated.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "success": len(terminated) > 0,
            "terminated_pids": terminated,
            "count": len(terminated),
            "message": f"Terminated {len(terminated)} process(es) matching '{app_name}'."
        }

    @classmethod
    def list_open_windows(cls) -> List[Dict[str, Any]]:
        """Returns all visible desktop application windows."""
        windows = []
        if not PYWIN32_AVAILABLE:
            return windows

        def enum_windows_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        pname = psutil.Process(pid).name()
                    except Exception:
                        pname = "unknown"
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "pid": pid,
                        "process_name": pname
                    })
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception as e:
            logger.warning(f"Error enumerating windows: {e}")

        return windows

    @classmethod
    def focus_window(cls, title_substring: str) -> bool:
        """Brings the window matching the title substring to the foreground."""
        if not PYWIN32_AVAILABLE:
            return False

        windows = cls.list_open_windows()
        for win in windows:
            if title_substring.lower() in win["title"].lower():
                hwnd = win["hwnd"]
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    return True
                except Exception as e:
                    logger.warning(f"Failed to focus window: {e}")
                    return False
        return False
