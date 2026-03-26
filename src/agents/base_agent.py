import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from core.config import AppConfig
from core.database import Database


@dataclass
class AgentResult:
    agent_name: str
    status: Literal["success", "failed", "skipped"]
    data: list = field(default_factory=list)
    error: str | None = None
    duration_seconds: float = 0.0

    @property
    def item_count(self) -> int:
        return len(self.data)

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "data": self.data,
            "error": self.error,
            "duration_seconds": round(self.duration_seconds, 2),
            "item_count": self.item_count,
        }


class BaseAgent(ABC):
    def __init__(self, config: AppConfig, db: Database):
        self.config = config
        self.db = db
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def _fetch(self) -> list:
        """Fetch and return normalized data items. May raise."""
        ...

    def run(self) -> AgentResult:
        """Execute the agent safely — never raises."""
        start = time.monotonic()
        try:
            data = self._fetch()
            duration = time.monotonic() - start
            self.logger.info(f"{self.name}: {len(data)} items in {duration:.1f}s")
            return AgentResult(
                agent_name=self.name,
                status="success",
                data=data,
                duration_seconds=duration,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            self.logger.error(f"{self.name} failed after {duration:.1f}s: {exc}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                status="failed",
                error=str(exc),
                duration_seconds=duration,
            )
