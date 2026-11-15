"""
Windows Intelligence & System Health Analytics Engine
Deep monitoring of CPU, RAM, Disks, Battery, Network interfaces, Running Processes,
Startup Applications, Storage distribution, Application Crash signatures, and Basic Troubleshooting.
"""

import os
import sys
import time
import socket
import logging
from typing import Dict, Any, List, Optional
import psutil

try:
    import winreg
    WINREG_AVAILABLE = True
except ImportError:
    WINREG_AVAILABLE = False

from modules.automation.system import SystemMonitor

logger = logging.getLogger("jarvis.automation.windows_intel")


class WindowsIntelligence:
    """Provides deep diagnostic inspection and health analytics for Windows 11."""

    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # =========================================================================
    # HARDWARE & NETWORK MONITORING
    # =========================================================================

    def get_hardware_telemetry(self) -> Dict[str, Any]:
        """Collects current hardware performance metrics via SystemMonitor."""
        return SystemMonitor.get_hardware_metrics()

    def get_network_status(self) -> Dict[str, Any]:
        """
        Inspects network interfaces, active IP addresses, transfer rates,
        and verifies internet connectivity.
        """
        # Test internet reachability
        is_connected = False
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2.0)
            is_connected = True
        except OSError:
            is_connected = False

        # Network I/O counters
        net_io = psutil.net_io_counters()
        bytes_sent_mb = round(net_io.bytes_sent / (1024 ** 2), 2)
        bytes_recv_mb = round(net_io.bytes_recv / (1024 ** 2), 2)

        # Active interfaces
        if_addrs = psutil.net_if_addrs()
        if_stats = psutil.net_if_stats()
        active_interfaces = []

        for name, addrs in if_addrs.items():
            stat = if_stats.get(name)
            if stat and stat.isup:
                ip_list = [a.address for a in addrs if a.family == socket.AF_INET]
                if ip_list:
                    active_interfaces.append({
                        "interface": name,
                        "ipv4": ip_list[0],
                        "speed_mbps": stat.speed,
                        "is_up": stat.isup
                    })

        return {
            "internet_connected": is_connected,
            "bytes_sent_mb": bytes_sent_mb,
            "bytes_recv_mb": bytes_recv_mb,
            "active_interfaces": active_interfaces,
            "interface_count": len(active_interfaces)
        }

    # =========================================================================
    # RUNNING PROCESSES & APPLICATION CRASH DETECTION
    # =========================================================================

    def get_running_processes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns top running processes ranked by CPU and RAM utilization."""
        return SystemMonitor.get_top_processes(limit=limit)

    def detect_recent_crashes(self) -> Dict[str, Any]:
        """
        Inspects application error indicators by checking recent WER (Windows Error Reporting)
        reports or crash signatures in %LOCALAPPDATA%\\CrashDumps.
        """
        crash_dumps_dir = os.path.expandvars(r"%LOCALAPPDATA%\CrashDumps")
        crashes = []

        if os.path.exists(crash_dumps_dir):
            for file in os.listdir(crash_dumps_dir):
                if file.lower().endswith(".dmp"):
                    p = os.path.join(crash_dumps_dir, file)
                    try:
                        stat = os.stat(p)
                        crashes.append({
                            "dump_file": file,
                            "path": p,
                            "size_bytes": stat.st_size,
                            "timestamp": time.ctime(stat.st_mtime)
                        })
                    except Exception:
                        continue

        return {
            "has_crashes": len(crashes) > 0,
            "crash_count": len(crashes),
            "recent_crashes": crashes[-5:] if crashes else [],
            "status": "No recent unhandled crash dumps detected." if not crashes else f"Detected {len(crashes)} crash dumps."
        }

    # =========================================================================
    # STARTUP APPLICATIONS INSPECTION
    # =========================================================================

    def get_startup_applications(self) -> List[Dict[str, Any]]:
        """
        Enumerates software configured to automatically start on Windows boot
        from Registry Run keys and the user's Startup folder.
        """
        startup_apps = []

        # 1. User Startup Directory
        startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
        if os.path.exists(startup_dir):
            for item in os.listdir(startup_dir):
                p = os.path.join(startup_dir, item)
                if os.path.isfile(p):
                    startup_apps.append({
                        "name": item,
                        "location": p,
                        "source": "Startup_Folder",
                        "enabled": True
                    })

        # 2. Windows Registry Run Keys
        if WINREG_AVAILABLE:
            run_keys = [
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU_Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM_Run")
            ]
            for root, subkey_path, source_label in run_keys:
                try:
                    key = winreg.OpenKey(root, subkey_path)
                    num_values = winreg.QueryInfoKey(key)[1]
                    for i in range(num_values):
                        try:
                            val_name, val_data, _ = winreg.EnumValue(key, i)
                            startup_apps.append({
                                "name": val_name,
                                "command": val_data,
                                "source": source_label,
                                "enabled": True
                            })
                        except Exception:
                            continue
                except Exception:
                    continue

        return startup_apps

    # =========================================================================
    # STORAGE ANALYSIS & TROUBLESHOOTING
    # =========================================================================

    def analyze_storage(self, target_folder: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes drive utilization and identifies space consumption across directories.
        """
        folder = target_folder or self.project_root
        total_size = 0
        file_count = 0
        extensions_breakdown: Dict[str, int] = {}

        for root, _, files in os.walk(folder):
            if any(ign in root for ign in [".git", "node_modules", ".venv", "__pycache__"]):
                continue
            for f in files:
                p = os.path.join(root, f)
                try:
                    sz = os.path.getsize(p)
                    total_size += sz
                    file_count += 1
                    _, ext = os.path.splitext(f)
                    ext = ext.lower() or "no_ext"
                    extensions_breakdown[ext] = extensions_breakdown.get(ext, 0) + sz
                except Exception:
                    continue

        # Sort extensions by storage impact
        top_exts = sorted(extensions_breakdown.items(), key=lambda x: x[1], reverse=True)[:6]

        return {
            "analyzed_path": folder,
            "total_size_mb": round(total_size / (1024 ** 2), 2),
            "file_count": file_count,
            "top_file_types": [
                {"extension": ext, "size_mb": round(sz / (1024 ** 2), 2)}
                for ext, sz in top_exts
            ]
        }

    def run_basic_troubleshooting(self) -> Dict[str, Any]:
        """
        Performs proactive diagnostic checks on RAM, CPU, Storage, Network, and Crashes.
        Returns recommendations if any anomalies are found.
        """
        metrics = self.get_hardware_telemetry()
        net = self.get_network_status()
        crashes = self.detect_recent_crashes()

        issues = []
        recommendations = []

        # CPU check
        cpu_pct = metrics.get("cpu", {}).get("percent", 0.0)
        if cpu_pct > 90.0:
            issues.append(f"High CPU utilization: {cpu_pct}%")
            recommendations.append("Inspect running processes for rogue background loops.")

        # RAM check
        ram_pct = metrics.get("ram", {}).get("percent", 0.0)
        if ram_pct > 88.0:
            issues.append(f"High RAM consumption: {ram_pct}%")
            recommendations.append("Close idle browser tabs or heavy development applications.")

        # Disk check
        disk_pct = metrics.get("disk", {}).get("percent", 0.0)
        if disk_pct > 92.0:
            issues.append(f"Primary system drive (C:) is {disk_pct}% full")
            recommendations.append("Run file organization and purge temporary files.")

        # Network check
        if not net.get("internet_connected"):
            issues.append("No active internet connection detected.")
            recommendations.append("Verify Wi-Fi/Ethernet connectivity and default gateway router.")

        # Crash check
        if crashes.get("has_crashes"):
            issues.append(f"{crashes['crash_count']} recent application crash dump(s) found.")
            recommendations.append("Review error logs in storage/logs/ for fault signatures.")

        is_healthy = len(issues) == 0
        return {
            "healthy": is_healthy,
            "status": "All diagnostic health parameters nominal." if is_healthy else f"Detected {len(issues)} alert(s).",
            "alerts": issues,
            "recommendations": recommendations,
            "metrics_summary": {
                "cpu_percent": cpu_pct,
                "ram_percent": ram_pct,
                "disk_percent": disk_pct,
                "internet": net.get("internet_connected")
            }
        }


# Global singleton instance
windows_intelligence = WindowsIntelligence()
