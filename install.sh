#!/usr/bin/env bash
# ============================================================
#  Research Bot Army — Server Installer
#  Run this on the Digital Ocean droplet as root:
#    bash install.sh
# ============================================================
set -euo pipefail

INSTALL_DIR="/opt/research-bot-army"
SERVICE_NAME="research-bot"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }
ask()     { echo -e "${YELLOW}[?]${NC} $*"; }

echo ""
echo "  ██████╗ ███████╗███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗"
echo "  ██╔══██╗██╔════╝██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║"
echo "  ██████╔╝█████╗  ███████╗█████╗  ███████║██████╔╝██║     ███████║"
echo "  ██╔══██╗██╔══╝  ╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║"
echo "  ██║  ██║███████╗███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║"
echo "  ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝"
echo "  Research Bot Army — Installer"
echo ""

# ---- Root check ----
[[ $EUID -ne 0 ]] && error "Please run as root: sudo bash install.sh"

# ---- Step 1: System packages ----
info "Installing system packages..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv curl rsync

PYTHON=$(command -v python3)
PY_VER=$($PYTHON --version | cut -d' ' -f2)
info "Python $PY_VER found at $PYTHON"

# Add swap if RAM is <= 1 GB (common on cheap droplets)
TOTAL_RAM=$(awk '/MemTotal/ {print $2}' /proc/meminfo)
if [[ $TOTAL_RAM -lt 1200000 ]] && ! swapon --show | grep -q /swapfile; then
  info "Low RAM detected ($((TOTAL_RAM / 1024)) MB). Adding 1 GB swap..."
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile -q
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
  info "Swap enabled."
fi

# ---- Step 2: Copy files ----
info "Copying project files to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
rsync -a --exclude '.git' --exclude 'venv' --exclude '__pycache__' \
  --exclude '*.pyc' --exclude 'data/' \
  "$SCRIPT_DIR/" "$INSTALL_DIR/"

cd "$INSTALL_DIR"
mkdir -p data logs

# ---- Step 3: Python virtual environment ----
info "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
info "Installing Python dependencies (this may take a minute)..."
pip install -r requirements.txt -q
info "Dependencies installed."

# ---- Step 4: Configure .env ----
if [[ -f .env ]]; then
  warn ".env already exists — skipping API key setup. Edit $INSTALL_DIR/.env manually if needed."
else
  info "Setting up API keys and delivery channels..."
  cp .env.example .env

  echo ""
  echo "─────────────────────────────────────────────"
  echo "  API Keys"
  echo "─────────────────────────────────────────────"

  ask "Anthropic API key (required — get one at console.anthropic.com):"
  read -r ANTHROPIC_KEY
  [[ -z "$ANTHROPIC_KEY" ]] && error "Anthropic API key is required."
  sed -i "s|your_anthropic_api_key_here|$ANTHROPIC_KEY|" .env

  ask "NewsAPI key (optional, press Enter to skip):"
  read -r NEWS_KEY
  [[ -n "$NEWS_KEY" ]] && sed -i "s|^NEWS_API_KEY=.*|NEWS_API_KEY=$NEWS_KEY|" .env

  ask "SerpAPI key (optional, press Enter to skip):"
  read -r SERP_KEY
  [[ -n "$SERP_KEY" ]] && sed -i "s|^SERP_API_KEY=.*|SERP_API_KEY=$SERP_KEY|" .env

  echo ""
  echo "─────────────────────────────────────────────"
  echo "  Delivery Channels (configure at least one)"
  echo "─────────────────────────────────────────────"

  ask "Telegram bot token (or Enter to skip):"
  read -r TG_TOKEN
  if [[ -n "$TG_TOKEN" ]]; then
    ask "Telegram chat ID:"
    read -r TG_CHAT
    sed -i "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=$TG_TOKEN|" .env
    sed -i "s|^TELEGRAM_CHAT_ID=.*|TELEGRAM_CHAT_ID=$TG_CHAT|" .env
    python3 - <<'EOF'
