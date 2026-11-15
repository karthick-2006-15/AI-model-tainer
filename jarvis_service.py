"""
JARVIS Master Background Service & Auto-Start Daemon
Runs silently in the background on system startup without console windows.
Coordinates the FastAPI ASGI core and Always-On Voice Listener.
"""

import sys
import os
import time
import logging
import threading
import uvicorn

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Set working directory to project root
os.chdir(PROJECT_ROOT)

# Configure logging
LOG_DIR = os.path.join(PROJECT_ROOT, "storage", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "jarvis_service.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("jarvis.service")


def vocal_welcome():
    """Plays an initial vocal confirmation that JARVIS is online and listening."""
    try:
        from modules.voice.tts import tts_engine
        time.sleep(1.5)  # Brief pause for audio device readiness
        tts_engine.speak("JARVIS online. Standing by, sir.")
    except Exception as e:
        logger.warning(f"Vocal welcome note: {e}")


def main():
    logger.info("==================================================")
    logger.info("JARVIS Always-On Background Service Starting...")
    logger.info("==================================================")

    # Trigger vocal startup greeting in background thread
    threading.Thread(target=vocal_welcome, daemon=True).start()

    # Run Uvicorn server (which automatically activates voice_listener via lifespan)
    try:
        from api.main import app
        from core.config.settings import settings

        config = uvicorn.Config(
            app=app,
            host=settings.JARVIS_HOST,
            port=settings.JARVIS_PORT,
            log_level="info",
            access_log=False
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception as e:
        logger.critical(f"JARVIS Service encountered an error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
