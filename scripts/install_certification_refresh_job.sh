#!/usr/bin/env bash
# Install the nightly authoring-certification refresh on the deployment host.
#
# The certification lasts 7 days and installing a new one was a manual step, so
# the public Create surface went dark repeatedly with no warning. This schedules
# the refresh so the margin is maintained without anyone remembering to do it.
#
# Idempotent: re-running replaces the job with the current definition.
set -euo pipefail

LABEL="com.cybernetic-influence.authoring-cert-refresh"
REPO="$HOME/code/cybernetic_influence_v3"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/cybernetic-influence"

if [[ ! -d "$REPO" ]]; then
  echo "repository not found at $REPO" >&2
  exit 1
fi
mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

# The job deliberately carries no secrets of its own: it reads the service
# environment out of the service's own plist at run time, so there is exactly
# one place credentials and certification ids live.
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$REPO/.venv/bin/python</string>
    <string>$REPO/scripts/refresh_authoring_certification.py</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>3</integer>
    <key>Minute</key><integer>30</integer>
  </dict>
  <key>StandardOutPath</key><string>$LOG_DIR/authoring-cert-refresh.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/authoring-cert-refresh.log</string>
  <key>RunAtLoad</key><false/>
</dict>
</plist>
PLIST

U="$(id -u)"
launchctl bootout "gui/$U/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$U" "$PLIST"
echo "installed $LABEL (nightly 03:30)"
launchctl print "gui/$U/$LABEL" | sed -n '1,6p'
echo "log: $LOG_DIR/authoring-cert-refresh.log"
