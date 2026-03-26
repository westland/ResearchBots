# Research Bot Army

A self-hosted, always-on market intelligence system that runs a daily "army" of AI research agents on your product and market, then delivers a synthesized briefing to your inbox, Telegram, or Slack — every morning.

Built with Python and Claude (Anthropic), deployed on a Digital Ocean Ubuntu droplet.

---

## What It Does

Every day at a scheduled time, four specialized research agents wake up and go to work:

| Agent | What It Does |
|---|---|
| **News Agent** | Pulls articles from NewsAPI and Google News RSS matching your product keywords |
| **Competitor Agent** | Scrapes your competitor URLs, detects pricing and content changes since the last run |
| **Reviews Agent** | Searches Reddit and review sites (via SerpAPI) for community mentions and sentiment |
| **Trends Agent** | Queries Google Trends and HackerNews for search interest and industry buzz |

All findings are fed to **Claude (claude-sonnet-4-6)** which synthesizes them into a clean, actionable 400–600 word daily briefing with sections for executive summary, news, competitor watch, community pulse, trends, and action items.

The report is stored in a local SQLite database and delivered to any combination of **Telegram**, **Slack**, and **email**.

---

## Architecture

```
main.py  (entry point)
│
├── core/scheduler.py       APScheduler — triggers daily at configured time
│
└── core/orchestrator.py    Coordinates the full research cycle
    │
    ├── agents/
    │   ├── news_agent.py       NewsAPI + Google News RSS
    │   ├── competitor_agent.py BeautifulSoup scraping + change detection
    │   ├── reviews_agent.py    Reddit JSON API + SerpAPI
    │   └── trends_agent.py     Google Trends (pytrends) + HackerNews
    │
    ├── synthesis/
    │   └── claude_synthesizer.py   Anthropic SDK → claude-sonnet-4-6
    │
    ├── delivery/
    │   ├── telegram_delivery.py
    │   ├── slack_delivery.py
    │   └── email_delivery.py
    │
    └── core/database.py    SQLite (WAL mode) — reports, snapshots, agent state
```

Agents run in parallel (ThreadPoolExecutor, max 2 workers) for speed while staying within the 1 GB RAM budget of a basic droplet. Each agent fails gracefully — if one errors, the others continue and the report still generates.

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| AI / LLM | Anthropic Claude API (`claude-sonnet-4-6`) |
| Scheduling | APScheduler 3.x (BlockingScheduler) |
| Web scraping | requests + BeautifulSoup4 + lxml |
| News feeds | NewsAPI, Google News RSS (feedparser) |
| Search / reviews | SerpAPI (optional) |
| Trends | pytrends (Google Trends), HackerNews Algolia API |
| Database | SQLite with WAL mode (stdlib) |
| Delivery | Telegram Bot API, Slack Webhooks, smtplib |
| Process manager | systemd |
| Hosting | Digital Ocean Ubuntu 24.04 droplet |

---

## Project Structure

```
Research Bot Army/
├── main.py                     Entry point (--now flag for manual runs)
├── config.yml                  Product & market configuration (edit this)
├── .env.example                Template for API keys and secrets
├── requirements.txt            Python dependencies
├── install.sh                  Interactive server installer
├── deploy.sh                   One-command deploy from local machine
├── research-bot.service        systemd unit file
├── data/                       SQLite database (created at runtime)
├── logs/                       Log files (created at runtime)
└── src/
    ├── agents/
    │   ├── base_agent.py       AgentResult dataclass + BaseAgent ABC
    │   ├── news_agent.py
    │   ├── competitor_agent.py
    │   ├── reviews_agent.py
    │   └── trends_agent.py
    ├── core/
    │   ├── config.py           AppConfig dataclass + config loader
    │   ├── database.py         SQLite wrapper with threading lock
    │   ├── orchestrator.py     Main research cycle coordinator
    │   └── scheduler.py        APScheduler setup + SIGTERM handler
    ├── delivery/
    │   ├── telegram_delivery.py
    │   ├── slack_delivery.py
    │   └── email_delivery.py
    ├── synthesis/
    │   └── claude_synthesizer.py
    └── utils/
        └── http_client.py      Shared requests.Session with retry adapter
```

---

## Quick Start

**Prerequisites:**
- A Digital Ocean Ubuntu 24.04 droplet (1 GB RAM / 25 GB minimum)
- An [Anthropic API key](https://console.anthropic.com)
- SSH access to the droplet

**1. Copy files to your droplet:**

On Mac/Linux:
```bash
bash deploy.sh root@YOUR_DROPLET_IP
```

On Windows (PowerShell):
```powershell
scp -r ".\." root@YOUR_DROPLET_IP:/opt/research-bot-army/
```

**2. SSH in and run the installer:**
```bash
ssh root@YOUR_DROPLET_IP
cd /opt/research-bot-army
bash install.sh
```

**3. Configure your product:**
```bash
nano /opt/research-bot-army/config.yml
systemctl restart research-bot
```

See the [User Manual](USER_MANUAL.md) for full setup instructions.

---

## Useful Commands (on the server)

```bash
# View live logs
tail -f /opt/research-bot-army/logs/service.log

# Run a research cycle immediately (without waiting for schedule)
cd /opt/research-bot-army && venv/bin/python main.py --now

# Restart the service after config changes
systemctl restart research-bot

# Check service status
systemctl status research-bot
```

---

## License

CC0 1.0 Universal — public domain. Use it for anything.
