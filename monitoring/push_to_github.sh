#!/bin/bash
# Push updated events.json to GitHub Pages (docs/data/events.json)
# Called after each monitoring cron run to keep the live dashboard in sync.
#
# Usage: bash brace4peace/monitoring/push_to_github.sh
# Requires: gh CLI authenticated, git configured

set -e

WORKSPACE="/home/user/workspace"
REPO_DIR="$WORKSPACE/brace4peace-repo"
PLATFORM_DIR="$WORKSPACE/brace4peace-platform"
REPO_URL="https://github.com/KSvend/brace4peace.git"

# Ensure repo is cloned
if [ ! -d "$REPO_DIR/.git" ]; then
  echo "Cloning repo..."
  git clone "$REPO_URL" "$REPO_DIR"
fi

# Configure git
cd "$REPO_DIR"
git config user.email "krdasv@me.com"
git config user.name "KSvend"

# Pull latest to avoid conflicts
git pull origin main --rebase 2>/dev/null || true

# Copy updated data files
cp "$PLATFORM_DIR/data/events.json" "$REPO_DIR/docs/data/events.json"
cp "$PLATFORM_DIR/data/narratives.json" "$REPO_DIR/docs/data/narratives.json"

# Check if anything changed
if git diff --quiet docs/data/; then
  echo "No changes to push."
  exit 0
fi

# Commit and push
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
EVENT_COUNT=$(python3 -c "import json; d=json.load(open('docs/data/events.json')); print(len(d))")

git add docs/data/
git commit -m "Auto-update: ${EVENT_COUNT} events — ${TIMESTAMP}

Automated push from BRACE4PEACE monitoring pipeline."

git push origin main

echo "Pushed ${EVENT_COUNT} events to GitHub Pages."
