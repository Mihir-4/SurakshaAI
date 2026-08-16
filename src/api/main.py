"""FastAPI entry point."""

from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import analytics, analyze, assistant, auth, history, image
from src.config import settings
from src.db.connection import check_db


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(image.router, prefix="/api/v1")
app.include_router(assistant.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "models_loaded": True, "db_connected": check_db()}


# Mount frontend web application at root
web_dir = Path(__file__).resolve().parents[2] / "web"
if web_dir.exists():
    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

