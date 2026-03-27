# Research Bot Army — User Manual

## Table of Contents

1. [Overview](#1-overview)
2. [What You Need Before Starting](#2-what-you-need-before-starting)
3. [Server Setup (Digital Ocean)](#3-server-setup-digital-ocean)
4. [Deploying the Bot Army](#4-deploying-the-bot-army)
5. [Running the Installer](#5-running-the-installer)
6. [The Web Dashboard](#6-the-web-dashboard)
7. [Configuring Your Product](#7-configuring-your-product)
8. [Managing Workflows](#8-managing-workflows)
9. [Setting Up API Keys](#9-setting-up-api-keys)
10. [Setting Up Delivery Channels](#10-setting-up-delivery-channels)
11. [Starting and Managing the Service](#11-starting-and-managing-the-service)
12. [Understanding the Daily Report](#12-understanding-the-daily-report)
13. [Monitoring and Logs](#13-monitoring-and-logs)
14. [Running a Manual Research Cycle](#14-running-a-manual-research-cycle)
15. [Updating Your Configuration](#15-updating-your-configuration)
16. [Troubleshooting](#16-troubleshooting)
17. [Updating to a New Version](#17-updating-to-a-new-version)
18. [Cost Estimates](#18-cost-estimates)

---

## 1. Overview

Research Bot Army is a self-hosted system that automatically researches your product and market. Assign a task and walk away — agents run asynchronously in the background while you monitor progress from any device via the built-in web dashboard.

Every research cycle delivers a briefing covering:

- **News** — what's being written about your market
- **Competitor changes** — pricing or website updates at your competitors
- **Community sentiment** — what people are saying on Reddit and review sites
- **Trends** — search interest and industry buzz on HackerNews

Claude (Anthropic) reads all the raw data and writes a clean, concise summary with action items.

Everything runs on a server you control. Your data never leaves your infrastructure.

---

## 2. What You Need Before Starting

### Required
- **Anthropic API key** — get one at [console.anthropic.com](https://console.anthropic.com). Powers the AI report generation (~$0.01–0.05 per run).
- **A Digital Ocean account** — [digitalocean.com](https://digitalocean.com). A basic $6–12/month droplet is sufficient.
- **SSH access** to your droplet.

### Recommended (free tiers available)
- **NewsAPI key** — [newsapi.org](https://newsapi.org) — free tier: 100 requests/day. Gives much better news coverage than the RSS fallback.
- **SerpAPI key** — [serpapi.com](https://serpapi.com) — free tier: 100 searches/month. Enables review site scraping (Trustpilot, G2, Capterra).

### Optional (for report delivery)
You need at least one of:
- A **Telegram bot** (free, setup in Section 10)
- A **Slack workspace** with incoming webhooks (free)
- An **email address** with SMTP access (Gmail works well)

---

## 3. Server Setup (Digital Ocean)

### Create a Droplet

1. Log into [digitalocean.com](https://digitalocean.com)
2. Click **Create → Droplets**
3. Choose:
   - **Image:** Ubuntu 24.04 LTS
   - **Size:** Basic — 1 GB RAM / 1 CPU / 25 GB SSD (~$6/month)
   - **Region:** Choose one close to you
   - **Authentication:** SSH Key (recommended) or Password
4. Click **Create Droplet**
5. Note the droplet's IP address

### Connect via SSH

On Mac/Linux:
```bash
ssh root@YOUR_DROPLET_IP
```

On Windows (PowerShell):
```powershell
ssh root@YOUR_DROPLET_IP
```

---

## 4. Deploying the Bot Army

Copy the project files from your local machine to the server.

### On Mac/Linux — use the deploy script:
```bash
bash deploy.sh root@YOUR_DROPLET_IP
```

### On Windows — use PowerShell:

First, create the directory on the server (in your SSH session):
```bash
mkdir -p /opt/research-bot-army
```

Then in a PowerShell window on your local machine:
```powershell
scp -r "C:\path\to\Research Bot Army\." root@YOUR_DROPLET_IP:/opt/research-bot-army/
```

---

## 5. Running the Installer

In your SSH session on the server:

```bash
cd /opt/research-bot-army
bash install.sh
```

The installer will:

1. Check your Python version and install system dependencies
2. Add 1 GB swap if your droplet has only 1 GB RAM
3. Create a Python virtual environment and install all dependencies
4. Ask for your API keys interactively (Anthropic required, NewsAPI and SerpAPI optional)
5. Ask for delivery channel credentials (Telegram, Slack, or email)
6. Open port 8080 in the firewall for the web dashboard
7. Install and enable the systemd service
8. Optionally start the service immediately

When complete, the installer prints your server's IP and the dashboard URL:
```
Web dashboard: http://YOUR_IP:8080
```

---

## 6. The Web Dashboard

Once the service is running, open a browser and go to:
```
http://YOUR_DROPLET_IP:8080
```

The dashboard has five tabs:

### 📊 Overview
- System status (last run, next scheduled run, active workflows)
- **Run Now** button — select a workflow and trigger an async research cycle
- Live progress panel showing agents moving through stages in real time
- Recent run history

### 🏭 Factory — Mission Control
A visual pipeline showing your research workflow in real time.

**Pipeline stages:**
```
READY → FETCHING → DATA IN → CLAUDE → SHIPPED
```

Each research agent appears as a pixel-art character that moves between stages as it works. The **Workflow Architecture** section below the pipeline renders a visual tree of your `config.yml` — your product at the root, each workflow as a branch showing its assigned agents, team manager, schedule, and objectives.

### ⚙️ Config
Edit your entire configuration without touching YAML:
- Product name, description, category
- Keywords (tag input — press Enter to add)
- Competitors (add/remove rows)
- Subreddits to monitor
- Global research objectives
- Schedule (hour, minute, timezone)
- Agent toggles and limits
- Delivery channels

Click **Save Config** when done. Restart the service to apply schedule changes.

### 🔄 Workflows
Define named research campaigns. Each workflow has:
- A name and description
- A selection of agents (News, Competitor, Reviews, Trends)
- A team manager / lead name (for context in reports)
- Per-workflow objectives that guide Claude's analysis
- An independent schedule
- A max workers setting (keep ≤ 2 on a 1 GB droplet)
- An enable/disable toggle

Click **Save Workflows** to persist. Enabled workflows run on their own schedule in addition to the default cycle. Any workflow can also be triggered manually from the Overview tab.

### ▶ Runs
Full history of all research runs with status badges, duration, and a detail modal showing the event log for each run.

### 📋 Reports
Browse all past reports with date, workflow, and token count. Click **Read** to open the full markdown report. Click **Download .md** to save it locally.

---

## 7. Configuring Your Product

You can edit configuration in the dashboard's **Config tab** (recommended) or directly on the server:

```bash
nano /opt/research-bot-army/config.yml
```

### Product Section

```yaml
product:
  name: "Your Product Name"
  description: "One sentence describing your product"
  category: "SaaS"
  keywords:
    - "your primary keyword"
    - "your brand name"
    - "competitor category term"
  competitors:
    - name: "Competitor A"
      url: "https://competitor-a.com/pricing"
  review_subreddits:
    - "startups"
    - "SaaS"
```

- **name** — used in report titles and the AI prompt
- **description** — helps Claude frame the analysis
- **category** — e.g. `"consumer electronics"`, `"SaaS"`, `"mobile app"`
- **keywords** — 3–6 terms used by news and review agents; most specific first
- **competitors** — use the pricing page if they have one; change detection runs on these URLs
- **review_subreddits** — where your target audience discusses your market

### Research Objectives Section

```yaml
objectives:
  - "Identify emerging market opportunities before competitors do"
  - "Monitor and respond to competitive threats in real time"
  - "Track customer sentiment trends across all channels"
```

These are included in the Claude prompt to focus analysis on what matters most to you. Add up to 5–6 specific objectives.

### Schedule Section

```yaml
schedule:
  hour: 7        # UTC hour (7 = 7:00 AM UTC)
  minute: 0
  timezone: "UTC"
  run_on_start: true
```

Time is in UTC. US Eastern = UTC−5, so `hour: 12` = 7 AM Eastern. Set `run_on_start: true` to get a report immediately when the service starts.

### Dashboard Section

```yaml
dashboard:
  enabled: true
  host: "0.0.0.0"
  port: 8080
```

Change `port` if 8080 is in use. Set `enabled: false` to run headless (no web UI).

### Agents Section

```yaml
agents:
  news:
    enabled: true
    max_articles: 15
  competitor:
    enabled: true
    timeout_seconds: 25
  reviews:
    enabled: true
    max_posts: 20
  trends:
    enabled: true
    hn_stories: 10
```

Disable any agent with `enabled: false`. These are the global defaults; individual workflows can override which agents they use.

After any manual config change, restart the service:
```bash
systemctl restart research-bot
```

---

## 8. Managing Workflows

Workflows are named research campaigns you can run on a schedule or on demand.

### Adding a Workflow (Dashboard)

1. Go to the **Workflows tab**
2. Click **+ Add Workflow**
3. Fill in:
   - **Name** — e.g. "Daily Market Brief"
   - **Description** — what this workflow monitors
   - **Agents** — click to select which agents run (News, Competitor, Reviews, Trends)
   - **Team Manager** — a label for who "owns" this workflow (shown in Factory view and reports)
   - **Schedule** — UTC hour and minute for automatic runs
   - **Max Workers** — parallel agent threads; keep at 2 for a 1 GB droplet
   - **Objectives** — specific goals for Claude's analysis on this workflow
   - **Enabled toggle** — only enabled workflows run on schedule
4. Click **Save Workflows**

### Running a Workflow On Demand

1. Go to the **Overview tab**
2. Select the workflow from the dropdown
3. Click **▶ Run Now**

The run executes asynchronously. Monitor live progress in the panel below the button, or switch to the **Factory tab** to watch the pipeline.

### Workflow Architecture (YAML)

Workflows are stored in `config.yml` under the `workflows:` key:

```yaml
workflows:
  - name: "Daily Market Brief"
    description: "Full daily intelligence across all channels"
    agents: [news, competitor, reviews, trends]
    manager: "Market Intelligence Lead"
    max_workers: 2
    objectives:
      - "Identify emerging market opportunities"
      - "Track competitor pricing and feature changes"
    schedule:
      hour: 7
      minute: 0
    enabled: true
```

---

## 9. Setting Up API Keys

All secrets go in the `.env` file on the server:

```bash
nano /opt/research-bot-army/.env
```

### Anthropic API Key (Required)

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Click **API Keys → Create Key**
3. Copy the key (starts with `sk-ant-`)
4. Add to `.env`:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

### NewsAPI Key (Optional but Recommended)

1. Go to [newsapi.org](https://newsapi.org) and sign up for free
2. Your API key is on the dashboard
3. Add to `.env`:
   ```
   NEWS_API_KEY=your-newsapi-key
   ```

### SerpAPI Key (Optional)

1. Go to [serpapi.com](https://serpapi.com) and sign up
2. Add to `.env`:
   ```
   SERP_API_KEY=your-serpapi-key
   ```

---

## 10. Setting Up Delivery Channels

### Telegram

**Step 1 — Create a bot:**
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. BotFather gives you a token like `123456789:ABCdef...`
4. Add to `.env`: `TELEGRAM_BOT_TOKEN=123456789:ABCdef...`

**Step 2 — Get your Chat ID:**
1. Start a conversation with your bot in Telegram
2. Visit `https://api.telegram.org/botTOKEN/getUpdates` in a browser
3. Find the `"id"` number inside `"chat"` in the JSON
4. Add to `.env`: `TELEGRAM_CHAT_ID=123456789`

**Step 3 — Enable in Config tab or config.yml:**
```yaml
delivery:
  telegram:
    enabled: true
```

### Slack

**Step 1 — Create an Incoming Webhook:**
1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App → From Scratch**
2. Enable **Incoming Webhooks** and add a webhook to your chosen channel
3. Copy the webhook URL
4. Add to `.env`: `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...`

**Step 2 — Enable:**
```yaml
delivery:
  slack:
    enabled: true
```

### Email (Gmail)

**Step 1 — Create a Gmail App Password:**
1. Google Account → Security → **2-Step Verification** (enable if needed)
2. Security → **App Passwords** → generate one for Mail
3. Add to `.env`:
   ```
   EMAIL_ADDRESS=youraddress@gmail.com
   EMAIL_PASSWORD=abcd efgh ijkl mnop
   ```

**Step 2 — Enable:**
```yaml
delivery:
  email:
    enabled: true
    to_addresses:
      - "you@example.com"
```

---

## 11. Starting and Managing the Service

```bash
systemctl start research-bot      # Start
systemctl stop research-bot       # Stop
systemctl restart research-bot    # Restart (required after config changes)
systemctl status research-bot     # Check status
systemctl enable research-bot     # Auto-start on reboot (done by installer)
```

### Entry Point Flags

```bash
# Start scheduler + web dashboard (default)
venv/bin/python main.py

# Run one cycle immediately and exit (no dashboard, no scheduler)
venv/bin/python main.py --now

# Start scheduler only, no web dashboard
venv/bin/python main.py --no-api
```

---

## 12. Understanding the Daily Report

The report is generated by Claude and structured into six sections:

**Executive Summary** — 2–3 sentences on what matters most today.

**News & Industry** — top 3–5 stories with a one-line takeaway each.

**Competitor Watch** — status of each configured competitor. Pages that changed since the last run are flagged as **CHANGED**. Pricing found on the page is extracted and listed.

**Community Pulse** — what real people are saying on Reddit and review sites. Surfaces complaints, questions, comparisons, and praise.

**Trends** — Google Trends interest scores for your keywords, and relevant HackerNews stories.

**Today's Action Items** — 1–3 concrete things worth acting on based only on today's data.

Report length: 400–600 words. Token cost: ~1500–2500 tokens per run.

---

## 13. Monitoring and Logs

### Via the Dashboard

The **Runs tab** shows full run history with status and event logs. The **Factory tab** shows live pipeline state during an active run.

### Via the Server

```bash
# Live log stream
tail -f /opt/research-bot-army/logs/service.log

# View recent entries
tail -100 /opt/research-bot-army/logs/service.log

# systemd journal
journalctl -u research-bot -f
```

### A Healthy Run Looks Like This

```
INFO: === Research cycle started: My Product run_id=20260327T070000-startup ===
INFO: Agent news: success (15 items, 3.2s)
INFO: Agent competitor: success (3 items, 8.1s)
INFO: Agent reviews: success (12 items, 4.5s)
INFO: Agent trends: success (5 items, 6.3s)
INFO: Calling Claude to synthesize report...
INFO: Report generated: 2341 chars, 1823 tokens
INFO: === Research cycle complete (1823 tokens) ===
```

If an agent shows `failed`, the run still completes — Claude just has less data.

---

## 14. Running a Manual Research Cycle

**Via the Dashboard:** Go to Overview, select a workflow (or leave blank for default), click **▶ Run Now**.

**Via the server:**
```bash
cd /opt/research-bot-army
venv/bin/python main.py --now
```

The report prints to the terminal and is delivered to your configured channels.

---

## 15. Updating Your Configuration

**Via the Dashboard (recommended):**
1. Open the **Config tab** or **Workflows tab**
2. Make changes
3. Click **Save Config** or **Save Workflows**
4. Restart the service to apply schedule changes: `systemctl restart research-bot`

**Via the server directly:**
```bash
nano /opt/research-bot-army/config.yml
systemctl restart research-bot
```

To add or change API keys:
```bash
nano /opt/research-bot-army/.env
systemctl restart research-bot
```

---

## 16. Troubleshooting

### Dashboard won't load at http://YOUR_IP:8080
- Check port 8080 is open: `ufw status` — should show `8080/tcp ALLOW`
- If not: `ufw allow 8080/tcp`
- Check the service is running: `systemctl status research-bot`

### Service won't start
```bash
systemctl status research-bot
tail -50 /opt/research-bot-army/logs/service.log
```
Most common cause: missing or incorrect `ANTHROPIC_API_KEY` in `.env`.

### No report being delivered
1. Check at least one delivery channel is `enabled: true` in Config tab
2. Check credentials in `.env` are correct
3. Run `venv/bin/python main.py --now` and look for delivery errors in output

### "Bad credentials" from Telegram
- Double-check `TELEGRAM_BOT_TOKEN` in `.env`
- Make sure you started a conversation with your bot in Telegram
- Re-check Chat ID using the `getUpdates` URL in Section 10

### Competitor agent returning no prices
Most sites use JavaScript to render prices. The agent extracts text-visible prices only. It will still detect page changes even when it can't extract price figures.

### Google Trends failing
pytrends is unofficial and Google rate-limits it. If it fails, the bot continues without it. Trends data is cached for 6 hours to reduce rate-limit risk.

### Out of memory errors
```bash
# Check if OOM killer is involved
dmesg | grep -i "killed process"

# Add more swap
fallocate -l 2G /swapfile2
chmod 600 /swapfile2
mkswap /swapfile2
swapon /swapfile2
```

---

## 17. Updating to a New Version

**1. Pull the latest code on your local machine:**
```bash
git pull origin main
```

**2. Redeploy to the server:**
```bash
bash deploy.sh root@YOUR_DROPLET_IP
```

The installer will update dependencies and restart the service. Your `.env` and `data/` (database) are preserved.

---

## 18. Cost Estimates

| Item | Cost |
|---|---|
| Digital Ocean 1 GB droplet | ~$6–12/month |
| Claude API (~2000–4000 tokens/day) | ~$0.01–0.05/day (~$0.30–1.50/month) |
| NewsAPI (free tier: 100 req/day) | $0 |
| SerpAPI (free tier: 100 searches/month) | $0 |
| Telegram / Slack / Email | $0 |
| **Total** | **~$7–15/month** |
