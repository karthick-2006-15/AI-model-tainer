"""
Proactive Daily Briefing Engine
Synthesizes contextual morning/daily briefings covering hardware telemetry, tasks, and system readiness.
"""

import datetime
import logging
from typing import Dict, Any, List
from modules.automation.system import SystemMonitor
from core.memory.profile import profile_memory
from core.planning.executor import dag_executor

logger = logging.getLogger("jarvis.scheduler.briefing")


class DailyBriefingGenerator:
    """Generates natural language daily executive briefings for the user."""

    def generate_briefing(self) -> Dict[str, Any]:
        """
        Gathers live system metrics, user profile facts, and active tasks to construct a comprehensive briefing.
        """
        logger.info("Generating proactive daily briefing...")

        # 1. Gather System Hardware Telemetry
        metrics = SystemMonitor.get_hardware_metrics()
        cpu_usage = metrics.get("cpu_percent", 0.0)
        ram_usage = metrics.get("memory", {}).get("percent", 0.0)
        disk_free_gb = metrics.get("disk", {}).get("free_gb", 0.0)
        battery = metrics.get("battery", {})
        battery_pct = battery.get("percent")
        is_charging = battery.get("power_plugged", True)

        # 2. Gather User Profile Context
        facts = profile_memory.list_facts()
        key_facts = [f"{f.get('category')}: {f.get('fact')}" for f in facts[:5]]

        # 3. Gather Active Plans
        plans = dag_executor.list_plans()
        active_plans = [p for p in plans if p.get("status") in ("pending", "running")]

        # 4. Formulate Greeting based on time of day
        now = datetime.datetime.now()
        hour = now.hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        # 5. Formulate Speech Script
        battery_msg = f"Battery is at {battery_pct}%" if battery_pct is not None else "Power supply is nominal"
        charging_msg = " and charging" if is_charging else " on battery power"
        task_msg = f"You have {len(active_plans)} active development tasks queued." if active_plans else "All tasks are up to date."

        speech_text = (
            f"{greeting}, sir. JARVIS systems are operational. "
            f"{battery_msg}{charging_msg}. RAM usage is at {ram_usage}%, with {disk_free_gb:.1f} GB storage available. "
            f"{task_msg} Core neural brain is primed and awaiting your command."
        )

        # 6. Formulate Markdown Briefing
        markdown = (
            f"# JARVIS Daily Executive Briefing\n"
            f"**Timestamp:** {now.strftime('%A, %B %d, %Y - %I:%M %p')}\n\n"
            f"### System Health Status\n"
            f"- **CPU Load:** {cpu_usage}%\n"
            f"- **Memory Usage:** {ram_usage}%\n"
            f"- **Storage Remaining:** {disk_free_gb:.1f} GB\n"
            f"- **Power:** {battery_pct}% {'(Plugged In)' if is_charging else '(Discharging)'}\n\n"
            f"### Active Objectives ({len(active_plans)})\n"
        )
        if active_plans:
            for p in active_plans:
                markdown += f"- **{p['goal']}** [{p['status'].upper()}]\n"
        else:
            markdown += "- No active or blocked background tasks.\n"

        if key_facts:
            markdown += f"\n### Context & Known Profile Facts\n"
            for kf in key_facts:
                markdown += f"- {kf}\n"

        return {
            "success": True,
            "timestamp": now.isoformat(),
            "greeting": greeting,
            "speech_text": speech_text,
            "briefing_markdown": markdown,
            "telemetry": {
                "cpu_percent": cpu_usage,
                "ram_percent": ram_usage,
                "disk_free_gb": disk_free_gb,
                "battery_percent": battery_pct,
                "is_charging": is_charging
            },
            "active_tasks_count": len(active_plans)
        }


# Global briefing generator instance
daily_briefing_generator = DailyBriefingGenerator()
