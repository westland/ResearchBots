import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime

from agents.news_agent import NewsAgent
from agents.competitor_agent import CompetitorAgent
from agents.reviews_agent import ReviewsAgent
from agents.trends_agent import TrendsAgent
from core.config import AppConfig, load_config
from core.database import Database
from delivery import telegram_delivery, slack_delivery, email_delivery
from synthesis import claude_synthesizer

logger = logging.getLogger(__name__)

AGENT_TIMEOUT = 120  # seconds per agent


def run_research_cycle(config: AppConfig | None = None, db: Database | None = None) -> str:
    """
    Run one full research cycle: fetch → synthesize → store → deliver.
    Returns the generated report markdown.
    """
    if config is None:
        config = load_config()
    if db is None:
        db = Database(config)

    run_id = datetime.utcnow().isoformat()
    product_name = config.product.name
    logger.info(f"=== Research cycle started: {product_name} (run_id={run_id}) ===")

    # Build agent list based on config flags
    agent_classes = []
    cfg = config.agents
    if cfg.news_enabled:
        agent_classes.append(NewsAgent)
    if cfg.competitor_enabled:
        agent_classes.append(CompetitorAgent)
    if cfg.reviews_enabled:
        agent_classes.append(ReviewsAgent)
    if cfg.trends_enabled:
        agent_classes.append(TrendsAgent)

    agents = [cls(config, db) for cls in agent_classes]

    # Run agents with bounded parallelism (2 workers to stay memory-safe on 1 GB)
    agent_data = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(agent.run): agent for agent in agents}
        for future in as_completed(futures, timeout=AGENT_TIMEOUT * len(agents)):
            agent = futures[future]
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
            logger.info(
                f"Agent {result.agent_name}: {result.status} "
                f"({result.item_count} items, {result.duration_seconds:.1f}s)"
            )

    # Synthesize report
    try:
        report, token_count = claude_synthesizer.synthesize(config, agent_data)
    except Exception as exc:
        logger.error(f"Synthesis failed: {exc}", exc_info=True)
        report = _fallback_report(product_name, agent_data, str(exc))
        token_count = 0

    # Persist report
    db.save_report(product_name, report, token_count)

    # Deliver
    for channel in [telegram_delivery, slack_delivery, email_delivery]:
        try:
            channel.send(report, config)
        except Exception as exc:
            logger.error(f"Delivery ({channel.__name__}) failed: {exc}")

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
