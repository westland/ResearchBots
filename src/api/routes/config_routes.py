"""
Config API routes — read and update config.yml via the dashboard.
"""
import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yml"

router = APIRouter()


def _load_raw() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_raw(data: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


@router.get("/config")
def get_config():
    """Return current config.yml as JSON."""
    try:
        return _load_raw()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
def save_config(body: dict):
    """
    Replace the full config.yml contents. The dashboard sends back
    the full config object after the user edits it.
    """
    try:
        # Basic sanity: must have product.name
        if not body.get("product", {}).get("name"):
            raise HTTPException(status_code=400, detail="product.name is required")
        _save_raw(body)
        return {"ok": True, "message": "Config saved. Restart the service to apply schedule changes."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/raw")
def get_config_raw():
    """Return raw YAML text."""
    try:
        return {"yaml": CONFIG_PATH.read_text(encoding="utf-8")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
