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


class SystemController:
    """Windows system controls: workstation lock, master audio, sleep, and power state."""

    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF

    @staticmethod
    def lock_workstation() -> Dict[str, Any]:
        """Locks the Windows workstation immediately."""
        try:
            import ctypes
            result = ctypes.windll.user32.LockWorkStation()
            if result != 0:
                return {"success": True, "action": "lock_workstation", "message": "Workstation locked successfully."}
            else:
                return {"success": False, "error": "LockWorkStation failed."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def adjust_volume(cls, action: str = "up", steps: int = 5) -> Dict[str, Any]:
        """
        Adjusts master system audio volume.
        action: 'up', 'down', 'mute', 'unmute'
        """
        try:
            import ctypes
            user32 = ctypes.windll.user32
            action_lower = action.lower().strip()

            if action_lower in ("mute", "unmute", "toggle_mute"):
                user32.keybd_event(cls.VK_VOLUME_MUTE, 0, 0, 0)
                user32.keybd_event(cls.VK_VOLUME_MUTE, 0, 2, 0)
                return {"success": True, "action": "mute_toggle", "message": "Master audio mute toggled."}

            vk = cls.VK_VOLUME_UP if "up" in action_lower or "increase" in action_lower else cls.VK_VOLUME_DOWN
            for _ in range(max(1, min(steps, 25))):
                user32.keybd_event(vk, 0, 0, 0)
                user32.keybd_event(vk, 0, 2, 0)

            return {
                "success": True,
                "action": f"volume_{'up' if vk == cls.VK_VOLUME_UP else 'down'}",
                "steps": steps,
                "message": f"Adjusted volume {action_lower} by {steps} steps."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def sleep_system() -> Dict[str, Any]:
        """Puts the computer into sleep mode."""
        try:
            import ctypes
            # SetSuspendState(Hibernate=False, ForceCritical=False, DisableWakeEvent=False)
            ctypes.windll.PowrProf.SetSuspendState(0, 0, 0)
            return {"success": True, "action": "sleep", "message": "System entering sleep mode."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def restart_system(confirm: bool = False) -> Dict[str, Any]:
        """Restarts the workstation. Requires explicit confirmation."""
        if not confirm:
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "System restart requires explicit authorization. Please confirm to proceed."
            }
        try:
            import subprocess
            subprocess.run(["shutdown", "/r", "/t", "10", "/c", "JARVIS initiated system restart."], check=False)
            return {"success": True, "action": "restart", "message": "System restart initiated in 10 seconds."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def shutdown_system(confirm: bool = False) -> Dict[str, Any]:
        """Shuts down the workstation. Requires explicit confirmation."""
        if not confirm:
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "System shutdown requires explicit authorization. Please confirm to proceed."
            }
        try:
            import subprocess
            subprocess.run(["shutdown", "/s", "/t", "10", "/c", "JARVIS initiated system shutdown."], check=False)
            return {"success": True, "action": "shutdown", "message": "System shutdown initiated in 10 seconds."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def abort_shutdown() -> Dict[str, Any]:
        """Cancels a pending shutdown or restart."""
        try:
            import subprocess
            subprocess.run(["shutdown", "/a"], check=False)
            return {"success": True, "action": "abort_shutdown", "message": "Pending shutdown or restart aborted."}
        except Exception as e:
            return {"success": False, "error": str(e)}


system_controller = SystemController()
