"""
Universal Windows Application Discovery Engine
Dynamically discovers Win32, UWP/Store, System, Portable, and Alias applications
across Start Menu shortcuts, Windows Registry, App Paths, UWP Packages, WindowsApps,
and System directories without hardcoded application lists.
"""

import os
import sys
import re
import json
import time
import shutil
import logging
import subprocess
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, asdict, field

# Safe import of winreg
try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False

logger = logging.getLogger("jarvis.computer_use.discovery")


@dataclass
class ApplicationRecord:
    id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    target: str = ""
    app_type: str = "win32"  # win32, uwp, system, portable, alias, protocol, folder
    launch_method: str = "direct_exec"  # direct_exec, apps_folder, system_uri, shortcut, explorer_folder
    source: str = "unknown"  # start_menu, registry, app_paths, uwp_package, app_alias, system, folder
    install_location: Optional[str] = None
    executable_path: Optional[str] = None
    description: str = ""
    categories: List[str] = field(default_factory=list)
    last_launch_status: Dict[str, Any] = field(default_factory=lambda: {"last_launch": None, "success_count": 0, "failure_count": 0})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AppDiscoveryEngine:
    """Discovers and indexes all applications installed across Windows 11."""

    # Default well-known category mappings based on keywords in name/description
    CATEGORY_KEYWORDS = {
        "browser": ["browser", "chrome", "edge", "firefox", "brave", "opera", "safari", "vivaldi", "internet", "web"],
        "development": ["visual studio", "vscode", "code", "python", "pycharm", "git", "terminal", "sublime", "intellij", "debugger", "ide", "compiler", "powershell", "node"],
        "media": ["music", "audio", "video", "media", "spotify", "vlc", "player", "sound", "groove", "podcast", "stream"],
        "productivity": ["word", "excel", "powerpoint", "office", "notes", "notepad", "onenote", "document", "sheet", "slide", "pdf", "reader", "writer", "calc"],
        "design": ["photoshop", "illustrator", "paint", "canva", "gimp", "blender", "photo", "image", "draw", "cad", "figma"],
        "communication": ["whatsapp", "telegram", "slack", "discord", "teams", "zoom", "skype", "chat", "message", "email", "outlook", "mail"],
        "system": ["settings", "task manager", "control panel", "terminal", "command prompt", "regedit", "utility", "explorer", "backup", "cleanup", "device manager"],
        "utility": ["calculator", "camera", "clock", "timer", "calendar", "weather", "alarm", "store", "winrar", "7-zip", "zip", "torrent"]
    }

    def __init__(self, cache_file: Optional[str] = None):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if cache_file:
            self.cache_file = cache_file
        else:
            cache_dir = os.path.join(self.project_root, "storage", "cache")
            os.makedirs(cache_dir, exist_ok=True)
            self.cache_file = os.path.join(cache_dir, "app_index.json")

        self._index: Dict[str, ApplicationRecord] = {}
        self._last_refresh_time: float = 0
        self._load_cached_index()

    def _normalize_id(self, name: str) -> str:
        """Generates a stable normalized ID from a display name."""
        clean = re.sub(r"[^\w\s-]", "", name.lower())
        clean = re.sub(r"[\s-]+", "_", clean).strip("_")
        return clean or "unknown_app"

    def _generate_aliases(self, name: str, exe_name: Optional[str] = None) -> List[str]:
        """Generates search aliases for an application."""
        aliases = set()
        clean = name.lower().strip()
        aliases.add(clean)

        # Remove common branding / suffixes
        stripped = re.sub(r"\s+\((?:64-bit|32-bit|x64|x86)\)$", "", clean, flags=re.I)
        stripped = re.sub(r"\s+(?:desktop|application|app|preview|edition|professional|community|lts|classic)$", "", stripped, flags=re.I)
        if stripped != clean:
            aliases.add(stripped.strip())

        # Acronyms (e.g. Visual Studio Code -> vsc, vscode)
        words = clean.split()
        if len(words) > 1:
            acronym = "".join(w[0] for w in words if w)
            if len(acronym) >= 2:
                aliases.add(acronym)
            no_spaces = "".join(words)
            aliases.add(no_spaces)

        # If executable provided
        if exe_name:
            exe_clean = os.path.splitext(os.path.basename(exe_name))[0].lower()
            aliases.add(exe_clean)

        return sorted(list(aliases))

    def _infer_categories(self, name: str, description: str = "") -> List[str]:
        """Infers category tags from name and description."""
        combined = f"{name} {description}".lower()
        cats = []
        for cat, kw_list in self.CATEGORY_KEYWORDS.items():
            for kw in kw_list:
                if re.search(r"\b" + re.escape(kw) + r"\b", combined):
                    if cat not in cats:
                        cats.append(cat)
                    break
        return cats or ["general"]

    def _load_cached_index(self):
        """Loads index from disk if available."""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data.get("apps", []):
                    rec = ApplicationRecord(**item)
                    self._index[rec.id] = rec
                self._last_refresh_time = data.get("timestamp", 0)
                logger.info(f"Loaded {len(self._index)} applications from cached index.")
            except Exception as e:
                logger.warning(f"Failed to load cached application index: {e}")

    def save_index(self):
        """Persists index to disk."""
        try:
            data = {
                "timestamp": time.time(),
                "count": len(self._index),
                "apps": [rec.to_dict() for rec in self._index.values()]
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved application index with {len(self._index)} entries to {self.cache_file}")
        except Exception as e:
            logger.error(f"Failed to save application index: {e}")

    # =========================================================================
    # DISCOVERY SOURCES
    # =========================================================================

    def _discover_start_apps_catalog(self) -> List[ApplicationRecord]:
        """Queries Windows StartApps via PowerShell (UWP, Store, Desktop apps with AppIDs)."""
        records = []
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = (item.get("Name") or "").strip()
                    app_id = (item.get("AppID") or "").strip()
                    if not name or not app_id:
                        continue

                    norm_id = self._normalize_id(name)
                    is_uwp = "!" in app_id or "_" in app_id or not os.path.isabs(app_id)
                    target = app_id if os.path.isabs(app_id) else f"shell:AppsFolder\\{app_id}"
                    launch_method = "direct_exec" if os.path.isabs(app_id) else "apps_folder"
                    app_type = "win32" if os.path.isabs(app_id) else "uwp"

                    rec = ApplicationRecord(
                        id=norm_id,
                        name=name,
                        aliases=self._generate_aliases(name, app_id if os.path.isabs(app_id) else None),
                        target=target,
                        app_type=app_type,
                        launch_method=launch_method,
                        source="uwp_package" if is_uwp else "start_menu",
                        executable_path=app_id if os.path.isabs(app_id) else None,
                        description=f"Installed Windows application ({name})",
                        categories=self._infer_categories(name)
                    )
                    records.append(rec)
        except Exception as e:
            logger.warning(f"StartApps catalog discovery note: {e}")
        return records

    def _discover_start_menu_shortcuts(self) -> List[ApplicationRecord]:
        """Discovers .lnk shortcuts in User and All Users Start Menu directories."""
        records = []
        dirs = [
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
        ]
        seen_targets = set()

        for base_dir in dirs:
            if not os.path.exists(base_dir):
                continue
            for root, _, files in os.walk(base_dir):
                for f in files:
                    if not f.lower().endswith(".lnk"):
                        continue
                    lnk_path = os.path.join(root, f)
                    app_name = f[:-4].strip()
                    if not app_name:
                        continue

                    # Filter out uninstall shortcuts
                    if "uninstall" in app_name.lower():
                        continue

                    norm_id = self._normalize_id(app_name)
                    if lnk_path in seen_targets:
                        continue
                    seen_targets.add(lnk_path)

                    records.append(ApplicationRecord(
                        id=norm_id,
                        name=app_name,
                        aliases=self._generate_aliases(app_name),
                        target=lnk_path,
                        app_type="win32",
                        launch_method="shortcut",
                        source="start_menu",
                        install_location=os.path.dirname(lnk_path),
                        description=f"Start Menu shortcut for {app_name}",
                        categories=self._infer_categories(app_name)
                    ))
        return records

    def _discover_app_paths(self) -> List[ApplicationRecord]:
        """Queries HKLM and HKCU 'App Paths' registry keys."""
        records = []
        if not WINREG_AVAILABLE:
            return records

        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
        ]

        for root_hkey, path in roots:
            try:
                key = winreg.OpenKey(root_hkey, path)
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subkey = winreg.OpenKey(key, subkey_name)
                        exe_path, _ = winreg.QueryValueEx(subkey, "")
                        if exe_path and os.path.exists(exe_path):
                            clean_name = os.path.splitext(subkey_name)[0]
                            norm_id = self._normalize_id(clean_name)
                            records.append(ApplicationRecord(
                                id=norm_id,
                                name=clean_name.replace("_", " ").title(),
                                aliases=self._generate_aliases(clean_name, subkey_name),
                                target=exe_path,
                                app_type="win32",
                                launch_method="direct_exec",
                                source="app_paths",
                                executable_path=exe_path,
                                install_location=os.path.dirname(exe_path),
                                description=f"Registered App Path executable: {subkey_name}",
                                categories=self._infer_categories(clean_name)
                            ))
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"App Paths scan note: {e}")
        return records

    def _discover_registry_uninstall(self) -> List[ApplicationRecord]:
        """Queries Uninstall registry keys for installed software."""
        records = []
        if not WINREG_AVAILABLE:
            return records

        roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]

        for root_hkey, path in roots:
            try:
                key = winreg.OpenKey(root_hkey, path)
                num_subkeys, _, _ = winreg.QueryInfoKey(key)
                for i in range(num_subkeys):
                    try:
                        sk_name = winreg.EnumKey(key, i)
                        sk = winreg.OpenKey(key, sk_name)
                        try:
                            disp_name, _ = winreg.QueryValueEx(sk, "DisplayName")
                        except Exception:
                            continue

                        if not disp_name or not str(disp_name).strip():
                            continue

                        disp_name = str(disp_name).strip()
                        # Ignore patches, updates, redistributables
                        if any(x in disp_name.lower() for x in ["update for", "security update", "hotfix", "redistributable"]):
                            continue

                        install_loc = ""
                        try:
                            install_loc, _ = winreg.QueryValueEx(sk, "InstallLocation")
                        except Exception:
                            pass

                        display_icon = ""
                        try:
                            display_icon, _ = winreg.QueryValueEx(sk, "DisplayIcon")
                        except Exception:
                            pass

                        exe_target = None
                        if display_icon:
                            cand = str(display_icon).split(",")[0].strip(' "')
                            if cand.lower().endswith(".exe") and os.path.exists(cand):
                                exe_target = cand

                        if not exe_target and install_loc and os.path.isdir(str(install_loc)):
                            for root_d, _, files_d in os.walk(str(install_loc)):
                                for fd in files_d:
                                    if fd.lower().endswith(".exe") and "uninstall" not in fd.lower():
                                        exe_target = os.path.join(root_d, fd)
                                        break
                                if exe_target:
                                    break

                        norm_id = self._normalize_id(disp_name)
                        records.append(ApplicationRecord(
                            id=norm_id,
                            name=disp_name,
                            aliases=self._generate_aliases(disp_name, exe_target),
                            target=exe_target or str(install_loc) or disp_name,
                            app_type="win32",
                            launch_method="direct_exec" if exe_target else "system_uri",
                            source="registry",
                            executable_path=exe_target,
                            install_location=str(install_loc) if install_loc else None,
                            description=f"Installed software ({disp_name})",
                            categories=self._infer_categories(disp_name)
                        ))
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Registry Uninstall scan note: {e}")
        return records

    def _discover_app_aliases(self) -> List[ApplicationRecord]:
        """Discovers Windows App Execution Aliases in %LOCALAPPDATA%\\Microsoft\\WindowsApps."""
        records = []
        apps_dir = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")
        if not os.path.exists(apps_dir):
            return records

        for item in os.listdir(apps_dir):
            full_p = os.path.join(apps_dir, item)
            if item.lower().endswith(".exe") and os.path.isfile(full_p):
                name = os.path.splitext(item)[0]
                norm_id = self._normalize_id(name)
                records.append(ApplicationRecord(
                    id=norm_id,
                    name=name.title(),
                    aliases=self._generate_aliases(name, item),
                    target=full_p,
                    app_type="alias",
                    launch_method="direct_exec",
                    source="app_alias",
                    executable_path=full_p,
                    description=f"Windows App Execution Alias ({item})",
                    categories=self._infer_categories(name)
                ))
        return records

    def _discover_system_apps(self) -> List[ApplicationRecord]:
        """Registers built-in Windows System utilities and Settings URIs."""
        system_defs = [
            {
                "id": "windows_settings",
                "name": "Windows Settings",
                "aliases": ["settings", "windows settings", "pc settings", "system settings"],
                "target": "ms-settings:",
                "app_type": "system",
                "launch_method": "system_uri",
                "description": "Windows 11 System Settings application",
                "categories": ["system"]
            },
            {
                "id": "task_manager",
                "name": "Task Manager",
                "aliases": ["task manager", "taskmgr", "task manager", "process manager"],
                "target": "taskmgr.exe",
                "app_type": "system",
                "launch_method": "direct_exec",
                "description": "Windows Task Manager system process and resource monitor",
                "categories": ["system"]
            },
            {
                "id": "calculator",
                "name": "Calculator",
                "aliases": ["calculator", "calc", "math calculator"],
                "target": "calc.exe",
                "app_type": "system",
                "launch_method": "direct_exec",
                "description": "Windows Calculator app",
                "categories": ["utility"]
            },
            {
                "id": "notepad",
                "name": "Notepad",
                "aliases": ["notepad", "notes", "text editor"],
                "target": "notepad.exe",
                "app_type": "system",
                "launch_method": "direct_exec",
                "description": "Windows default text editor",
                "categories": ["productivity", "utility"]
            },
            {
                "id": "control_panel",
                "name": "Control Panel",
                "aliases": ["control panel", "control"],
                "target": "control.exe",
                "app_type": "system",
                "launch_method": "direct_exec",
                "description": "Windows legacy Control Panel",
                "categories": ["system"]
            },
            {
                "id": "file_explorer",
                "name": "File Explorer",
                "aliases": ["file explorer", "explorer", "files", "my files", "my computer", "this pc"],
                "target": "explorer.exe",
                "app_type": "system",
                "launch_method": "direct_exec",
                "description": "Windows File Explorer",
                "categories": ["system", "utility"]
            },
            {
                "id": "windows_terminal",
                "name": "Windows Terminal",
                "aliases": ["terminal", "windows terminal", "wt", "command prompt", "cmd", "powershell"],
                "target": "wt.exe" if shutil.which("wt.exe") else "powershell.exe",
                "app_type": "system",
                "launch_method": "direct_exec",
                "description": "Command-line terminal and shell environment",
                "categories": ["development", "system"]
            },
            {
                "id": "mspaint",
                "name": "Paint",
                "aliases": ["paint", "mspaint", "paint app", "drawing"],
                "target": "mspaint.exe",
                "app_type": "system",
                "launch_method": "direct_exec",
                "description": "Windows Paint image editor",
                "categories": ["design", "utility"]
            },
            {
                "id": "device_manager",
                "name": "Device Manager",
                "aliases": ["device manager", "devmgmt"],
                "target": "devmgmt.msc",
                "app_type": "system",
                "launch_method": "direct_exec",
                "description": "Windows Device Manager configuration tool",
                "categories": ["system"]
            }
        ]

        records = []
        for d in system_defs:
            rec = ApplicationRecord(
                id=d["id"],
                name=d["name"],
                aliases=d["aliases"],
                target=d["target"],
                app_type=d["app_type"],
                launch_method=d["launch_method"],
                source="system",
                description=d["description"],
                categories=d["categories"]
            )
            records.append(rec)
        return records

    def _discover_special_folders(self) -> List[ApplicationRecord]:
        """Registers standard user directories (Downloads, Documents, Desktop, Pictures, Videos, Music)."""
        folders = [
            ("Downloads", os.path.expandvars(r"%USERPROFILE%\Downloads"), ["downloads", "download folder", "my downloads"]),
            ("Documents", os.path.expandvars(r"%USERPROFILE%\Documents"), ["documents", "document folder", "my documents", "docs"]),
            ("Desktop", os.path.expandvars(r"%USERPROFILE%\Desktop"), ["desktop", "my desktop"]),
            ("Pictures", os.path.expandvars(r"%USERPROFILE%\Pictures"), ["pictures", "photos", "my pictures", "images"]),
            ("Videos", os.path.expandvars(r"%USERPROFILE%\Videos"), ["videos", "movies", "my videos"]),
            ("Music", os.path.expandvars(r"%USERPROFILE%\Music"), ["music", "songs", "my music", "audio folder"])
        ]
        records = []
        for name, path, aliases in folders:
            if os.path.exists(path):
                norm_id = f"folder_{name.lower()}"
                records.append(ApplicationRecord(
                    id=norm_id,
                    name=f"{name} Folder",
                    aliases=aliases,
                    target=path,
                    app_type="folder",
                    launch_method="explorer_folder",
                    source="folder",
                    install_location=path,
                    description=f"User {name} folder in File Explorer",
                    categories=["system", "utility"]
                ))
        return records

    # =========================================================================
    # INDEX BUILDING & DEDUPLICATION
    # =========================================================================

    def refresh_index(self, force: bool = False) -> Dict[str, Any]:
        """Refreshes the index across all discovery sources, deduping and merging records."""
        now = time.time()
        # Avoid rapid re-scanning unless forced (cache for 1 hour)
        if not force and self._index and (now - self._last_refresh_time) < 3600:
            return {"success": True, "count": len(self._index), "cached": True}

        logger.info("Rebuilding Windows Application Discovery Index...")
        start_time = time.time()

        all_candidates: List[ApplicationRecord] = []

        # 1. System apps & special folders (high reliability)
        all_candidates.extend(self._discover_system_apps())
        all_candidates.extend(self._discover_special_folders())

        # 2. StartApps Catalog (Store, UWP & desktop with AppIDs)
        all_candidates.extend(self._discover_start_apps_catalog())

        # 3. Start Menu Shortcuts (.lnk files)
        all_candidates.extend(self._discover_start_menu_shortcuts())

        # 4. App Paths Registry
        all_candidates.extend(self._discover_app_paths())

        # 5. App Execution Aliases
        all_candidates.extend(self._discover_app_aliases())

        # 6. Registry Uninstall Keys
        all_candidates.extend(self._discover_registry_uninstall())

        # Deduplication & Merge Priority:
        # Priority order: system > uwp_package / start_menu > app_paths > app_alias > registry
        merged: Dict[str, ApplicationRecord] = {}

        for cand in all_candidates:
            existing = merged.get(cand.id)
            if not existing:
                merged[cand.id] = cand
            else:
                # Merge aliases
                for a in cand.aliases:
                    if a not in existing.aliases:
                        existing.aliases.append(a)
                # Merge categories
                for c in cand.categories:
                    if c not in existing.categories:
                        existing.categories.append(c)
                # Upgrade target if new candidate has a direct executable or apps_folder target
                if not existing.executable_path and cand.executable_path:
                    existing.executable_path = cand.executable_path
                if existing.launch_method == "system_uri" and cand.launch_method in ("direct_exec", "apps_folder", "shortcut"):
                    existing.target = cand.target
                    existing.launch_method = cand.launch_method
                    existing.app_type = cand.app_type

        self._index = merged
        self._last_refresh_time = time.time()
        self.save_index()

        duration = round(time.time() - start_time, 2)
        logger.info(f"Discovery index built with {len(self._index)} applications in {duration}s.")
        return {"success": True, "count": len(self._index), "duration": duration, "cached": False}

    # =========================================================================
    # SEARCH & RESOLUTION
    # =========================================================================

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Searches the application index using exact match, prefix match,
        token overlap, and fuzzy string similarity.
        """
        if not self._index:
            self.refresh_index()

        q = query.lower().strip()
        # Clean conversational noise
        q = re.sub(r"^(?:open|launch|start|run|switch to|show|find)\s+", "", q).strip()
        q = re.sub(r"\s+(?:application|app|program|window|please|now)$", "", q).strip()
        q = q.strip(" .,!?:;'\"")

        scored_results = []

        for rec in self._index.values():
            score = 0.0
            name_lower = rec.name.lower()

            # 1. Exact match on name or ID
            if q == name_lower or q == rec.id:
                score = 100.0
            elif q in rec.aliases:
                score = 95.0
            # 2. Word boundary or starts-with match
            elif name_lower.startswith(q) or f" {q}" in name_lower:
                score = 85.0
            # 3. Substring match
            elif q in name_lower:
                score = 70.0
            # 4. Alias substring match
            elif any(q in a for a in rec.aliases):
                score = 65.0
            # 5. Token overlap
            else:
                q_words = set(q.split())
                name_words = set(name_lower.split())
                overlap = q_words.intersection(name_words)
                if overlap:
                    score = 40.0 + (len(overlap) * 15.0)

            if score > 0:
                # Small boost for frequently launched apps
                launches = rec.last_launch_status.get("success_count", 0)
                score += min(launches * 2.0, 10.0)

                d = rec.to_dict()
                d["match_score"] = score
                scored_results.append(d)

        scored_results.sort(key=lambda x: x["match_score"], reverse=True)
        return scored_results[:limit]

    def resolve(self, query: str) -> Dict[str, Any]:
        """
        Resolves an application query to a single best match or returns an ambiguity response.
        """
        candidates = self.search(query, limit=5)
        if not candidates:
            return {
                "success": False,
                "query": query,
                "error": f"No installed application matching '{query}' could be found in the index.",
                "app": None
            }

        top = candidates[0]
        # Ambiguity check: if 2nd result has close score (>80 and within 5 points of top), flag as ambiguous
        if len(candidates) > 1:
            second = candidates[1]
            if top["match_score"] < 95.0 and (top["match_score"] - second["match_score"]) < 10.0:
                return {
                    "success": False,
                    "ambiguous": True,
                    "query": query,
                    "message": f"Multiple applications match '{query}'. Please choose one.",
                    "candidates": [
                        {"id": c["id"], "name": c["name"], "type": c["app_type"], "description": c["description"]}
                        for c in candidates[:4]
                    ]
                }

        return {
            "success": True,
            "ambiguous": False,
            "query": query,
            "app": top
        }

    def find_by_description(self, description: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Matches functional descriptions (e.g., 'application I use for Python', 'my music player').
        """
        if not self._index:
            self.refresh_index()

        desc_lower = description.lower()
        scored = []

        # Find target categories from keywords
        target_cats = []
        for cat, kw_list in self.CATEGORY_KEYWORDS.items():
            for kw in kw_list:
                if re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
                    if cat not in target_cats:
                        target_cats.append(cat)
                    break

        for rec in self._index.values():
            score = 0.0
            rec_text = f"{rec.name} {rec.description} {' '.join(rec.aliases)}".lower()

            # Category match
            for cat in target_cats:
                if cat in rec.categories:
                    score += 40.0

            # Keyword overlap
            for word in desc_lower.split():
                if len(word) > 2 and word in rec_text:
                    score += 15.0

            if score > 0:
                d = rec.to_dict()
                d["match_score"] = score
                scored.append(d)

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        return scored[:limit]

    def list_apps(self, category: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
        """Lists applications in index, optionally filtered by category."""
        if not self._index:
            self.refresh_index()

        results = []
        for rec in self._index.values():
            if category:
                if category.lower() in rec.categories:
                    results.append(rec.to_dict())
            else:
                results.append(rec.to_dict())

        return {
            "success": True,
            "total_indexed": len(self._index),
            "category_filter": category,
            "count": len(results[:limit]),
            "apps": results[:limit]
        }

    def record_launch_result(self, app_id: str, success: bool, message: str = ""):
        """Updates launch statistics in index."""
        rec = self._index.get(app_id)
        if rec:
            rec.last_launch_status["last_launch"] = time.time()
            if success:
                rec.last_launch_status["success_count"] = rec.last_launch_status.get("success_count", 0) + 1
            else:
                rec.last_launch_status["failure_count"] = rec.last_launch_status.get("failure_count", 0) + 1
                rec.last_launch_status["last_error"] = message
            self.save_index()


# Global Singleton Instance
app_discovery = AppDiscoveryEngine()