import yaml
with open("config.yml") as f: c = yaml.safe_load(f)
c["delivery"]["telegram"]["enabled"] = True
with open("config.yml", "w") as f: yaml.dump(c, f, default_flow_style=False, allow_unicode=True)
EOF
    info "Telegram delivery enabled."
  fi

  ask "Slack webhook URL (or Enter to skip):"
  read -r SLACK_URL
  if [[ -n "$SLACK_URL" ]]; then
    sed -i "s|^SLACK_WEBHOOK_URL=.*|SLACK_WEBHOOK_URL=$SLACK_URL|" .env
    python3 - <<'EOF'
import yaml
with open("config.yml") as f: c = yaml.safe_load(f)
c["delivery"]["slack"]["enabled"] = True
with open("config.yml", "w") as f: yaml.dump(c, f, default_flow_style=False, allow_unicode=True)
EOF
    info "Slack delivery enabled."
  fi

  ask "Email address for sending reports (or Enter to skip):"
  read -r EMAIL_ADDR
  if [[ -n "$EMAIL_ADDR" ]]; then
    ask "Email app password (for Gmail, use an App Password):"
    read -rs EMAIL_PASS
    echo ""
    ask "Send reports to (comma-separated, e.g. you@example.com,team@example.com):"
    read -r EMAIL_TO_RAW
    sed -i "s|^EMAIL_ADDRESS=.*|EMAIL_ADDRESS=$EMAIL_ADDR|" .env
    sed -i "s|^EMAIL_PASSWORD=.*|EMAIL_PASSWORD=$EMAIL_PASS|" .env
    # Build YAML list from comma-separated input
    python3 - "$EMAIL_ADDR" "$EMAIL_TO_RAW" <<'EOF'
import sys, yaml
addr = sys.argv[1]
to_list = [e.strip() for e in sys.argv[2].split(",") if e.strip()]
with open("config.yml") as f: c = yaml.safe_load(f)
c["delivery"]["email"]["enabled"] = True
c["delivery"]["email"]["from_address"] = addr
c["delivery"]["email"]["to_addresses"] = to_list
with open("config.yml", "w") as f: yaml.dump(c, f, default_flow_style=False, allow_unicode=True)
EOF
    info "Email delivery enabled."
  fi
fi

# Secure the .env file
chmod 600 .env

# ---- Step 5: Remind about config.yml ----
echo ""
echo "─────────────────────────────────────────────"
echo "  IMPORTANT: Edit your product configuration"
echo "─────────────────────────────────────────────"
warn "You must edit $INSTALL_DIR/config.yml before the bot runs correctly."
echo ""
echo "  nano $INSTALL_DIR/config.yml"
echo ""
echo "  Set your product name, keywords, and competitor URLs."
echo ""

# ---- Step 5b: Open dashboard port ----
if command -v ufw &>/dev/null; then
  ufw allow 8080/tcp &>/dev/null || true
  info "Firewall: port 8080 (dashboard) opened."
fi

# ---- Step 6: systemd service ----
info "Installing systemd service..."
cp "$INSTALL_DIR/research-bot.service" /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# ---- Step 7: Start ----
ask "Start the service now? (y/N):"
read -r START_NOW
if [[ "${START_NOW,,}" == "y" ]]; then
  systemctl start "$SERVICE_NAME"
  sleep 2
  echo ""
  info "Service status:"
  systemctl status "$SERVICE_NAME" --no-pager -l || true
fi

echo ""
echo "════════════════════════════════════════════════"
echo "  Installation complete!"
echo "════════════════════════════════════════════════"
echo ""
echo "  Web dashboard: http://$(curl -s ifconfig.me 2>/dev/null || echo YOUR_SERVER_IP):8080"
echo "  Edit config:   nano $INSTALL_DIR/config.yml  (or use the dashboard)"
echo "  View logs:     journalctl -u $SERVICE_NAME -f"
echo "             or: tail -f $INSTALL_DIR/logs/service.log"
echo "  Run now:       cd $INSTALL_DIR && venv/bin/python main.py --now"
echo "  Start:         systemctl start $SERVICE_NAME"
echo "  Stop:          systemctl stop $SERVICE_NAME"
echo "  Restart:       systemctl restart $SERVICE_NAME"
echo ""
