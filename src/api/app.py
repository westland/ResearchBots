"""
Research Bot Army — Web Dashboard API
Serves the config editor, run management, and reports viewer.
Runs on port 8080 alongside the scheduler.
"""
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes.config_routes import router as config_router
from api.routes.runs_routes import router as runs_router
from api.routes.reports_routes import router as reports_router

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = PROJECT_ROOT / "static"

app = FastAPI(title="Research Bot Army", version="2.0")

# API routes
app.include_router(config_router, prefix="/api")
app.include_router(runs_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

# Serve static files
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Research Bot Army</h1><p>Dashboard loading...</p>")


@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
