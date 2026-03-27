import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime
from typing import Callable

from agents.news_agent import NewsAgent
from agents.competitor_agent import CompetitorAgent
from agents.reviews_agent import ReviewsAgent
from agents.trends_agent import TrendsAgent
from core.config import AppConfig, WorkflowConfig, load_config
from core.database import Database
from delivery import telegram_delivery, slack_delivery, email_delivery
from synthesis import claude_synthesizer

logger = logging.getLogger(__name__)

AGENT_TIMEOUT = 120  # seconds per agent

_AGENT_MAP = {
    "news": NewsAgent,
    "competitor": CompetitorAgent,
    "reviews": ReviewsAgent,
    "trends": TrendsAgent,
}


def run_research_cycle(
    config: AppConfig | None = None,
    db: Database | None = None,
    run_id: str | None = None,
    workflow: WorkflowConfig | None = None,
    progress_cb: Callable[[str, str, str], None] | None = None,
) -> str:
    """
    Run one full research cycle: fetch → synthesize → store → deliver.
    Returns the generated report markdown.

    Args:
        config: loaded AppConfig (loaded fresh if None)
        db: Database instance (created if None)
        run_id: unique ID for this run (generated if None)
        workflow: WorkflowConfig to use; if None, uses global agent config
        progress_cb: optional callback(event_type, agent_name, message)
    """
    if config is None:
        config = load_config()
    if db is None:
        db = Database(config)
    if run_id is None:
        run_id = datetime.utcnow().isoformat()

    def emit(event_type: str, agent_name: str = "", message: str = ""):
        db.add_run_event(run_id, event_type, agent_name, message)
        if progress_cb:
            progress_cb(event_type, agent_name, message)

    workflow_name = workflow.name if workflow else ""
    product_name = config.product.name
    logger.info(f"=== Research cycle started: {product_name} run_id={run_id} workflow={workflow_name!r} ===")

    db.update_run_status(run_id, "running")
    emit("cycle_started", message=f"Research cycle started for {product_name}")

    # Determine which agents to run
    if workflow:
        agent_keys = workflow.agents
        max_workers = max(1, min(workflow.max_workers, 4))
    else:
        cfg = config.agents
        agent_keys = []
        if cfg.news_enabled:
            agent_keys.append("news")
        if cfg.competitor_enabled:
            agent_keys.append("competitor")
        if cfg.reviews_enabled:
            agent_keys.append("reviews")
        if cfg.trends_enabled:
            agent_keys.append("trends")
        max_workers = 2

    agents = []
    for key in agent_keys:
        cls = _AGENT_MAP.get(key)
        if cls:
            agents.append(cls(config, db))
        else:
            logger.warning(f"Unknown agent key: {key!r}")

    # Run agents with bounded parallelism
    agent_data = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(agent.run): agent for agent in agents}
        for future in as_completed(futures, timeout=AGENT_TIMEOUT * max(len(agents), 1)):
            agent = futures[future]
            emit("agent_started", agent.name, f"Running {agent.name} agent")
            try:
                result = future.result(timeout=AGENT_TIMEOUT)
            except TimeoutError:
                from agents.base_agent import AgentResult
                result = AgentResult(
                    agent_name=agent.name,
                    status="failed",
                    error="Timed out",
                    duration_seconds=AGENT_TIMEOUT,
                )
            except Exception as exc:
                from agents.base_agent import AgentResult
                result = AgentResult(
                    agent_name=agent.name,
                    status="failed",
                    error=str(exc),
                )

            agent_data[result.agent_name] = result.to_dict()
            db.save_agent_result(
                run_id=run_id,
                agent_name=result.agent_name,
                status=result.status,
                result={"data": result.data},
                error=result.error,
                duration=result.duration_seconds,
            )
            status_msg = f"{result.item_count} items in {result.duration_seconds:.1f}s"
            emit(
                "agent_completed" if result.status == "success" else "agent_failed",
                result.agent_name,
                status_msg if result.status == "success" else result.error or "failed",
            )
            logger.info(
                f"Agent {result.agent_name}: {result.status} "
                f"({result.item_count} items, {result.duration_seconds:.1f}s)"
            )

    # Synthesize report
    emit("synthesis_started", message="Synthesizing report with Claude")
    try:
        # Pass workflow objectives if available
        extra_objectives = []
        if workflow and workflow.objectives:
            extra_objectives = workflow.objectives
        elif config.objectives:
            extra_objectives = config.objectives

        report, token_count = claude_synthesizer.synthesize(config, agent_data, extra_objectives)
    except Exception as exc:
        logger.error(f"Synthesis failed: {exc}", exc_info=True)
        report = _fallback_report(product_name, agent_data, str(exc))
        token_count = 0

    emit("synthesis_completed", message=f"Report generated ({token_count} tokens)")

    # Persist report
    report_id = db.save_report(product_name, report, token_count, workflow_name)
    db.link_run_report(run_id, report_id)

    # Deliver
    for channel in [telegram_delivery, slack_delivery, email_delivery]:
        try:
            channel.send(report, config)
        except Exception as exc:
            logger.error(f"Delivery ({channel.__name__}) failed: {exc}")

    db.update_run_status(run_id, "completed")
    emit("cycle_completed", message=f"Cycle complete — report #{report_id} saved")
    logger.info(f"=== Research cycle complete ({token_count} tokens) ===")
    return report


def _fallback_report(product_name: str, agent_data: dict, error: str) -> str:
    lines = [
        f"# Daily Research Report: {product_name}",
        f"_Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        f"> ⚠️ AI synthesis failed: {error}",
        "",
        "## Raw Data Summary",
    ]
    for name, data in agent_data.items():
        count = data.get("item_count", 0)
        status = data.get("status", "unknown")
        lines.append(f"- **{name}**: {status}, {count} items")
    return "\n".join(lines)
