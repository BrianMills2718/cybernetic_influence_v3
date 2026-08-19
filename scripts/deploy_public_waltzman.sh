#!/usr/bin/env bash
# Deploy the public Waltzman workbench to the Mac Mini and reload it.
#
# Exists because two verification runs were destroyed by redeploying on top of
# them: restarting the LaunchAgent kills any authoring or simulation job in
# flight, and the browser sees a 502 that looks exactly like a product defect.
# This refuses to deploy while the host is busy unless --force says otherwise.

set -euo pipefail

HOST="${WALTZMAN_DEPLOY_HOST:-100.109.41.60}"
LABEL="com.cybernetic-influence.waltzman-public"
PUBLIC_URL="${WALTZMAN_PUBLIC_URL:-https://brian-mac-mini.tail9c321e.ts.net/waltzman}"
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -n "$(git status --porcelain)" ]]; then
  echo "refusing to deploy: working tree is dirty" >&2
  git status --short >&2
  exit 1
fi
commit="$(git rev-parse --short HEAD)"
echo "deploying $commit from $repo_root"

# --- the gate: is anything running that a restart would destroy? -------------
echo "checking for work in flight on the host..."
# A simulation run persists its status, so those are detected exactly. An
# authoring job does NOT: while it is generating, its draft on disk still reads
# status "draft" with no attempts, because the job lives in the service
# process. Recent draft mtime is the only disk-visible signal, so that half is
# a deliberate over-approximation -- it would rather block a safe deploy than
# silently destroy a 15-minute authoring job again.
running="$(ssh -o BatchMode=yes "$HOST" '
  store="$HOME/Library/Application Support/cybernetic-influence-waltzman"
  python3 - "$store" <<PY
import json, os, sys, time
store = sys.argv[1]
busy = []
now = time.time()

runs = os.path.join(store, "runs")
if os.path.isdir(runs):
    for name in os.listdir(runs):
        if not name.endswith(".json"):
            continue
        path = os.path.join(runs, name)
        if now - os.path.getmtime(path) > 3600:
            continue
        try:
            doc = json.load(open(path))
        except Exception:
            continue
        status = doc.get("status")
        if status in ("running", "narrating", "pause_requested"):
            busy.append("run " + name + " is " + str(status))

drafts = os.path.join(store, "authoring_drafts")
if os.path.isdir(drafts):
    for name in os.listdir(drafts):
        if not name.endswith(".json"):
            continue
        path = os.path.join(drafts, name)
        age = now - os.path.getmtime(path)
        if age > 1200:
            continue
        try:
            doc = json.load(open(path))
        except Exception:
            continue
        # A draft that has resolved -- either way -- is not in flight: it moves
        # off "draft" status and records its attempts. A recently touched draft
        # still sitting at "draft" with nothing recorded is the one that is
        # probably mid-generation in the service process.
        resolved = doc.get("status") != "draft" or (doc.get("attempts") or [])
        if not doc.get("proposal") and not resolved:
            busy.append(
                "draft " + name + " touched " + str(int(age)) + "s ago, still"
                " status=draft with no attempts (probable authoring job in flight)"
            )
print("\n".join(busy))
PY' || true)"

if [[ -n "$running" ]]; then
  echo "WORK IN FLIGHT on the deployment:" >&2
  echo "$running" | sed 's/^/  /' >&2
  if [[ "$FORCE" -ne 1 ]]; then
    echo >&2
    echo "refusing to deploy; a reload would kill these and surface as a 502." >&2
    echo "wait for them, or re-run with --force if you accept losing them." >&2
    exit 2
  fi
  echo "--force given; proceeding and losing the above." >&2
fi

# --- transfer (the host has no GitHub credentials) ---------------------------
bundle="$(mktemp -t ci3-XXXX).bundle"
trap 'rm -f "$bundle"' EXIT
git bundle create "$bundle" main >/dev/null
scp -q "$bundle" "$HOST:/tmp/ci3-deploy.bundle"

ssh -o BatchMode=yes "$HOST" "
  set -euo pipefail
  cd ~/code/cybernetic_influence_v3
  git fetch /tmp/ci3-deploy.bundle main >/dev/null 2>&1
  git merge --ff-only FETCH_HEAD
  echo \"host now at: \$(git log -1 --format='%h %s')\"
  U=\$(id -u)
  python3 - ~/Library/LaunchAgents/$LABEL.plist <<PY
import plistlib, sys
p = sys.argv[1]
d = plistlib.load(open(p, 'rb'))
d['EnvironmentVariables']['CYBERNETIC_INFLUENCE_BUILD_COMMIT'] = '$commit'
plistlib.dump(d, open(p, 'wb'))
PY
  # a changed plist needs bootout+bootstrap; kickstart -k keeps the loaded one
  launchctl bootout \"gui/\$U/$LABEL\" 2>/dev/null || true
  sleep 3
  launchctl bootstrap \"gui/\$U\" ~/Library/LaunchAgents/$LABEL.plist
  rm -f /tmp/ci3-deploy.bundle
"

echo "waiting for the service to answer..."
for _ in $(seq 1 30); do
  reported="$(curl -fsS --max-time 10 "$PUBLIC_URL/api/config" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["build_commit"])' 2>/dev/null || true)"
  [[ -n "$reported" ]] && break
  sleep 2
done

if [[ "$reported" != "$commit" ]]; then
  echo "deployed commit mismatch: service reports '${reported:-<no answer>}', expected '$commit'" >&2
  exit 3
fi
echo "deployed and serving $reported"
