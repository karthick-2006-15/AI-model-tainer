"""
Global Pytest Conftest Harness
Ensures workspace root and required subdirectories are properly resolved in sys.path,
configures global test isolation flags, and silences environment noise.
"""

import sys
import os
from pathlib import Path

# Workspace root resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure modules/media is also accessible if imported directly
MEDIA_DIR = ROOT_DIR / "modules" / "media"
if str(MEDIA_DIR) not in sys.path:
    sys.path.append(str(MEDIA_DIR))

# Environment controls for test runs
os.environ["JARVIS_TESTING"] = "1"
os.environ["JARVIS_DEBUG"] = "false"

import pytest
import asyncio

@pytest.fixture(autouse=True)
def reset_asyncio_loop():
    """Yields cleanly and ensures no hanging event loops."""
    yield
