#!/usr/bin/env bash
# ============================================================
#  Deploy Research Bot Army to your Digital Ocean droplet
#  Run this from your LOCAL machine (not the server).
#
#  Prerequisites:
#    - SSH key added to the droplet
#    - rsync installed locally
#
#  Usage:  bash deploy.sh [user@host]
#  Default host: root@64.23.234.155
# ============================================================
set -euo pipefail

TARGET="${1:-root@64.23.234.155}"
REMOTE_DIR="/opt/research-bot-army"

echo "Deploying to $TARGET:$REMOTE_DIR ..."

# Copy project files (exclude git, venv, compiled files, local data/logs)
rsync -avz --progress \
  --exclude '.git' \
  --exclude 'venv/' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'data/' \
  --exclude 'logs/' \
  --exclude '.env' \
  ./ "$TARGET:$REMOTE_DIR/"

echo ""
echo "Files synced. Now running installer on the server..."
echo ""

# Run installer on the server
ssh -t "$TARGET" "cd $REMOTE_DIR && bash install.sh"
