"""
Windows Application Lifecycle & Window Management Engine
Controls application startup, shutdown, and window manipulation via Win32 APIs and psutil.
"""

import subprocess
import os
import shutil
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
    KNOWN_APP_CANDIDATES = {
        "vs code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            shutil.which("code.cmd"),
            shutil.which("code")
        ],
        "vscode": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            shutil.which("code.cmd"),
            shutil.which("code")
        ],
        "code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            shutil.which("code.cmd"),
            shutil.which("code")
        ],
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            shutil.which("chrome")
        ],
        "google chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            shutil.which("chrome")
        ],
        "edge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            shutil.which("msedge")
        ],
        "msedge": [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "terminal": ["wt.exe", "powershell.exe"],
        "powershell": ["powershell.exe"],
        "cmd": ["cmd.exe"],
        "explorer": ["explorer.exe"],
        "spotify": ["spotify:"]
    }

    @classmethod
    def launch(cls, app_name: str, args: Optional[str] = None) -> Dict[str, Any]:
        """Launches an application interactively using Windows ShellExecute or binary path."""
        clean_name = app_name.lower().strip()
        candidates = cls.KNOWN_APP_CANDIDATES.get(clean_name, [clean_name])

        target = None
        for cand in candidates:
            if cand and (os.path.isabs(cand) and os.path.exists(cand)):
                target = cand
                break
            elif cand and shutil.which(cand):
                target = shutil.which(cand)
                break
            elif cand and cand.endswith(":"):
                target = cand
                break

        if not target:
            target = clean_name

        try:
            if os.name == "nt":
                if args:
                    subprocess.Popen(f'start "" "{target}" {args}', shell=True)
                else:
                    try:
                        os.startfile(target)
                    except Exception:
                        subprocess.Popen(f'start "" "{target}"', shell=True)
            else:
                cmd_list = [target] + ([args] if args else [])
                subprocess.Popen(cmd_list)

            logger.info(f"Launched application '{app_name}' via target '{target}'")
            return {
                "success": True,
                "app_name": app_name,
                "target": target,
                "message": f"Application '{app_name}' launched successfully."
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
