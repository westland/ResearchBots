# Research Bot Army

A self-hosted, always-on market intelligence system that runs an "army" of AI research agents on your product and market, then delivers synthesized briefings to your inbox, Telegram, or Slack — on a schedule or on demand.

Built with Python and Claude (Anthropic). Deployed on a Digital Ocean Ubuntu droplet. Managed through a built-in web dashboard.

---

## What It Does

Assign a research task and walk away. Agents run asynchronously — kick off a workflow from your laptop, close the lid, and monitor progress from your phone via the web dashboard.

Four specialized agents gather intelligence in parallel:

| Agent | What It Does |
|---|---|
| **News Agent** | Pulls articles from NewsAPI and Google News RSS matching your keywords |
| **Competitor Agent** | Scrapes competitor URLs, detects pricing and content changes |
| **Reviews Agent** | Searches Reddit and review sites for community mentions and sentiment |
| **Trends Agent** | Queries Google Trends and HackerNews for search interest and buzz |

All findings are fed to **Claude (claude-sonnet-4-6)** which synthesizes them into a clean, actionable briefing with executive summary, competitor watch, community pulse, trends, and action items.

Reports are stored in SQLite and delivered to any combination of **Telegram**, **Slack**, and **email**.

---

## v0.77 — Web Dashboard & Workflow Management

Version 0.77 adds a full web dashboard accessible at `http://YOUR_SERVER:8080`:

### 🏭 Factory View — Mission Control
A live pipeline visualization showing your agents as pixel-art characters moving through research stages in real time:

```
READY → FETCHING → DATA IN → CLAUDE → SHIPPED
```

Each agent has a unique animated sprite. The view also renders a live **Workflow Architecture diagram** that mirrors your `config.yml` structure — product at the root, each workflow as a branch with its assigned agents, manager, schedule, and objectives.

### ⚙️ Config Editor
Edit your entire `config.yml` through a form — no YAML editing required:
- Product name, description, category
- Keywords and subreddits (tag-style input)
- Competitors (add/remove rows with name + URL)
- Schedule, agent toggles, delivery channels
- Global research objectives

### 🔄 Workflow Manager
Define named research campaigns, each with:
- A dedicated set of agents
- A team manager / lead name
- Per-workflow objectives that guide Claude's analysis
- An independent schedule and worker count
- Enable/disable toggle

### ▶ Async Task Assignment
Trigger any workflow on demand from the dashboard. Runs execute in the background — monitor live progress events as agents move through the pipeline. Full run history with status, duration, and event logs.

### 📋 Reports Viewer
Browse all past reports, read full markdown, download as `.md`.

---

## Architecture

```
main.py  (entry point: --now, --no-api flags)
│
├── core/scheduler.py        APScheduler — daily cron + workflow schedules
├── core/orchestrator.py     Workflow-aware research cycle + progress events
│
├── agents/
│   ├── news_agent.py        NewsAPI + Google News RSS
│   ├── competitor_agent.py  BeautifulSoup scraping + change detection
│   ├── reviews_agent.py     Reddit JSON API + SerpAPI
│   └── trends_agent.py      Google Trends (pytrends) + HackerNews
│
├── synthesis/
│   └── claude_synthesizer.py    Anthropic SDK → claude-sonnet-4-6
│
├── delivery/
│   ├── telegram_delivery.py
│   ├── slack_delivery.py
│   └── email_delivery.py
│
├── api/                     FastAPI web dashboard (port 8080)
│   ├── app.py
│   └── routes/
│       ├── config_routes.py     GET/PUT config.yml
│       ├── runs_routes.py       Trigger + monitor runs, /factory state
│       └── reports_routes.py    Browse past reports
│
├── core/database.py         SQLite (WAL) — reports, runs, events, snapshots
│
└── static/                  Web dashboard frontend (vanilla JS, no build step)
    ├── index.html
    ├── css/style.css
    └── js/app.js
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| AI / LLM | Anthropic Claude API (`claude-sonnet-4-6`) |
| Web Dashboard | FastAPI + uvicorn (port 8080) |
| Scheduling | APScheduler 3.x |
| Web scraping | requests + BeautifulSoup4 + lxml |
| News feeds | NewsAPI, Google News RSS (feedparser) |
| Search / reviews | SerpAPI (optional) |
| Trends | pytrends (Google Trends), HackerNews Algolia API |
| Database | SQLite with WAL mode |
| Delivery | Telegram Bot API, Slack Webhooks, smtplib |
| Process manager | systemd |
| Hosting | Digital Ocean Ubuntu 24.04 droplet |

---

## Project Structure

```
Research Bot Army/
├── main.py                      Entry point (--now, --no-api flags)
├── config.yml                   Product, workflows, objectives, schedule
├── .env.example                 Template for API keys and secrets
├── requirements.txt             Python dependencies
├── install.sh                   Interactive server installer
├── deploy.sh                    One-command deploy from local machine
├── research-bot.service         systemd unit file
├── data/                        SQLite database (created at runtime)
├── logs/                        Log files (created at runtime)
├── static/                      Web dashboard frontend
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
└── src/
    ├── agents/
    │   ├── base_agent.py
    │   ├── news_agent.py
    │   ├── competitor_agent.py
    │   ├── reviews_agent.py
    │   └── trends_agent.py
    ├── api/
    │   ├── app.py
    │   └── routes/
    │       ├── config_routes.py
    │       ├── runs_routes.py
    │       └── reports_routes.py
    ├── core/
    │   ├── config.py            AppConfig + WorkflowConfig + DashboardConfig
    │   ├── database.py          SQLite wrapper (runs, events, reports tables)
    │   ├── orchestrator.py      Workflow-aware cycle + progress callbacks
    │   └── scheduler.py         APScheduler + SIGTERM handler
    ├── delivery/
    │   ├── telegram_delivery.py
    │   ├── slack_delivery.py
    │   └── email_delivery.py
    ├── synthesis/
    │   └── claude_synthesizer.py
    └── utils/
        └── http_client.py
```

---

## Quick Start

**Prerequisites:**
- A Digital Ocean Ubuntu 24.04 droplet (1 GB RAM / 25 GB minimum)
- An [Anthropic API key](https://console.anthropic.com)
- SSH access to the droplet

**Deploy to server (Mac/Linux):**
```bash
bash deploy.sh root@YOUR_DROPLET_IP
```

**Deploy to server (Windows PowerShell):**
```powershell
scp -r ".\." root@YOUR_DROPLET_IP:/opt/research-bot-army/
ssh root@YOUR_DROPLET_IP "cd /opt/research-bot-army && bash install.sh"
```

The installer handles everything: Python venv, dependencies, API key prompts, systemd service, and firewall rule for port 8080.

**Open the dashboard:**
```
http://YOUR_DROPLET_IP:8080
```

Use the **Config tab** to set your product name, keywords, and competitors — no YAML editing required.

See the [User Manual](USER_MANUAL.md) for full setup instructions.

---

## Useful Commands (on the server)

```bash
# View live logs
tail -f /opt/research-bot-army/logs/service.log

# Run a research cycle immediately
cd /opt/research-bot-army && venv/bin/python main.py --now

# Restart after config changes
systemctl restart research-bot

# Check service status
systemctl status research-bot
```

---

## Cost Estimates

| Item | Cost |
|---|---|
| Digital Ocean 1 GB droplet | ~$6–12/month |
| Claude API (~2000–4000 tokens/day) | ~$0.01–0.05/day |
| NewsAPI (free tier) | $0 |
| SerpAPI (free tier) | $0 |
| **Total** | **~$7–15/month** |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
