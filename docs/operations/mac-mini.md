# Mac Mini Development Host

This is a private development host, not a public deployment surface.

- private URL: <https://brian-mac-mini.tail9c321e.ts.net:8620/>
- checkout: `/Users/b/code/cybernetic_influence_v3`
- retained runs: `/Users/b/Library/Application Support/CyberneticInfluenceV3/runs`
- service: `com.cybernetic-influence.v3`
- logs: `/Users/b/Library/Logs/cybernetic-influence-v3*.log`

The service binds to `127.0.0.1:8620`; Tailscale Serve provides the private
HTTPS listener. Do not use Funnel or reset unrelated Tailscale Serve settings.

Current product direction is the [roadmap](../ROADMAP.md) and
[Slice 24](../plans/024-configurable-theory-analysis-mvp.md). Before treating
this host as ready for live work, inspect its `/api/config`, the installed
shared-client revision, and current route capability evidence. Historical route
certifications, model capacity incidents, run identifiers, and canary results
are retained separately in the [July 2026 runtime history](../archive/operations/mac-mini-2026-07.md);
they do not authorize a new run or establish present model availability.

## Inspect

```bash
ssh 100.109.41.60 \
  'launchctl print "gui/$(id -u)/com.cybernetic-influence.v3"'

curl https://brian-mac-mini.tail9c321e.ts.net:8620/api/config
```

Compare `build_commit` with the approved local commit before interpreting a
remote run.

## Update without host GitHub credentials

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
export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m mypy
.venv/bin/python -m pytest -q
.venv/bin/python -m pip install -e /Users/b/code/llm_client
```

Use the committed LaunchAgent template and its explicit current certification
placeholders. Do not copy credentials, historical observation IDs, or route
defaults from archived runtime records into a new deployment.
