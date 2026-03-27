"""
Reports API routes — browse and read past research reports.
"""
import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

_db = None


def init(db):
    global _db
    _db = db


@router.get("/reports")
def list_reports(limit: int = 20):
    """List recent reports (with preview, no full text)."""
    if _db is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"reports": _db.get_recent_reports(limit=limit)}


@router.get("/reports/{report_id}")
def get_report(report_id: int):
    """Return a specific report including full markdown."""
    if _db is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    report = _db.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
