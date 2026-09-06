#!/usr/bin/env bash
# Install the nightly public-demo audit on the deployment host.
#
# Every check it runs exists because a real defect got past everything else.
# Scheduling them means keeping the demo correct does not depend on anyone
# remembering to look, which is what it depended on until now.
#
# No model calls: this costs nothing to run nightly.
# Idempotent: re-running replaces the job with the current definition.
set -euo pipefail

LABEL="com.cybernetic-influence.demo-audit"
REPO="$HOME/code/cybernetic_influence_v3"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/cybernetic-influence"

if [[ ! -d "$REPO" ]]; then
  echo "repository not found at $REPO" >&2
  exit 1
fi
mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

# The Deck has been served from project-launcher/www/ since the 2026-09-01
# split. Writing the verdict into the parent index.html leaves the audit green
# and the published card stale, which is how a "do not share" verdict stood
# unread for four days.
STATUS_TARGET="$HOME/Sites/project-launcher/www/index.html"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$REPO/.venv/bin/python</string>
    <string>$REPO/scripts/audit_public_demo.py</string>
    <string>--status-target</string>
    <string>$STATUS_TARGET</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>4</integer>
    <key>Minute</key><integer>15</integer>
  </dict>
  <key>StandardOutPath</key><string>$LOG_DIR/demo-audit.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/demo-audit.log</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
PLIST

U="$(id -u)"
launchctl bootout "gui/$U/$LABEL" 2>/dev/null || true
sleep 2
launchctl bootstrap "gui/$U" "$PLIST"
echo "installed $LABEL (nightly 04:15)"
echo "log: $LOG_DIR/demo-audit.log"
