# Mac Mini Development Host

The approved development instance runs as the `b` user's LaunchAgent on
`brian-mac-mini`:

- private URL: <https://brian-mac-mini.tail9c321e.ts.net:8620/>
- checkout: `/Users/b/code/cybernetic_influence_v3`
- retained runs:
  `/Users/b/Library/Application Support/CyberneticInfluenceV3/runs`
- service: `com.cybernetic-influence.v3`
- logs: `/Users/b/Library/Logs/cybernetic-influence-v3*.log`

The service binds only to `127.0.0.1:8620`. Tailscale Serve adds the
tailnet-only HTTPS listener. Do not use Funnel for this port, and do not reset
the machine's Serve configuration because its other listeners are unrelated.

Live execution is intentionally disabled. The host does not yet have the
shared `llm_client` or an approved provider-secret injection path.

## Inspect

```bash
ssh 100.109.41.60 \
  'launchctl print "gui/$(id -u)/com.cybernetic-influence.v3"'

curl https://brian-mac-mini.tail9c321e.ts.net:8620/api/config
```

The config response reports `build_commit`; compare it with the approved local
commit before interpreting a remote run.

## Update Without Host GitHub Credentials

From an approved, clean local `main`:

```bash
git bundle create /tmp/cybernetic-influence-v3.bundle main
scp /tmp/cybernetic-influence-v3.bundle 100.109.41.60:/tmp/
ssh 100.109.41.60
```

On the Mac:

```bash
cd ~/code/cybernetic_influence_v3
git fetch /tmp/cybernetic-influence-v3.bundle main
git merge --ff-only FETCH_HEAD
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m mypy
.venv/bin/python -m pytest -q
```

Render the LaunchAgent template with the new commit in
`__BUILD_COMMIT__`, validate it with `plutil -lint`, then use:

```bash
launchctl bootout "gui/$(id -u)/com.cybernetic-influence.v3"
sleep 1
launchctl bootstrap "gui/$(id -u)" \
  ~/Library/LaunchAgents/com.cybernetic-influence.v3.plist
```

Reopen an existing retained run after restart before considering the update
complete. Delete the transferred bundle after the update; it is only transport.
