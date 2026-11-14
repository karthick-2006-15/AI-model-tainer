"""
JARVIS Central API Gateway & ASGI Application
Entry point for REST APIs and WebSocket communication channels.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core.config.settings import settings
from storage.db.connection import init_db
from api.routers import system, sessions, voice, chat, memory, automation, files, mobile, research, tasks, vision, scheduler, integrations
from api.websockets import hud_stream, audio_stream
from modules.mobile import bridge as mobile_bridge
import logging
import os

# Configure structured logging
logging.basicConfig(
    level=logging.DEBUG if settings.JARVIS_DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("jarvis.core")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle manager."""
    logger.info("Initializing JARVIS Database & Subsystems...")
    init_db()
    logger.info("Database tables initialized successfully.")
    yield
    logger.info("JARVIS Core shutting down cleanly.")


app = FastAPI(
    title="JARVIS Personal AI Operating System",
    description="Intelligent, voice-controlled personal operating system connecting Windows and Android.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure Cross-Origin Resource Sharing (CORS) for UI and Mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits localhost Vite frontend and mobile network origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST routers
app.include_router(system.router)
app.include_router(sessions.router)
app.include_router(voice.router)
app.include_router(chat.router)
app.include_router(memory.router)
app.include_router(automation.router)
app.include_router(files.router)
app.include_router(mobile.router)
app.include_router(research.router)
app.include_router(tasks.router)
app.include_router(vision.router)
app.include_router(scheduler.router)
app.include_router(integrations.router)

# Mount WebSocket routers
app.include_router(hud_stream.router)
app.include_router(audio_stream.router)
app.include_router(mobile_bridge.router)

# Serve built frontend if available
ui_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "dist")
if os.path.exists(ui_dist):
    app.mount("/", StaticFiles(directory=ui_dist, html=True), name="static_hud")
else:
    @app.get("/")
    async def root():
        return {
            "system": "JARVIS Personal AI Operating System",
            "status": "online",
            "documentation": "/docs",
            "telemetry_stream": "/ws/hud",
            "health_endpoint": "/api/system/health"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.JARVIS_HOST,
        port=settings.JARVIS_PORT,
        reload=settings.JARVIS_DEBUG
    )
