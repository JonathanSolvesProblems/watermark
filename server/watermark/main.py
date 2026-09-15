"""ASGI entry point: `uvicorn watermark.main:app --port 8000`."""
from __future__ import annotations

import logging
import os

from .app import create_app

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = create_app()
