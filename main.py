#!/usr/bin/env python3
"""
Research Bot Army — entry point.

Usage:
  python main.py            # Start scheduler + web dashboard
  python main.py --now      # Run one research cycle immediately and exit
  python main.py --no-api   # Start scheduler only (no web dashboard)
"""
import logging
import logging.handlers
import sys
import threading
from pathlib import Path

# Ensure src/ is on the path whether run via systemd (PYTHONPATH set) or directly
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.config import load_config
from core.database import Database


def setup_logging(config):
    logs_dir = config.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "research-bot.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    # Rotating file handler — caps at 5 MB × 3 files = 15 MB max
    fh = logging.handlers.RotatingFileHandler(
        str(log_file), maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)


def start_dashboard(config, db):
    """Start the FastAPI web dashboard in a background thread."""
    try:
        import uvicorn
        from api.app import app
        from api.routes import runs_routes, reports_routes

        # Inject shared state into route handlers
        runs_routes.init(db, config)
        reports_routes.init(db)

        host = config.dashboard.host
        port = config.dashboard.port

        logger = logging.getLogger(__name__)
        logger.info(f"Starting web dashboard on http://{host}:{port}")

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="warning",  # suppress uvicorn access logs from cluttering output
        )
    except ImportError:
        logging.getLogger(__name__).warning(
            "FastAPI/uvicorn not installed — dashboard disabled. "
            "Run: pip install fastapi uvicorn"
        )
    except Exception as exc:
        logging.getLogger(__name__).error(f"Dashboard failed to start: {exc}", exc_info=True)


def main():
    config = load_config()
    setup_logging(config)

    logger = logging.getLogger(__name__)
    logger.info(f"Research Bot Army starting for: {config.product.name}")

    if not config.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY is not set. Edit .env and restart.")
        sys.exit(1)

    db = Database(config)

    run_now = "--now" in sys.argv
    no_api = "--no-api" in sys.argv

    if run_now or config.schedule.run_on_start:
        logger.info("Running initial research cycle...")
        from core.orchestrator import run_research_cycle

        # Register a run record so the dashboard can show it
        from datetime import datetime
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S") + "-startup"
        db.create_run(run_id, "")

        report = run_research_cycle(config, db, run_id=run_id)
        print("\n" + "=" * 70)
        print(report)
        print("=" * 70 + "\n")

    if run_now:
        logger.info("--now flag set; exiting after single run.")
        return

    # Start web dashboard in a background thread (unless disabled)
    if not no_api and config.dashboard.enabled:
        dash_thread = threading.Thread(
            target=start_dashboard,
            args=(config, db),
            daemon=True,
            name="dashboard",
        )
        dash_thread.start()

    from core.scheduler import start
    start(config, db)


if __name__ == "__main__":
    main()
