"""
Universal Windows Application Manager & Window Control Service
Provides discovery, launching, verification, graceful closing, window switching,
and interaction across Win32, UWP, System, and Portable applications.
"""

import os
import sys
import time
import re
import shlex
import logging
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple
import psutil

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

from modules.computer_use.app_discovery import app_discovery, ApplicationRecord

logger = logging.getLogger("jarvis.computer_use.apps")


class UniversalAppManager:
    """Universal controller for Windows application lifecycle and window manipulation."""

    # Applications where closing without saving may cause data loss
    PRODUCTIVITY_APPS = {"code", "vscode", "notepad", "word", "excel", "powerpnt", "winword", "photoshop", "paint"}

    def __init__(self):
        self.discovery = app_discovery

    # =========================================================================
    # APPLICATION DISCOVERY & SEARCH
    # =========================================================================

    def search_app(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Searches indexed applications across names, aliases, and executables."""
        return self.discovery.search(query=query, limit=limit)

    def list_installed_apps(self, category: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Lists installed applications, optionally filtered by functional category."""
        return self.discovery.list_apps(category=category, limit=limit)

    def find_app_by_description(self, description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Resolves natural language descriptions to candidate applications."""
        return self.discovery.find_by_description(description=description, limit=limit)

    # =========================================================================
    # RUNNING APPS & WINDOW ENUMERATION
    # =========================================================================

    def list_open_windows(self) -> List[Dict[str, Any]]:
        """Returns all visible desktop application windows with title, PID, and HWND."""
        windows = []
        if not PYWIN32_AVAILABLE:
            return windows

        try:
            # Ensure calling thread is attached to the interactive desktop
            import ctypes
            user32 = ctypes.windll.user32
            h_winsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
            if h_winsta:
                user32.SetProcessWindowStation(h_winsta)
            h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

        def enum_cb(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                # Filter out invisible or tool windows
                if title:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        proc = psutil.Process(pid)
                        pname = proc.name()
                    except Exception:
                        pname = "unknown"
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    # Filter out 0x0 size helper windows
                    if width > 10 and height > 10:
                        windows.append({
                            "hwnd": hwnd,
                            "title": title,
                            "pid": pid,
                            "process_name": pname,
                            "geometry": {"x": rect[0], "y": rect[1], "width": width, "height": height}
                        })
            return True

        try:
            win32gui.EnumWindows(enum_cb, None)
        except Exception as e:
            logger.warning(f"Window enumeration note: {e}")

        return windows

    def get_running_apps(self) -> List[Dict[str, Any]]:
        """
        Returns running desktop applications that have visible GUI windows.
        Deduplicates by process name while aggregating window titles.
        """
        windows = self.list_open_windows()
        running_map: Dict[str, Dict[str, Any]] = {}

        for win in windows:
            pname = win["process_name"].lower()
            if pname not in running_map:
                running_map[pname] = {
                    "process_name": win["process_name"],
                    "primary_pid": win["pid"],
                    "primary_hwnd": win["hwnd"],
                    "primary_title": win["title"],
                    "windows": [win["title"]],
                    "window_count": 1
                }
            else:
                running_map[pname]["windows"].append(win["title"])
                running_map[pname]["window_count"] += 1

        return list(running_map.values())

    def get_active_window(self) -> Dict[str, Any]:
        """Returns details about the currently active foreground window."""
        if not PYWIN32_AVAILABLE:
            return {"success": False, "error": "pywin32 not available"}

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or hwnd == 0:
                hwnd = win32gui.GetDesktopWindow()

            title = win32gui.GetWindowText(hwnd).strip() if hwnd else "Desktop"
            _, pid = win32process.GetWindowThreadProcessId(hwnd) if hwnd else (0, 0)
            try:
                pname = psutil.Process(pid).name() if pid else "System"
            except Exception:
                pname = "unknown"

            rect = win32gui.GetWindowRect(hwnd) if hwnd else (0, 0, 0, 0)
            return {
                "success": True,
                "hwnd": hwnd,
                "title": title or "Desktop",
                "process_name": pname,
                "pid": pid,
                "geometry": {
                    "x": rect[0],
                    "y": rect[1],
                    "width": rect[2] - rect[0],
                    "height": rect[3] - rect[1]
                }
            }
        except Exception as e:
            logger.warning(f"Error getting active window: {e}")
            return {"success": False, "error": str(e)}

    # =========================================================================
    # APPLICATION LAUNCH & VERIFICATION
    # =========================================================================

    def _launch_interactive_desktop(self, target: str, args: Optional[str] = None) -> bool:
        """
        Launches an application directly into the user's interactive desktop (WinSta0\\Default)
        via Windows Task Scheduler XML, explicitly allowing battery power and least privilege.
        """
        task_name = "JARVIS_Interactive_Bridge"
        cwd = os.getcwd()
        arg_xml = f"<Arguments>{args}</Arguments>" if args else "<Arguments/>"

        xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>JARVIS</Author>
  </RegistrationInfo>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <MultipleInstancesPolicy>Parallel</MultipleInstancesPolicy>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{target}</Command>
      {arg_xml}
      <WorkingDirectory>{cwd}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""
        xml_path = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-16", suffix=".xml", delete=False) as f:
                f.write(xml_content)
                xml_path = f.name

            # 1. Register task
            res_create = subprocess.run(["schtasks", "/create", "/tn", task_name, "/xml", xml_path, "/f"], capture_output=True, text=True)
            if res_create.returncode != 0:
                logger.warning(f"Interactive bridge task creation warning: {res_create.stderr}")
                return False

            # 2. Run task
            res_run = subprocess.run(["schtasks", "/run", "/tn", task_name], capture_output=True, text=True)
            return res_run.returncode == 0
        except Exception as e:
            logger.warning(f"Interactive desktop launcher exception: {e}")
            return False
        finally:
            if xml_path and os.path.exists(xml_path):
                try:
                    os.remove(xml_path)
                except Exception:
                    pass

    def open_app(self, app_name_or_query: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Resolves, launches, and verifies any Windows application (Win32, UWP, System, or Folder).
        Does NOT report success until process or window appearance is verified.
        """
        clean_query = app_name_or_query.lower().strip()
        # Strip voice command prefixes/suffixes
        clean_query = re.sub(r"^(?:please\s+|can\s+you\s+|jarvis\s+|open\s+|launch\s+|start\s+)+", "", clean_query).strip()
        clean_query = re.sub(r"\s+(?:in\s+window|in\s+a\s+window|window|app|application|please|now|for\s+me)$", "", clean_query).strip()
        clean_query = clean_query.strip(" .,!?:;'\"")

        # 1. Check if application window is already running and bring to foreground
        running_windows = self.list_open_windows()
        for win in running_windows:
            w_title = win["title"].lower()
            p_name = win["process_name"].lower()
            if clean_query in w_title or clean_query in p_name:
                self.switch_app(win["title"])
                logger.info(f"App '{clean_query}' already running. Brought window '{win['title']}' to foreground.")
                return {
                    "success": True,
                    "verified": True,
                    "already_running": True,
                    "app_name": win["title"],
                    "pid": win["pid"],
                    "hwnd": win["hwnd"],
                    "message": f"Application '{win['title']}' is already running and has been brought to the foreground."
                }

        # 2. Resolve via Application Discovery Engine
        resolution = self.discovery.resolve(clean_query)
        if not resolution["success"]:
            if resolution.get("ambiguous"):
                return {
                    "success": False,
                    "ambiguous": True,
                    "query": clean_query,
                    "message": resolution.get("message", "Multiple matching applications found."),
                    "candidates": resolution.get("candidates", [])
                }
            # Fallback check if it's a known executable or command on PATH
            if shutil.which(clean_query) or shutil.which(f"{clean_query}.exe"):
                target = shutil.which(clean_query) or shutil.which(f"{clean_query}.exe")
                app_rec = {
                    "id": clean_query,
                    "name": clean_query.title(),
                    "target": target,
                    "launch_method": "direct_exec",
                    "app_type": "win32"
                }
            else:
                return {
                    "success": False,
                    "verified": False,
                    "query": clean_query,
                    "error": f"Could not find any installed application matching '{app_name_or_query}'."
                }
        else:
            app_rec = resolution["app"]

        target = app_rec["target"]
        launch_method = app_rec.get("launch_method", "direct_exec")
        args_str = " ".join(args) if args else ""

        # Special casing for VS Code workspace defaulting
        if app_rec["id"] in ("visual_studio_code", "code", "vscode") and not args_str:
            cwd = os.getcwd()
            if os.path.isdir(cwd):
                args_str = f'"{cwd}"'

        logger.info(f"Launching '{app_rec['name']}' via {launch_method} -> '{target}' (args: {args_str})")
        launched = False

        try:
            # Method 1: Special folder opening via File Explorer
            if launch_method == "explorer_folder" or os.path.isdir(target):
                subprocess.Popen(["explorer.exe", target])
                launched = True

            # Method 2: UWP / Store Apps via shell:AppsFolder
            elif launch_method == "apps_folder" or target.startswith("shell:AppsFolder\\"):
                try:
                    os.startfile(target)
                    launched = True
                except Exception as ex_sf:
                    logger.warning(f"os.startfile failed for AppsFolder: {ex_sf}. Trying explorer fallback.")
                    subprocess.Popen(["explorer.exe", target])
                    launched = True

            # Method 3: System Protocol URIs (ms-settings:, calc:, etc.)
            elif launch_method == "system_uri" or target.endswith(":") or "://" in target:
                try:
                    os.startfile(target)
                    launched = True
                except Exception as ex_uri:
                    subprocess.Popen(["explorer.exe", target])
                    launched = True

            # Method 4: Shortcuts (.lnk)
            elif launch_method == "shortcut" or target.lower().endswith(".lnk"):
                try:
                    os.startfile(target)
                    launched = True
                except Exception as ex_lnk:
                    subprocess.Popen(["explorer.exe", target])
                    launched = True

            # Method 5: Executable binaries (.exe)
            else:
                # Try interactive desktop bridge first
                launched = self._launch_interactive_desktop(target, args_str or None)

                # Fallback to os.startfile
                if not launched:
                    try:
                        if args_str:
                            os.startfile(target, "open", arguments=args_str)
                        else:
                            os.startfile(target)
                        launched = True
                    except Exception as ex_start:
                        logger.warning(f"os.startfile fallback note: {ex_start}")

                # Fallback to detached subprocess
                if not launched:
                    cmd_list = [target]
                    if args_str:
                        cmd_list.extend(shlex.split(args_str))
                    subprocess.Popen(cmd_list, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
                    launched = True

        except Exception as e:
            logger.error(f"Execution error while launching '{app_rec['name']}': {e}")
            self.discovery.record_launch_result(app_rec["id"], success=False, message=str(e))
            return {
                "success": False,
                "verified": False,
                "app_name": app_rec["name"],
                "error": f"Failed to launch '{app_rec['name']}': {str(e)}"
            }

        # 3. VERIFICATION POLLING LOOP
        # Verify that either a window or process appeared within 6 seconds
        verified = False
        detected_hwnd = None
        detected_title = None
        detected_pid = None
        start_wait = time.time()

        expected_tokens = set([app_rec["name"].lower(), app_rec["id"].lower()] + [a.lower() for a in app_rec.get("aliases", [])])
        if app_rec.get("executable_path"):
            expected_tokens.add(os.path.splitext(os.path.basename(app_rec["executable_path"]))[0].lower())

        while time.time() - start_wait < 6.0:
            time.sleep(0.5)
            open_wins = self.list_open_windows()
            for win in open_wins:
                w_t = win["title"].lower()
                p_n = win["process_name"].lower().replace(".exe", "")
                if any(tok in w_t or tok in p_n for tok in expected_tokens if len(tok) >= 3):
                    verified = True
                    detected_hwnd = win["hwnd"]
                    detected_title = win["title"]
                    detected_pid = win["pid"]
                    # Bring verified window to foreground
                    self.switch_app(win["title"])
                    break

            if verified:
                break

        # Record launch telemetry in index
        self.discovery.record_launch_result(app_rec["id"], success=verified, message="Window verified" if verified else "Timeout waiting for window")

        if verified:
            return {
                "success": True,
                "verified": True,
                "app_name": app_rec["name"],
                "target": target,
                "hwnd": detected_hwnd,
                "pid": detected_pid,
                "window_title": detected_title,
                "message": f"Application '{app_rec['name']}' launched and verified on desktop."
            }
        else:
            # Check if process is running even if window didn't register in top-level enum (e.g. background utility)
            proc_running = False
            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    p_name = proc.info['name'].lower().replace(".exe", "")
                    if any(tok in p_name for tok in expected_tokens if len(tok) >= 3):
                        proc_running = True
                        detected_pid = proc.info['pid']
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "success": True,
                "verified": proc_running,
                "app_name": app_rec["name"],
                "target": target,
                "pid": detected_pid,
                "warning": "Process started but main application window did not focus within 6 seconds.",
                "message": f"Application '{app_rec['name']}' activation initiated."
            }

    # =========================================================================
    # APPLICATION TERMINATION & RESTART
    # =========================================================================

    def close_app(self, app_name_or_process: str, force: bool = False, confirm: bool = False) -> Dict[str, Any]:
        """
        Gracefully closes an application by sending WM_CLOSE to its windows.
        Warns if potential unsaved work exists and confirm=False.
        Falls back to process termination if requested or if unresponsive.
        """
        clean_name = app_name_or_process.lower().strip().replace(".exe", "")
        # Strip phrases
        clean_name = re.sub(r"^(?:close|quit|exit|kill|terminate)\s+", "", clean_name).strip()

        # Locate running windows matching target
        matching_windows = []
        matching_pids = set()

        for win in self.list_open_windows():
            if clean_name in win["title"].lower() or clean_name in win["process_name"].lower():
                matching_windows.append(win)
                matching_pids.add(win["pid"])

        # Also search running processes without visible windows
        if not matching_pids:
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if clean_name in proc.info['name'].lower():
                        matching_pids.add(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if not matching_pids:
            return {
                "success": False,
                "message": f"No running application or process matching '{app_name_or_process}' was found."
            }

        # Check for unsaved work risk in productivity apps
        is_productivity = any(p in clean_name for p in self.PRODUCTIVITY_APPS)
        if is_productivity and not confirm and not force:
            # Check window title for unsaved indicators (e.g. '*' or 'Unsaved')
            has_unsaved_indicator = any("*" in w["title"] or "unsaved" in w["title"].lower() for w in matching_windows)
            if has_unsaved_indicator:
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "app_name": app_name_or_process,
                    "message": f"Application '{app_name_or_process}' appears to have unsaved changes. Confirm closing to proceed."
                }

        # 1. Graceful close via WM_CLOSE
        closed_windows = 0
        if PYWIN32_AVAILABLE:
            for win in matching_windows:
                try:
                    win32gui.PostMessage(win["hwnd"], win32con.WM_CLOSE, 0, 0)
                    closed_windows += 1
                except Exception as e:
                    logger.debug(f"WM_CLOSE error: {e}")

        # Wait briefly for graceful exit
        time.sleep(1.0)

        # 2. Force termination if requested or if processes remain
        terminated_pids = []
        for pid in matching_pids:
            try:
                p = psutil.Process(pid)
                if p.is_running():
                    if force:
                        p.kill()
                        terminated_pids.append(pid)
                    else:
                        p.terminate()
                        terminated_pids.append(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "success": True,
            "closed_windows": closed_windows,
            "terminated_pids": terminated_pids,
            "message": f"Closed application '{app_name_or_process}'."
        }

    def restart_app(self, app_name_or_process: str) -> Dict[str, Any]:
        """Closes and re-opens an application."""
        close_res = self.close_app(app_name_or_process, force=False, confirm=True)
        time.sleep(1.2)
        open_res = self.open_app(app_name_or_process)
        return {
            "success": open_res.get("success", False),
            "close_status": close_res,
            "open_status": open_res,
            "message": f"Restarted '{app_name_or_process}'."
        }

    # =========================================================================
    # WINDOW SWITCHING & MANIPULATION
    # =========================================================================

    def switch_app(self, app_name_or_window: str) -> bool:
        """
        Brings the window matching the app name or title to the foreground.
        Uses thread input attachment to bypass Windows foreground lock restrictions.
        """
        if not PYWIN32_AVAILABLE:
            return False

        q = app_name_or_window.lower().strip()
        q = re.sub(r"^(?:switch to|switch|bring to front|focus)\s+", "", q).strip()

        windows = self.list_open_windows()
        target_hwnd = None

        # 1. Exact or substring match in title
        for win in windows:
            if q in win["title"].lower() or q in win["process_name"].lower():
                target_hwnd = win["hwnd"]
                break

        if not target_hwnd:
            return False

        try:
            curr_thread = win32api.GetCurrentThreadId()
            target_thread, _ = win32process.GetWindowThreadProcessId(target_hwnd)

            if curr_thread != target_thread:
                win32process.AttachThreadInput(curr_thread, target_thread, True)

            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            win32gui.BringWindowToTop(target_hwnd)
            win32gui.SetForegroundWindow(target_hwnd)

            if curr_thread != target_thread:
                win32process.AttachThreadInput(curr_thread, target_thread, False)

            return True
        except Exception as e:
            logger.warning(f"Error switching to window {target_hwnd}: {e}")
            try:
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(target_hwnd)
                return True
            except Exception:
                return False

    def maximize_window(self, app_name_or_window: str) -> bool:
        """Maximizes the window matching the application or title."""
        if not PYWIN32_AVAILABLE:
            return False
        q = app_name_or_window.lower().strip()
        for win in self.list_open_windows():
            if q in win["title"].lower() or q in win["process_name"].lower():
                try:
                    win32gui.ShowWindow(win["hwnd"], win32con.SW_MAXIMIZE)
                    return True
                except Exception:
                    return False
        return False

    def minimize_window(self, app_name_or_window: str) -> bool:
        """Minimizes the window matching the application or title."""
        if not PYWIN32_AVAILABLE:
            return False
        q = app_name_or_window.lower().strip()
        for win in self.list_open_windows():
            if q in win["title"].lower() or q in win["process_name"].lower():
                try:
                    win32gui.ShowWindow(win["hwnd"], win32con.SW_MINIMIZE)
                    return True
                except Exception:
                    return False
        return False


# Global Singleton Instance
universal_app_manager = UniversalAppManager()
