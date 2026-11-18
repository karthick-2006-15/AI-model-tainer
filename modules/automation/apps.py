"""
Windows Application Lifecycle & Window Management Engine
Controls application startup, shutdown, and window manipulation via Win32 APIs and psutil.
"""

import subprocess
import os
import shutil
import logging
import time
import json
from typing import List, Dict, Any, Optional
import psutil

# Safe import of pywin32
try:
    import win32gui
    import win32con
    import win32process
    import win32api
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

logger = logging.getLogger("jarvis.automation.apps")


class ApplicationManager:
    # Dynamic catalog cache for Get-StartApps
    _START_APPS_CACHE: Optional[List[Dict[str, str]]] = None
    _START_APPS_CACHE_TIME: float = 0

    WINDOW_TITLE_MAP = {
        "vs code": ["Visual Studio Code", "Code"],
        "vscode": ["Visual Studio Code", "Code"],
        "code": ["Visual Studio Code", "Code"],
        "visual studio code": ["Visual Studio Code", "Code"],
        "whatsapp": ["WhatsApp"],
        "spotify": ["Spotify", "Spotify Premium", "Spotify Free"],
        "chrome": ["Google Chrome", "Chrome"],
        "google chrome": ["Google Chrome", "Chrome"],
        "browser": ["Google Chrome", "Edge"],
        "edge": ["Microsoft Edge", "Edge"],
        "msedge": ["Microsoft Edge", "Edge"],
        "notepad": ["Notepad"],
        "notes": ["Notepad"],
        "calculator": ["Calculator"],
        "calc": ["Calculator"],
        "settings": ["Settings"],
        "camera": ["Camera"],
        "paint": ["Paint"],
        "clock": ["Clock", "Alarms & Clock"],
        "timer": ["Clock", "Alarms & Clock"],
        "excel": ["Excel"],
        "word": ["Word"],
        "powerpoint": ["PowerPoint"],
        "ppt": ["PowerPoint"],
        "chatgpt": ["ChatGPT"],
        "claude": ["Claude"],
        "canva": ["Canva"],
        "capcut": ["CapCut"],
        "explorer": ["File Explorer", "Explorer"],
        "file explorer": ["File Explorer", "Explorer"],
        "files": ["File Explorer", "Explorer"],
        "terminal": ["Terminal", "PowerShell", "Command Prompt"],
        "powershell": ["PowerShell"],
        "cmd": ["Command Prompt"],
        "task manager": ["Task Manager"],
        "control panel": ["Control Panel"],
        "vlc": ["VLC media player", "VLC"],
        "discord": ["Discord"],
        "telegram": ["Telegram"],
        "slack": ["Slack"],
        "steam": ["Steam"],
        "whatsapp": ["WhatsApp"],
    }

    KNOWN_APP_CANDIDATES = {
        "whatsapp": [
            "whatsapp:",
            r"shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
            os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe")
        ],
        "vs code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            r"shell:AppsFolder\Microsoft.VisualStudioCode",
            shutil.which("code.cmd"),
            shutil.which("code")
        ],
        "vscode": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            r"shell:AppsFolder\Microsoft.VisualStudioCode",
            shutil.which("code.cmd"),
            shutil.which("code")
        ],
        "code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            r"shell:AppsFolder\Microsoft.VisualStudioCode",
            shutil.which("code.cmd"),
            shutil.which("code")
        ],
        "visual studio code": [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
            r"C:\Program Files\Microsoft VS Code\Code.exe",
            r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
            r"shell:AppsFolder\Microsoft.VisualStudioCode",
            shutil.which("code.cmd"),
            shutil.which("code")
        ],
        "spotify": [
            os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
            "spotify:",
            r"shell:AppsFolder\Chrome._crx_pjibgcllelbfgfagdaldikeohf"
        ],
        "chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            r"shell:AppsFolder\Chrome",
            shutil.which("chrome")
        ],
        "google chrome": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            r"shell:AppsFolder\Chrome",
            shutil.which("chrome")
        ],
        "browser": [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "chrome.exe",
            "msedge.exe"
        ],
        "edge": [
            "microsoft-edge:",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "msedge.exe",
            r"shell:AppsFolder\Microsoft.MicrosoftEdge.Stable_8wekyb3d8bbwe!App"
        ],
        "msedge": [
            "microsoft-edge:",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "msedge.exe"
        ],
        "notepad": [
            "notepad.exe",
            r"shell:AppsFolder\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"
        ],
        "notes": [
            "notepad.exe",
            r"shell:AppsFolder\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"
        ],
        "calculator": [
            "calc.exe",
            "calculator:",
            r"shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"
        ],
        "calc": [
            "calc.exe",
            "calculator:",
            r"shell:AppsFolder\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App"
        ],
        "camera": [
            "microsoft.windows.camera:",
            r"shell:AppsFolder\Microsoft.WindowsCamera_8wekyb3d8bbwe!App"
        ],
        "settings": [
            "ms-settings:",
            r"shell:AppsFolder\windows.immersivecontrolpanel_cw5n1h2txyewy!microsoft.windows.immersivecontrolpanel"
        ],
        "paint": [
            "mspaint.exe",
            "ms-paint:",
            r"shell:AppsFolder\Microsoft.Paint_8wekyb3d8bbwe!App"
        ],
        "clock": [
            "ms-clock:",
            r"shell:AppsFolder\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"
        ],
        "timer": [
            "ms-clock:",
            r"shell:AppsFolder\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"
        ],
        "terminal": [
            "wt.exe",
            "powershell.exe",
            "cmd.exe"
        ],
        "powershell": [
            "powershell.exe"
        ],
        "cmd": [
            "cmd.exe"
        ],
        "command prompt": [
            "cmd.exe"
        ],
        "explorer": [
            "explorer.exe"
        ],
        "file explorer": [
            "explorer.exe"
        ],
        "files": [
            "explorer.exe"
        ],
        "task manager": [
            "taskmgr.exe"
        ],
        "taskmgr": [
            "taskmgr.exe"
        ],
        "control panel": [
            "control.exe"
        ],
        "excel": [
            "excel.exe",
            r"shell:AppsFolder\Microsoft.Office.EXCEL.EXE.15",
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\EXCEL.EXE"
        ],
        "word": [
            "winword.exe",
            r"shell:AppsFolder\Microsoft.Office.WINWORD.EXE.15",
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\WINWORD.EXE"
        ],
        "powerpoint": [
            "powerpnt.exe",
            r"shell:AppsFolder\Microsoft.Office.POWERPNT.EXE.15",
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            r"C:\Program Files (x86)\Microsoft Office\root\Office16\POWERPNT.EXE"
        ],
        "ppt": [
            "powerpnt.exe",
            r"shell:AppsFolder\Microsoft.Office.POWERPNT.EXE.15",
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE"
        ],
        "chatgpt": [
            r"shell:AppsFolder\OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0!ChatGPT"
        ],
        "claude": [
            r"shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude"
        ],
        "canva": [
            r"shell:AppsFolder\com.canva.CanvaDesktop"
        ],
        "capcut": [
            os.path.expandvars(r"%LOCALAPPDATA%\CapCut\Apps\8.1.1.3417\capcut.exe")
        ],
        "utorrent": [
            os.path.expandvars(r"%APPDATA%\utorrent\uTorrent.exe")
        ],
        "vlc": [
            "vlc.exe",
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
        ],
        "discord": [
            "discord:",
            os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe")
        ],
        "telegram": [
            "telegram:",
            "telegram.exe"
        ],
        "slack": [
            "slack:",
            "slack.exe"
        ],
        "steam": [
            "steam:",
            "steam.exe"
        ],
        "zoom": [
            "zoom:",
            "zoom.exe"
        ],
        "store": [
            "ms-windows-store:"
        ],
        "microsoft store": [
            "ms-windows-store:"
        ]
    }

    @classmethod
    def _get_start_apps_catalog(cls) -> List[Dict[str, str]]:
        """Queries and caches installed Windows applications via Get-StartApps."""
        now = time.time()
        if cls._START_APPS_CACHE is not None and (now - cls._START_APPS_CACHE_TIME) < 600:
            return cls._START_APPS_CACHE
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json"],
                capture_output=True,
                text=True,
                timeout=6
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                cls._START_APPS_CACHE = data
                cls._START_APPS_CACHE_TIME = now
                return data
        except Exception as e:
            logger.warning(f"Failed to query Get-StartApps: {e}")
        return cls._START_APPS_CACHE or []

    @classmethod
    def _find_start_menu_shortcut(cls, query: str) -> Optional[str]:
        """Searches Start Menu directories for .lnk shortcuts matching query."""
        search_dirs = [
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
        ]
        q = query.lower().strip()
        contains_match = None

        for base in search_dirs:
            if not os.path.exists(base):
                continue
            for root, _, files in os.walk(base):
                for f in files:
                    if not f.lower().endswith(".lnk"):
                        continue
                    name_without_ext = f[:-4].lower()
                    full_path = os.path.join(root, f)
                    if name_without_ext == q:
                        return full_path
                    elif q in name_without_ext and not contains_match:
                        contains_match = full_path

        return contains_match

    @classmethod
    def _resolve_app_candidate(cls, clean_name: str) -> Optional[str]:
        """Resolves an application name to an executable path, protocol URI, or shell:AppsFolder AppID."""
        # 1. Check preconfigured candidates
        candidates = cls.KNOWN_APP_CANDIDATES.get(clean_name)
        if candidates:
            for cand in candidates:
                if not cand:
                    continue
                if cand.startswith("shell:AppsFolder\\"):
                    return cand
                if cand.endswith(":") or "://" in cand:
                    return cand
                if os.path.isabs(cand) and os.path.exists(cand):
                    return cand
                if shutil.which(cand):
                    return shutil.which(cand)

        # 2. Check Start Menu .lnk shortcuts
        lnk_path = cls._find_start_menu_shortcut(clean_name)
        if lnk_path:
            return lnk_path

        # 3. Dynamic lookup in Windows StartApps catalog (UWP, Store, Desktop apps)
        catalog = cls._get_start_apps_catalog()
        q = clean_name.lower().strip()

        # 3a. Exact match
        for app in catalog:
            if app.get("Name", "").lower() == q:
                app_id = app.get("AppID", "")
                if os.path.isabs(app_id) and os.path.exists(app_id):
                    return app_id
                if app_id.endswith(":") or "://" in app_id:
                    return app_id
                return f"shell:AppsFolder\\{app_id}"

        # 3b. Word boundary / prefix match
        for app in catalog:
            name = app.get("Name", "").lower()
            if name.startswith(q) or f" {q}" in name:
                app_id = app.get("AppID", "")
                if os.path.isabs(app_id) and os.path.exists(app_id):
                    return app_id
                if app_id.endswith(":") or "://" in app_id:
                    return app_id
                return f"shell:AppsFolder\\{app_id}"

        # 3c. Substring match
        for app in catalog:
            name = app.get("Name", "").lower()
            if q in name or name in q:
                app_id = app.get("AppID", "")
                if os.path.isabs(app_id) and os.path.exists(app_id):
                    return app_id
                if app_id.endswith(":") or "://" in app_id:
                    return app_id
                return f"shell:AppsFolder\\{app_id}"

        # 4. Check system PATH
        if shutil.which(clean_name):
            return shutil.which(clean_name)
        if shutil.which(clean_name + ".exe"):
            return shutil.which(clean_name + ".exe")

        return None

    @classmethod
    def launch(cls, app_name: str, args: Optional[str] = None) -> Dict[str, Any]:
        """Launches or focuses an application interactively across Win32, UWP, and protocol apps."""
        import re
        import shlex
        import time

        clean_name = app_name.lower().strip()
        # Strip conversational modifiers
        clean_name = re.sub(r"\s+(?:in\s+window|in\s+a\s+window|window|app|application|please|now|for\s+me)$", "", clean_name).strip()
        clean_name = re.sub(r"^(?:the\s+)", "", clean_name).strip()
        clean_name = clean_name.strip(" .,!?:;'\"")

        # 1. Check if application window is already running and bring it to foreground
        title_candidates = cls.WINDOW_TITLE_MAP.get(clean_name, [clean_name])
        for t_cand in title_candidates:
            if cls.focus_window(t_cand):
                logger.info(f"Application '{clean_name}' already open. Brought to foreground.")
                return {
                    "success": True,
                    "app_name": app_name,
                    "target": "active_window",
                    "message": f"Application '{app_name}' is already running and has been brought to the foreground."
                }

        # 2. Resolve application candidate
        target = cls._resolve_app_candidate(clean_name)
        if not target:
            target = clean_name

        # If launching VS Code without explicit arguments, default to current workspace
        effective_args = args
        if not effective_args and clean_name in ("vs code", "vscode", "code", "visual studio code"):
            cwd = os.getcwd()
            if os.path.isdir(cwd):
                effective_args = f'"{cwd}"'
            else:
                effective_args = "--new-window"

        try:
            if os.name == "nt":
                launched = False

                # Handle shell:AppsFolder / UWP Apps (e.g. WhatsApp, Calculator, Settings, Canva, ChatGPT)
                if target.startswith("shell:AppsFolder\\"):
                    try:
                        os.startfile(target)
                        launched = True
                    except Exception as ex_start:
                        logger.warning(f"os.startfile failed for '{target}': {ex_start}. Trying explorer fallback.")
                        subprocess.Popen(["explorer.exe", target])
                        launched = True

                # Handle Protocol URIs (e.g. whatsapp:, spotify:, ms-settings:, calc:)
                elif target.endswith(":") or "://" in target:
                    try:
                        os.startfile(target)
                        launched = True
                    except Exception as ex_proto:
                        logger.warning(f"os.startfile failed for protocol '{target}': {ex_proto}. Trying explorer fallback.")
                        subprocess.Popen(["explorer.exe", target])
                        launched = True

                # Handle .lnk shortcuts
                elif target.lower().endswith(".lnk"):
                    try:
                        os.startfile(target)
                        launched = True
                    except Exception as ex_lnk:
                        logger.warning(f"os.startfile failed for lnk '{target}': {ex_lnk}.")
                        subprocess.Popen(["explorer.exe", target])
                        launched = True

                # Handle Executable files (.exe)
                elif target.lower().endswith(".exe") or (shutil.which(target) and not target.endswith(":")):
                    # Method A: Interactive Desktop Bridge via Windows Task Scheduler XML
                    launched = cls._launch_interactive_desktop(target, effective_args)

                    # Method B: os.startfile fallback
                    if not launched:
                        try:
                            if effective_args:
                                os.startfile(target, "open", arguments=effective_args)
                            else:
                                os.startfile(target)
                            launched = True
                        except Exception as ex_start:
                            logger.warning(f"os.startfile failed for '{target}': {ex_start}. Trying detached process.")

                    # Method C: Detached Subprocess
                    if not launched:
                        try:
                            cmd_list = [target]
                            if effective_args:
                                cmd_list.extend(shlex.split(effective_args))
                            subprocess.Popen(cmd_list, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
                            launched = True
                        except Exception as ex_sub:
                            logger.warning(f"subprocess fallback failed for '{target}': {ex_sub}.")

                # Generic Fallback: explorer.exe
                if not launched:
                    try:
                        subprocess.Popen(["explorer.exe", target])
                        launched = True
                    except Exception as ex_exp:
                        logger.error(f"Explorer fallback failed for '{target}': {ex_exp}")
                        return {
                            "success": False,
                            "error": f"Could not launch application '{app_name}'. Target: {target}"
                        }

                # Attempt focus after launch
                time.sleep(0.6)
                for t_cand in title_candidates:
                    if cls.focus_window(t_cand):
                        break

            else:
                cmd_list = [target] + ([effective_args] if effective_args else [])
                subprocess.Popen(cmd_list)

            logger.info(f"Launched application '{app_name}' via target '{target}' (args: {effective_args})")
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
    def _launch_interactive_desktop(cls, target: str, args: Optional[str] = None) -> bool:
        """Launches an application directly onto the interactive user desktop (WinSta0\\Default).
        Uses Windows Task Scheduler XML to bridge session boundaries and explicitly allow battery execution.
        """
        import tempfile
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

            # 1. Register task with battery and interactive token permissions
            res_create = subprocess.run(["schtasks", "/create", "/tn", task_name, "/xml", xml_path, "/f"], capture_output=True, text=True)
            if res_create.returncode != 0:
                logger.warning(f"Failed to create interactive task: {res_create.stderr}")
                return False

            # 2. Run task in the user's interactive session
            res_run = subprocess.run(["schtasks", "/run", "/tn", task_name], capture_output=True, text=True)
            return res_run.returncode == 0
        except Exception as e:
            logger.warning(f"_launch_interactive_desktop exception: {e}")
            return False
        finally:
            if xml_path and os.path.exists(xml_path):
                try:
                    os.remove(xml_path)
                except Exception:
                    pass

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
        """Returns all visible desktop application windows across the interactive user desktop."""
        windows = []
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            h_winsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
            if h_winsta:
                user32.SetProcessWindowStation(h_winsta)
            h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_desk:
                user32.SetThreadDesktop(h_desk)

            WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

            def enum_cb(hwnd, lparam):
                try:
                    if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
                        length = user32.GetWindowTextLengthW(hwnd)
                        if length > 0:
                            buff = ctypes.create_unicode_buffer(length + 1)
                            user32.GetWindowTextW(hwnd, buff, length + 1)
                            title = buff.value.strip()
                            if title and title not in ("Default IME", "MSCTFIME UI", "Program Manager"):
                                pid = wintypes.DWORD()
                                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                                try:
                                    pname = psutil.Process(pid.value).name()
                                except Exception:
                                    pname = "unknown"
                                windows.append({
                                    "hwnd": hwnd,
                                    "title": title,
                                    "pid": pid.value,
                                    "process_name": pname,
                                    "is_visible": bool(user32.IsWindowVisible(hwnd))
                                })
                except Exception:
                    pass
                return True

            user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
        except Exception as e:
            logger.warning(f"Error enumerating windows: {e}")

        return windows

    @classmethod
    def _force_window_foreground(cls, hwnd: int) -> bool:
        """Forces a window into the active foreground using thread input attachment, TopMost cycling, and Win32 APIs."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            if not user32.IsWindow(hwnd):
                return False

            # Unlock Windows foreground lock timeout
            try:
                user32.SystemParametersInfoW(0x2001, 0, 0, 0x0002)  # SPI_SETFOREGROUNDLOCKTIMEOUT = 0
                user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
            except Exception:
                pass

            if user32.IsIconic(hwnd):
                user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            user32.ShowWindow(hwnd, 5)  # SW_SHOW

            fg_hwnd = user32.GetForegroundWindow()
            if fg_hwnd == hwnd:
                return True

            fg_thread_id = user32.GetWindowThreadProcessId(fg_hwnd, None)
            cur_thread_id = kernel32.GetCurrentThreadId()

            attached = False
            if fg_thread_id != 0 and fg_thread_id != cur_thread_id:
                attached = bool(user32.AttachThreadInput(cur_thread_id, fg_thread_id, True))

            try:
                # Alt key press trick to unlock Windows foreground lock
                user32.keybd_event(0x12, 0, 0, 0)
                user32.BringWindowToTop(hwnd)
                # Toggle TOPMOST to bring in front of full-screen IDEs/windows
                user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)  # HWND_TOPMOST
                user32.SetWindowPos(hwnd, -2, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)  # HWND_NOTOPMOST | SWP_SHOWWINDOW
                user32.SetForegroundWindow(hwnd)
                user32.SwitchToThisWindow(hwnd, True)
                user32.keybd_event(0x12, 0, 2, 0)
            finally:
                if attached:
                    user32.AttachThreadInput(cur_thread_id, fg_thread_id, False)

            time.sleep(0.2)
            return user32.GetForegroundWindow() == hwnd
        except Exception as e:
            logger.warning(f"Error in _force_window_foreground for hwnd {hwnd}: {e}")
            return False

    @classmethod
    def focus_window(cls, title_substring: str) -> bool:
        """Brings the window matching the title substring or process to the foreground with verification."""
        if not PYWIN32_AVAILABLE:
            return False

        q = title_substring.lower().strip()
        windows = cls.list_open_windows()
        if not windows:
            return False

        # Rank candidates: prioritize dedicated native process matches over browser tabs
        def match_score(w: Dict[str, Any]) -> int:
            pname = w.get("process_name", "").lower()
            title = w.get("title", "").lower()

            # Exact process match or process starting with query (e.g. whatsapp.root.exe)
            if pname.startswith(q) or q in pname:
                if title == q:
                    return 100
                return 80
            if title == q:
                return 70
            if title.startswith(q):
                return 60
            if q in title:
                # Deprioritize browser tabs (msedge, chrome) if looking for standalone apps
                if any(b in pname for b in ["msedge", "chrome", "firefox", "brave"]):
                    return 30
                return 50
            return 0

        scored = [(match_score(w), w) for w in windows]
        scored = [item for item in scored if item[0] > 0]
        scored.sort(key=lambda x: x[0], reverse=True)

        for score, win in scored:
            hwnd = win["hwnd"]
            if cls._force_window_foreground(hwnd):
                logger.info(f"Focused window '{win.get('title')}' (PID: {win.get('pid')}) with score {score}")
                return True

        return False
