"""
Runs API routes — trigger research runs and monitor their progress.
"""
import logging
import threading
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared state — injected by main.py at startup
_db = None
_config = None


def init(db, config):
    global _db, _config
    _db = db
    _config = config


class TriggerRequest(BaseModel):
    workflow: str = ""       # workflow name; empty = use global agent config
    agents: list[str] = []  # override: specific agents to run


@router.post("/runs")
def trigger_run(req: TriggerRequest):
    """Trigger an async research run."""
    if _db is None or _config is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]

    # Resolve workflow
    workflow = None
    if req.workflow:
        for wf in _config.workflows:
            if wf.name == req.workflow:
                workflow = wf
                break
        if workflow is None:
            raise HTTPException(status_code=404, detail=f"Workflow {req.workflow!r} not found")

    # Create run record
    _db.create_run(run_id, workflow.name if workflow else "")

    # Launch in background thread
    def _run():
        from core.orchestrator import run_research_cycle
        try:
            run_research_cycle(
                config=_config,
                db=_db,
                run_id=run_id,
                workflow=workflow,
            )
        except Exception as exc:
            logger.error(f"Run {run_id} failed: {exc}", exc_info=True)
            _db.update_run_status(run_id, "failed", str(exc))

    t = threading.Thread(target=_run, daemon=True, name=f"run-{run_id}")
    t.start()

    return {"run_id": run_id, "status": "pending", "workflow": req.workflow}


@router.get("/runs")
def list_runs(limit: int = 20):
    """List recent runs with status."""
    if _db is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"runs": _db.get_recent_runs(limit)}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    """Get run details and progress events."""
    if _db is None:
        raise HTTPException(status_code=503, detail="Service not ready")
    run = _db.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    events = _db.get_run_events(run_id)
    return {"run": run, "events": events}


@router.get("/factory")
def get_factory():
    """
    Return everything the Factory pipeline view needs:
    - latest run + events (for live agent positions)
    - workflow config (for the architecture diagram)
    - computed agent_stages map
    """
    if _db is None or _config is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    runs = _db.get_recent_runs(1)
    latest_run = runs[0] if runs else None
    events = []
    if latest_run:
        events = _db.get_run_events(latest_run["id"])

    # Derive current stage for each agent from event log
    agent_stages: dict[str, str] = {}
    if latest_run:
        if latest_run["status"] == "running":
            for ev in events:
                name = ev.get("agent_name", "")
                etype = ev.get("event_type", "")
                if not name:
                    if etype == "synthesis_started":
                        agent_stages["_claude"] = "synthesizing"
                    elif etype == "synthesis_completed":
                        agent_stages["_claude"] = "delivered"
                    continue
                if etype == "agent_started":
                    agent_stages[name] = "fetching"
                elif etype in ("agent_completed", "agent_failed"):
                    agent_stages[name] = "done"
        elif latest_run["status"] == "completed":
            # Show everyone at delivered
            workflow = latest_run.get("workflow", "")
            wf_agents = ["news", "competitor", "reviews", "trends"]
            for wf in _config.workflows:
                if wf.name == workflow:
                    wf_agents = wf.agents
                    break
            for a in wf_agents:
                agent_stages[a] = "delivered"

    workflows = [
        {
            "name": wf.name,
            "description": wf.description,
            "agents": wf.agents,
            "manager": wf.manager,
            "objectives": wf.objectives,
            "enabled": wf.enabled,
            "schedule": {"hour": wf.schedule.hour, "minute": wf.schedule.minute},
            "max_workers": wf.max_workers,
        }
        for wf in _config.workflows
    ]

    return {
        "latest_run": latest_run,
        "events": events[-30:],
        "agent_stages": agent_stages,
        "workflows": workflows,
        "objectives": _config.objectives,
        "product": _config.product.name,
        "agents_config": {
            "news": {"enabled": _config.agents.news_enabled, "max_articles": _config.agents.max_articles},
            "competitor": {"enabled": _config.agents.competitor_enabled, "timeout": _config.agents.competitor_timeout},
            "reviews": {"enabled": _config.agents.reviews_enabled, "max_posts": _config.agents.max_reddit_posts},
            "trends": {"enabled": _config.agents.trends_enabled, "hn_stories": _config.agents.hn_stories},
        },
    }


@router.get("/status")
def system_status():
    """Return system-level status for the dashboard header."""
    if _db is None or _config is None:
        return {"ready": False}

    runs = _db.get_recent_runs(1)
    last_run = runs[0] if runs else None

    enabled_workflows = [wf.name for wf in _config.workflows if wf.enabled]

    return {
        "ready": True,
        "product": _config.product.name,
        "last_run": last_run,
        "enabled_workflows": enabled_workflows,
        "schedule": {
            "hour": _config.schedule.hour,
            "minute": _config.schedule.minute,
            "timezone": _config.schedule.timezone,
        },
        "dashboard_version": "2.0",
    }
