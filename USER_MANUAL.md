# Research Bot Army — User Manual

## Table of Contents

1. [Overview](#1-overview)
2. [What You Need Before Starting](#2-what-you-need-before-starting)
3. [Server Setup (Digital Ocean)](#3-server-setup-digital-ocean)
4. [Deploying the Bot Army](#4-deploying-the-bot-army)
5. [Running the Installer](#5-running-the-installer)
6. [Configuring Your Product](#6-configuring-your-product)
7. [Setting Up API Keys](#7-setting-up-api-keys)
8. [Setting Up Delivery Channels](#8-setting-up-delivery-channels)
9. [Starting and Managing the Service](#9-starting-and-managing-the-service)
10. [Understanding the Daily Report](#10-understanding-the-daily-report)
11. [Monitoring and Logs](#11-monitoring-and-logs)
12. [Running a Manual Research Cycle](#12-running-a-manual-research-cycle)
13. [Updating Your Configuration](#13-updating-your-configuration)
14. [Troubleshooting](#14-troubleshooting)
15. [Updating to a New Version](#15-updating-to-a-new-version)
16. [Cost Estimates](#16-cost-estimates)

---

## 1. Overview

Research Bot Army is a self-hosted system that automatically researches your product and market every day. You set it up once, and every morning it delivers a briefing covering:

- **News** — what's being written about your market
- **Competitor changes** — pricing or website updates at your competitors
- **Community sentiment** — what people are saying on Reddit and review sites
- **Trends** — search interest and industry buzz on HackerNews

An AI (Claude) reads all the raw data and writes you a clean, concise summary with action items.

Everything runs on a server you control. Your data never leaves your infrastructure.

---

## 2. What You Need Before Starting

### Required
- **Anthropic API key** — get one free at [console.anthropic.com](https://console.anthropic.com). This powers the AI report generation. You will be charged per report (~$0.01–0.05 per daily run depending on data volume).
- **A Digital Ocean account** — sign up at [digitalocean.com](https://digitalocean.com). A basic $6–12/month droplet is sufficient.
- **SSH access** to your droplet

### Recommended (free tiers available)
- **NewsAPI key** — [newsapi.org](https://newsapi.org) — free tier: 100 requests/day. Gives much better news coverage than the RSS fallback.
- **SerpAPI key** — [serpapi.com](https://serpapi.com) — free tier: 100 searches/month. Enables review site scraping (Trustpilot, G2, Capterra).

### Optional (for report delivery)
You need at least one of:
- A **Telegram bot** (free, setup instructions in Section 8)
- A **Slack workspace** with incoming webhooks enabled (free)
- An **email address** with SMTP access (Gmail works well)

---

## 3. Server Setup (Digital Ocean)

### Create a Droplet

1. Log into [digitalocean.com](https://digitalocean.com)
2. Click **Create → Droplets**
3. Choose:
   - **Image:** Ubuntu 24.04 LTS
   - **Size:** Basic — 1 GB RAM / 1 CPU / 25 GB SSD (~$6/month) is sufficient
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

You should see a welcome message and the `root@hostname:~#` prompt.

---

## 4. Deploying the Bot Army

You need to copy the project files from your local machine to the server.

### On Mac/Linux — use the deploy script:
```bash
bash deploy.sh root@YOUR_DROPLET_IP
```

### On Windows — use PowerShell:

First, create the directory on the server (in your SSH session):
```bash
mkdir -p /opt/research-bot-army
```

Then, in a new PowerShell window on your local machine:
```powershell
scp -r "C:\path\to\Research Bot Army\." root@YOUR_DROPLET_IP:/opt/research-bot-army/
```

When prompted, enter your server password (or it will use your SSH key automatically).

---

## 5. Running the Installer

In your SSH session on the server:

```bash
cd /opt/research-bot-army
bash install.sh
```

The installer will:

1. **Check your Python version** and install system dependencies
2. **Add swap space** if your droplet has only 1 GB RAM (prevents out-of-memory errors during pip installs)
3. **Create a Python virtual environment** and install all dependencies
4. **Ask for your API keys** interactively:
   - Anthropic API key (required)
   - NewsAPI key (optional)
   - SerpAPI key (optional)
5. **Ask for delivery channel credentials** (Telegram, Slack, or email)
6. **Install and enable the systemd service** so the bot restarts automatically if the server reboots
7. **Optionally start the service** immediately

After the installer finishes, you will see a summary with useful commands.

---

## 6. Configuring Your Product

This is the most important step. Open the configuration file:

```bash
nano /opt/research-bot-army/config.yml
```

### Product Section

```yaml
product:
  name: "Your Product Name"
```
The name of your product or brand. Used in the AI prompt and report titles.

```yaml
  description: "Brief description of what your product does"
```
One sentence describing your product. Helps Claude frame the analysis correctly.

```yaml
  category: "SaaS"
```
Your product category. Examples: `"consumer electronics"`, `"SaaS"`, `"fashion"`, `"food & beverage"`, `"mobile app"`.

```yaml
  keywords:
    - "your primary keyword"
    - "your brand name"
    - "competitor category term"
```
3–6 search terms. Put your most specific terms first. These are used by the news and reviews agents to find relevant content.

```yaml
  competitors:
    - name: "Competitor A"
      url: "https://competitor-a.com/pricing"
    - name: "Competitor B"
      url: "https://competitor-b.com"
```
Add each competitor you want to monitor. Use the specific page you care about most — a pricing page is ideal if they have one. The bot will detect any changes to these pages between runs.

```yaml
  review_subreddits:
    - "startups"
    - "entrepreneur"
    - "SaaS"
```
Subreddits where your target audience hangs out. The reviews agent searches these for mentions of your keywords.

### Schedule Section

```yaml
schedule:
  hour: 7        # 7 = 7:00 AM UTC
  minute: 0
  timezone: "UTC"
  run_on_start: true
```

Set `hour` and `minute` to when you want the daily report. The time is in UTC. To convert: UK = UTC, US East = UTC-5 (so 7 AM UTC = 2 AM Eastern). Set `run_on_start: true` to get a report immediately when the service starts.

### Agents Section

```yaml
agents:
  news:
    enabled: true
    max_articles: 15
  competitor:
    enabled: true
  reviews:
    enabled: true
    max_posts: 20
  trends:
    enabled: true
    hn_stories: 10
```

You can disable any agent by setting `enabled: false`. Useful if you want to save API costs or an agent is causing problems.

### Delivery Section

```yaml
delivery:
  telegram:
    enabled: false   # change to true if using Telegram
  slack:
    enabled: false   # change to true if using Slack
  email:
    enabled: false   # change to true if using email
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    to_addresses:
      - "you@example.com"
```

Enable whichever channels you set up. You can enable multiple. The actual credentials (tokens, passwords) go in `.env`, not here.

**Save and exit nano:** `Ctrl+O` then `Enter` to save, `Ctrl+X` to exit.

After any config change, restart the service:
```bash
systemctl restart research-bot
```

---

## 7. Setting Up API Keys

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
2. Your API key is shown on the dashboard
3. Add to `.env`:
   ```
   NEWS_API_KEY=your-newsapi-key
   ```

### SerpAPI Key (Optional)

1. Go to [serpapi.com](https://serpapi.com) and sign up
2. Find your API key on the dashboard
3. Add to `.env`:
   ```
   SERP_API_KEY=your-serpapi-key
   ```

---

## 8. Setting Up Delivery Channels

### Telegram

Telegram is the easiest and most reliable delivery method — reports arrive as messages to your phone instantly.

**Step 1 — Create a bot:**
1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow the prompts — choose a name and username for your bot
4. BotFather will give you a token like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
5. Add it to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

**Step 2 — Get your Chat ID:**
1. Start a conversation with your new bot in Telegram (search for it by username and press Start)
2. Open this URL in your browser (replace TOKEN with your actual token):
   ```
   https://api.telegram.org/botTOKEN/getUpdates
   ```
3. You'll see JSON output. Find the `"id"` number inside `"chat"` — that's your Chat ID
4. Add it to `.env`:
   ```
   TELEGRAM_CHAT_ID=123456789
   ```

**Step 3 — Enable in config.yml:**
```yaml
delivery:
  telegram:
    enabled: true
```

### Slack

**Step 1 — Create an Incoming Webhook:**
1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App → From Scratch**
2. Name it (e.g. "Research Bot") and pick your workspace
3. In the app settings, click **Incoming Webhooks → Activate Incoming Webhooks**
4. Click **Add New Webhook to Workspace** and choose a channel
5. Copy the webhook URL (starts with `https://hooks.slack.com/services/...`)
6. Add to `.env`:
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook/url
   ```

**Step 2 — Enable in config.yml:**
```yaml
delivery:
  slack:
    enabled: true
```

### Email (Gmail)

Gmail requires an App Password (not your regular password) when using SMTP.

**Step 1 — Create a Gmail App Password:**
1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** if not already enabled
3. Go to **Security → App Passwords**
4. Select **Mail** and your device, click **Generate**
5. Copy the 16-character password

**Step 2 — Add to `.env`:**
```
EMAIL_ADDRESS=youraddress@gmail.com
EMAIL_PASSWORD=abcd efgh ijkl mnop
```

**Step 3 — Enable in config.yml:**
```yaml
delivery:
  email:
    enabled: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    to_addresses:
      - "you@example.com"
      - "colleague@example.com"
```

---

## 9. Starting and Managing the Service

### Start the service
```bash
systemctl start research-bot
```

### Stop the service
```bash
systemctl stop research-bot
```

### Restart after config changes
```bash
systemctl restart research-bot
```

### Check if it's running
```bash
systemctl status research-bot
```

### Enable auto-start on server reboot (already done by installer)
```bash
systemctl enable research-bot
```

### Disable auto-start
```bash
systemctl disable research-bot
```

---

## 10. Understanding the Daily Report

The report is generated by Claude and structured into six sections:

**Executive Summary**
2–3 sentences covering the most important thing that happened in your market today.

**News & Industry**
The top 3–5 news stories relevant to your keywords, with a one-line takeaway for each.

**Competitor Watch**
Status of each configured competitor. If a competitor's page changed since yesterday, it will be flagged as **CHANGED** with details. Pricing found on the page is extracted and listed.

**Community Pulse**
What real people are saying on Reddit and review sites. Surfaces complaints, questions, comparisons, and praise.

**Trends**
Google Trends interest scores for your keywords, and relevant HackerNews stories with point counts.

**Today's Action Items**
1–3 concrete things worth acting on based only on today's data. These might include: following up on a competitor change, responding to a Reddit thread, or investigating a news story.

---

## 11. Monitoring and Logs

### Live log stream
```bash
tail -f /opt/research-bot-army/logs/service.log
```

### View recent log entries
```bash
tail -100 /opt/research-bot-army/logs/service.log
```

### Check systemd journal
```bash
journalctl -u research-bot -f
```

### What to look for in logs

A healthy run looks like this:
```
INFO: === Research cycle started: My Product (run_id=2026-03-26T07:00:00) ===
INFO: Agent news: success (15 items, 3.2s)
INFO: Agent competitor: success (3 items, 8.1s)
INFO: Agent reviews: success (12 items, 4.5s)
INFO: Agent trends: success (5 items, 6.3s)
INFO: Calling Claude to synthesize report...
INFO: Report generated: 2341 chars, 1823 tokens
INFO: Telegram: sent part 1/1
INFO: === Research cycle complete (1823 tokens) ===
```

If an agent shows `failed`, the run still completes — Claude just has less data to work with.

---

## 12. Running a Manual Research Cycle

To trigger a report right now without waiting for the schedule:

```bash
cd /opt/research-bot-army
venv/bin/python main.py --now
```

The report will print to the terminal and also be delivered to your configured channels.

---

## 13. Updating Your Configuration

Any time you want to change your product, keywords, competitors, or schedule:

1. Edit the config:
   ```bash
   nano /opt/research-bot-army/config.yml
   ```

2. Save and restart:
   ```bash
   systemctl restart research-bot
   ```

To add or change API keys or delivery credentials:

1. Edit the secrets file:
   ```bash
   nano /opt/research-bot-army/.env
   ```

2. Restart:
   ```bash
   systemctl restart research-bot
   ```

---

## 14. Troubleshooting

### Service won't start
```bash
systemctl status research-bot
tail -50 /opt/research-bot-army/logs/service.log
```
Look for `ERROR` lines. The most common cause is a missing or incorrect `ANTHROPIC_API_KEY` in `.env`.

### No report being delivered
1. Check that at least one delivery channel is `enabled: true` in `config.yml`
2. Check that the credentials in `.env` are correct
3. Run `venv/bin/python main.py --now` and look for delivery error messages

### "Bad credentials" from Telegram
- Double-check `TELEGRAM_BOT_TOKEN` in `.env`
- Make sure you started a conversation with your bot in Telegram before the first run
- Re-check your Chat ID using the `getUpdates` URL method in Section 8

### Competitor agent returning no prices
Most sites don't show prices in plain text — they use JavaScript or images. The agent extracts text-visible prices only. If a site uses JavaScript to render its pricing, the agent will still detect page changes but may not extract the exact price figures.

### Google Trends failing
pytrends is an unofficial library and Google rate-limits it aggressively. If it fails, the bot logs a warning and continues without it. HackerNews results are always included. Trends data is cached for 6 hours to reduce rate-limit risk.

### Out of memory errors
If your droplet has only 1 GB RAM and the service is being killed:
```bash
# Check if the OOM killer is involved
dmesg | grep -i "killed process"

# Add more swap
fallocate -l 2G /swapfile2
chmod 600 /swapfile2
mkswap /swapfile2
swapon /swapfile2
```

### NewsAPI returning old articles
The free NewsAPI tier only returns articles from the past 30 days. If you're looking for very recent news (last few hours), the Google News RSS fallback is actually more current.

---

## 15. Updating to a New Version

When a new release is published:

**1. On your local machine, pull the latest code:**
```bash
git pull origin main
```

**2. Redeploy to the server:**

On Mac/Linux:
```bash
bash deploy.sh root@YOUR_DROPLET_IP
```

On Windows (PowerShell):
```powershell
scp -r ".\." root@YOUR_DROPLET_IP:/opt/research-bot-army/
```

**3. On the server, update dependencies and restart:**
```bash
ssh root@YOUR_DROPLET_IP
cd /opt/research-bot-army
source venv/bin/activate
pip install -r requirements.txt -q
systemctl restart research-bot
```

Your `.env` and `config.yml` are preserved — they are not overwritten by updates.

---

## 16. Cost Estimates

| Item | Cost |
|---|---|
| Digital Ocean 1 GB droplet | ~$6–12/month |
| Anthropic API (Claude) | ~$0.01–0.05 per daily report |
| NewsAPI | Free (100 req/day) |
| SerpAPI | Free (100 searches/month) |
| Telegram delivery | Free |
| Slack delivery | Free |
| Gmail SMTP | Free |

**Typical monthly total: ~$7–15/month** for a fully running system with daily reports.

The main variable cost is Claude API usage. A typical run processes ~2,000–4,000 tokens, costing roughly $0.01–0.03 at current Anthropic pricing. Running once per day = under $1/month in AI costs.

---

*Research Bot Army is released under the MIT License — see [LICENSE](LICENSE) for details.*
