import os
from pathlib import Path
from dataclasses import dataclass, field
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class ProductConfig:
    name: str
    keywords: list
    category: str = ""
    description: str = ""
    competitors: list = field(default_factory=list)
    review_subreddits: list = field(default_factory=list)


@dataclass
class ScheduleConfig:
    hour: int = 7
    minute: int = 0
    timezone: str = "UTC"
    run_on_start: bool = True


@dataclass
class AgentConfig:
    news_enabled: bool = True
    competitor_enabled: bool = True
    reviews_enabled: bool = True
    trends_enabled: bool = True
    max_articles: int = 15
    max_reddit_posts: int = 20
    competitor_timeout: int = 25
    hn_stories: int = 10


@dataclass
class DeliveryConfig:
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    slack_enabled: bool = False
    slack_webhook_url: str = ""
    email_enabled: bool = False
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_from: str = ""
    email_to: list = field(default_factory=list)
    email_password: str = ""


@dataclass
class WorkflowSchedule:
    hour: int = 7
    minute: int = 0


@dataclass
class WorkflowConfig:
    name: str
    agents: list = field(default_factory=lambda: ["news", "competitor", "reviews", "trends"])
    description: str = ""
    manager: str = ""
    objectives: list = field(default_factory=list)
    schedule: WorkflowSchedule = field(default_factory=WorkflowSchedule)
    max_workers: int = 2
    enabled: bool = True


@dataclass
class DashboardConfig:
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class AppConfig:
    product: ProductConfig
    schedule: ScheduleConfig
    agents: AgentConfig
    delivery: DeliveryConfig
    anthropic_api_key: str = ""
    news_api_key: str = ""
    serp_api_key: str = ""
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    logs_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "logs")
    workflows: list = field(default_factory=list)
    objectives: list = field(default_factory=list)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)


def load_config() -> AppConfig:
    config_path = PROJECT_ROOT / "config.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"config.yml not found at {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    p = raw.get("product", {})
    product = ProductConfig(
        name=p.get("name", "My Product"),
        keywords=p.get("keywords", []),
        category=p.get("category", ""),
        description=p.get("description", ""),
        competitors=p.get("competitors", []),
        review_subreddits=p.get("review_subreddits", ["startups"]),
    )

    s = raw.get("schedule", {})
    schedule = ScheduleConfig(
        hour=s.get("hour", 7),
        minute=s.get("minute", 0),
        timezone=s.get("timezone", "UTC"),
        run_on_start=s.get("run_on_start", True),
    )

    a = raw.get("agents", {})
    agents = AgentConfig(
        news_enabled=a.get("news", {}).get("enabled", True),
        competitor_enabled=a.get("competitor", {}).get("enabled", True),
        reviews_enabled=a.get("reviews", {}).get("enabled", True),
        trends_enabled=a.get("trends", {}).get("enabled", True),
        max_articles=a.get("news", {}).get("max_articles", 15),
        max_reddit_posts=a.get("reviews", {}).get("max_posts", 20),
        hn_stories=a.get("trends", {}).get("hn_stories", 10),
    )

    d = raw.get("delivery", {})
    tg = d.get("telegram", {})
    sl = d.get("slack", {})
    em = d.get("email", {})
    delivery = DeliveryConfig(
        telegram_enabled=tg.get("enabled", False),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        slack_enabled=sl.get("enabled", False),
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
        email_enabled=em.get("enabled", False),
        email_smtp_host=em.get("smtp_host", "smtp.gmail.com"),
        email_smtp_port=em.get("smtp_port", 587),
        email_from=os.getenv("EMAIL_ADDRESS", em.get("from_address", "")),
        email_to=em.get("to_addresses", []),
        email_password=os.getenv("EMAIL_PASSWORD", ""),
    )

    workflows = []
    for wf in raw.get("workflows", []):
        wf_sched_raw = wf.get("schedule", {})
        workflows.append(WorkflowConfig(
            name=wf.get("name", "Unnamed Workflow"),
            agents=wf.get("agents", ["news", "competitor", "reviews", "trends"]),
            description=wf.get("description", ""),
            manager=wf.get("manager", ""),
            objectives=wf.get("objectives", []),
            schedule=WorkflowSchedule(
                hour=wf_sched_raw.get("hour", 7),
                minute=wf_sched_raw.get("minute", 0),
            ),
            max_workers=wf.get("max_workers", 2),
            enabled=wf.get("enabled", True),
        ))

    db_raw = raw.get("dashboard", {})
    dashboard = DashboardConfig(
        enabled=db_raw.get("enabled", True),
        host=db_raw.get("host", "0.0.0.0"),
        port=db_raw.get("port", 8080),
    )

    return AppConfig(
        product=product,
        schedule=schedule,
        agents=agents,
        delivery=delivery,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        news_api_key=os.getenv("NEWS_API_KEY", ""),
        serp_api_key=os.getenv("SERP_API_KEY", ""),
        workflows=workflows,
        objectives=raw.get("objectives", []),
        dashboard=dashboard,
    )
