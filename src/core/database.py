import sqlite3
import json
import threading
import logging
from pathlib import Path
from datetime import datetime
from core.config import AppConfig

logger = logging.getLogger(__name__)

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT    NOT NULL,
    product     TEXT    NOT NULL,
    report_md   TEXT    NOT NULL,
    token_count INTEGER
);

CREATE TABLE IF NOT EXISTS agent_results (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id           TEXT    NOT NULL,
    agent_name       TEXT    NOT NULL,
    status           TEXT    NOT NULL,
    result_json      TEXT,
    error_msg        TEXT,
    duration_seconds REAL,
    created_at       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS competitor_snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at   TEXT NOT NULL,
    name         TEXT NOT NULL,
    url          TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    excerpt      TEXT
);

CREATE TABLE IF NOT EXISTS agent_state (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, config: AppConfig):
        db_path = config.data_dir / "research.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(db_path)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info(f"Database ready at {db_path}")

    # ---- writes (serialized) ----

    def save_report(self, product: str, report_md: str, token_count: int = 0) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO reports (created_at, product, report_md, token_count) VALUES (?,?,?,?)",
                (datetime.utcnow().isoformat(), product, report_md, token_count),
            )
            self._conn.commit()
            return cur.lastrowid

    def save_agent_result(
        self,
        run_id: str,
        agent_name: str,
        status: str,
        result: dict | None,
        error: str | None,
        duration: float,
    ):
        result_json = json.dumps(result)[:20_000] if result else None
        with self._lock:
            self._conn.execute(
                """INSERT INTO agent_results
                   (run_id, agent_name, status, result_json, error_msg, duration_seconds, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                (run_id, agent_name, status, result_json, error, duration, datetime.utcnow().isoformat()),
            )
            self._conn.commit()

    def save_competitor_snapshot(self, name: str, url: str, content_hash: str, excerpt: str):
        with self._lock:
            self._conn.execute(
                "INSERT INTO competitor_snapshots (created_at, name, url, content_hash, excerpt) VALUES (?,?,?,?,?)",
                (datetime.utcnow().isoformat(), name, url, content_hash, excerpt[:1000]),
            )
            self._conn.commit()

    def set_state(self, key: str, value: str):
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO agent_state (key, value, updated_at) VALUES (?,?,?)",
                (key, value, datetime.utcnow().isoformat()),
            )
            self._conn.commit()

    # ---- reads ----

    def get_competitor_snapshot(self, name: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM competitor_snapshots WHERE name=? ORDER BY created_at DESC LIMIT 1",
            (name,),
        ).fetchone()
        return dict(row) if row else None

    def get_state(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM agent_state WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def get_recent_reports(self, product: str, limit: int = 5) -> list:
        rows = self._conn.execute(
            "SELECT * FROM reports WHERE product=? ORDER BY created_at DESC LIMIT ?",
            (product, limit),
        ).fetchall()
        return [dict(r) for r in rows]
