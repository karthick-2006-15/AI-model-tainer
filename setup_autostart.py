"""
JARVIS System Auto-Start Installer
Registers JARVIS to launch silently and automatically whenever the laptop is turned on or user logs in.
Installs both:
1. Windows Startup folder VBScript launcher (silent, windowless pythonw execution)
2. Windows Task Scheduler XML task with battery-power execution permission
"""

import os
import sys
import subprocess
import tempfile
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("jarvis.autostart")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SERVICE_SCRIPT = os.path.join(PROJECT_ROOT, "jarvis_service.py")

# Locate pythonw.exe
pythonw_candidates = [
    os.path.join(os.path.dirname(sys.executable), "pythonw.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe"),
    r"C:\Python310\pythonw.exe",
    sys.executable
]
PYTHONW_PATH = sys.executable
for cand in pythonw_candidates:
    if os.path.exists(cand) and cand.endswith("pythonw.exe"):
        PYTHONW_PATH = cand
        break

logger.info(f"Using python executable: {PYTHONW_PATH}")


def install_startup_vbs() -> bool:
    """Installs a VBScript launcher in the user's Windows Startup folder."""
    startup_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup")
    if not os.path.exists(startup_dir):
        logger.error(f"Startup directory not found: {startup_dir}")
        return False

    vbs_path = os.path.join(startup_dir, "JARVIS_AutoStart.vbs")
    vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{PROJECT_ROOT}"
WshShell.Run """{PYTHONW_PATH}"" ""{SERVICE_SCRIPT}""", 0, False
'''
    try:
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_content)
        logger.info(f"Installed Windows Startup VBScript: {vbs_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write startup VBScript: {e}")
        return False


def install_task_scheduler() -> bool:
    """Registers a Windows Task Scheduler task that runs at user logon, including on battery power."""
    task_name = "JARVIS_Always_On"
    xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Author>JARVIS</Author>
    <Description>JARVIS Always-On Voice Assistant Background Daemon</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHONW_PATH}</Command>
      <Arguments>"{SERVICE_SCRIPT}"</Arguments>
      <WorkingDirectory>{PROJECT_ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
'''
    xml_file = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-16", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            xml_file = f.name

        cmd = ["schtasks", "/create", "/tn", task_name, "/xml", xml_file, "/f"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            logger.info(f"Registered Windows Scheduled Task '{task_name}' successfully.")
            return True
        else:
            logger.warning(f"Could not register task scheduler task: {res.stderr.strip()}")
            return False
    except Exception as e:
        logger.warning(f"Task Scheduler configuration error: {e}")
        return False
    finally:
        if xml_file and os.path.exists(xml_file):
            try:
                os.remove(xml_file)
            except Exception:
                pass


def main():
    print("==================================================")
    print("Installing JARVIS Always-On Auto-Start Engine...")
    print("==================================================")
    vbs_ok = install_startup_vbs()
    task_ok = install_task_scheduler()

    if vbs_ok or task_ok:
        print("\nSUCCESS: JARVIS is now registered to start automatically whenever your laptop turns on!")
        print(f"• Service script: {SERVICE_SCRIPT}")
        print("• Voice trigger: Say 'Hey Jarvis' at any time.")
        print("• Speech response: Enabled aloud via laptop speakers.")
    else:
        print("\nWARNING: Auto-start installation encountered issues. Please check logs.")


if __name__ == "__main__":
    main()
