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

Live execution uses the shared `llm_client` checkout at
`/Users/b/code/llm_client`. The LaunchAgent starts through
`deploy/run-with-keychain.sh`, which reads the OpenRouter credential from the
login Keychain service `cybernetic-influence-v3-openrouter`. The credential is
not stored in the repository or LaunchAgent plist.

The advertised service-desk live path uses `gpt-5.6-terra` through OpenRouter
at medium reasoning. Runtime contracts cap each call at $0.05 and the complete
nine-activation run at $0.50; the UI presents the tighter nine-call estimate of
$0.45. Only one live run may execute at a time.

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
export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m mypy
.venv/bin/python -m pytest -q
```

Install the accepted `llm_client` revision into the simulator environment:

```bash
.venv/bin/python -m pip install -e /Users/b/code/llm_client
```

Provision or replace the provider credential through the Keychain prompt:

```bash
security add-generic-password -U \
  -a "$(id -un)" \
  -s cybernetic-influence-v3-openrouter \
  -w
```

Render the LaunchAgent template with the new commit in `__BUILD_COMMIT__`, the
approved Tailscale login in `__ALLOWED_TAILSCALE_USERS__`, and
`/Users/b/Library/Application Support/LLMClient` in
`__LLM_CLIENT_DATA_ROOT__`. Validate it with `plutil -lint`, then use:

```bash
launchctl bootout "gui/$(id -u)/com.cybernetic-influence.v3"
sleep 1
launchctl bootstrap "gui/$(id -u)" \
  ~/Library/LaunchAgents/com.cybernetic-influence.v3.plist
```

Reopen an existing retained run after restart before considering the update
complete. Before advertising live execution, make one bounded provider-backed
run, verify its retained model-call evidence and cost, and confirm that the
missing-credential and unauthorized-live controls fail closed. Delete
transferred bundles after the update; they are only transport.
