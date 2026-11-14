"""
System Telemetry & Hardware Monitor for Windows
Uses psutil to monitor CPU, RAM, disk, battery, and process telemetry in real-time.
"""

from typing import Dict, Any, List
import psutil
import platform
import os


class SystemMonitor:
    @staticmethod
    def get_hardware_metrics() -> Dict[str, Any]:
        """Collects current hardware performance metrics."""
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_count = psutil.cpu_count(logical=True)
        
        virtual_mem = psutil.virtual_memory()
        ram_used_gb = round(virtual_mem.used / (1024 ** 3), 2)
        ram_total_gb = round(virtual_mem.total / (1024 ** 3), 2)
        ram_percent = virtual_mem.percent

        # Disk usage for system drive (C:)
        try:
            disk_usage = psutil.disk_usage("C:\\" if os.name == "nt" else "/")
            disk_used_gb = round(disk_usage.used / (1024 ** 3), 2)
            disk_total_gb = round(disk_usage.total / (1024 ** 3), 2)
            disk_percent = disk_usage.percent
        except Exception:
            disk_used_gb, disk_total_gb, disk_percent = 0.0, 0.0, 0.0

        # Battery metrics if available
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else None
        battery_plugged = battery.power_plugged if battery else None

        return {
            "platform": platform.system(),
            "os_release": platform.release(),
            "cpu": {
                "percent": cpu_percent,
                "cores": cpu_count
            },
            "ram": {
                "used_gb": ram_used_gb,
                "total_gb": ram_total_gb,
                "percent": ram_percent
            },
            "disk": {
                "used_gb": disk_used_gb,
                "total_gb": disk_total_gb,
                "percent": disk_percent
            },
            "battery": {
                "percent": battery_percent,
                "power_plugged": battery_plugged
            },
            "process_count": len(psutil.pids())
        }

    @staticmethod
    def get_top_processes(limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieves top processes sorted by CPU and memory usage."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info['cpu_percent'] or 0.0,
                    "memory_percent": round(info['memory_percent'] or 0.0, 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU usage descending
        processes.sort(key=lambda p: p['cpu_percent'], reverse=True)
        return processes[:limit]
