#!/usr/bin/env python3
"""
Research Bot Army — entry point.

Usage:
  python main.py            # Start the scheduler (runs daily + on start if configured)
  python main.py --now      # Run one research cycle immediately and exit
"""
import logging
import logging.handlers
import sys
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

    if run_now or config.schedule.run_on_start:
        logger.info("Running initial research cycle...")
        from core.orchestrator import run_research_cycle
        report = run_research_cycle(config, db)
        print("\n" + "=" * 70)
        print(report)
        print("=" * 70 + "\n")

    if run_now:
        logger.info("--now flag set; exiting after single run.")
        return

    from core.scheduler import start
    start(config, db)


if __name__ == "__main__":
    main()
