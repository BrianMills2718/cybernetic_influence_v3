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
# The trailing slash is not cosmetic. The page references its assets relatively,
# so a browser resolving them from ".../waltzman" drops the last segment and asks
# for /assets/*, which belongs to another service and 404s -- the visitor gets an
# unstyled page with no working navigation. Share PAGE_URL, never PUBLIC_URL.
PAGE_URL="$PUBLIC_URL/"
FORCE=0
[[ "${1:-}" == "--force" ]] && FORCE=1

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# Only committed work ships -- the transfer is a bundle of main -- so the risk
# this guards against is deploying while believing uncommitted changes are
# included. That is about tracked modifications. Untracked files cannot ship,
# and other sessions leave them in this shared checkout, so they are reported
# rather than treated as a blocker.
untracked="$(git ls-files --others --exclude-standard)"
if [[ -n "$untracked" ]]; then
  echo "note: untracked files present (they will NOT be deployed):" >&2
  echo "$untracked" | sed 's/^/  /' >&2
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "refusing to deploy: tracked files have uncommitted changes" >&2
  git status --short >&2
  exit 1
fi
commit="$(git rev-parse --short HEAD)"
echo "deploying $commit from $repo_root"

# A page can render perfectly and still tell the reader something the run does
# not support. That failure is invisible to every other check here, and it is
# the one that would cost most with an expert reader.
echo "checking the page's claims against the retained evidence..."
if ! python3 "$(dirname "$0")/check_page_claims_match_evidence.py"; then
  echo "refusing to deploy: the page claims something the runs do not support" >&2
  exit 6
fi

# Only committed work ships, so a bundle that was never rebuilt-and-copied ships
# silently: `make ui-build` writes to web/, this app serves public/waltzman/, and
# nothing bridged them. That is how the demo served a 2026-08-16 graph bundle for
# ten days while every build reported success. Checked here because this is the
# step that puts it in front of a reader.
echo "checking the served bundle is what frontend/src builds..."
if ! python3 "$(dirname "$0")/check_served_bundle_matches_source.py"; then
  echo "refusing to deploy: the demo would serve a bundle the source no longer produces" >&2
  exit 7
fi

# --- the gate: is anything running that a restart would destroy? -------------
# The detection logic lives in scripts/host_busy_check.py so the deploy path and
# the certification-refresh path cannot drift apart; the copy that drifts is the
# one that eats a live run. Piped over stdin rather than invoked from the host's
# checkout, so the gate is always this commit's version, not the deployed one.
echo "checking for work in flight on the host..."
running="$(ssh -o BatchMode=yes "$HOST" \
  'python3 - "$HOME/Library/Application Support/cybernetic-influence-waltzman"' \
  < "$(dirname "$0")/host_busy_check.py" || true)"

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

# --- is there anything to do at all? -----------------------------------------
# Reloading is the destructive part: it kills whatever the service is executing.
# Doing it when the host already serves this commit buys nothing and cost one
# live run, so a no-op deploy must stay a no-op.
# Compare full SHAs: the host's `git rev-parse --short` yields a different
# abbreviation length than this machine's, so short-form equality silently
# never matched and the no-op path never fired.
full_commit="$(git rev-parse HEAD)"
already="$(curl -fsS --max-time 10 "$PUBLIC_URL/api/config" 2>/dev/null \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["build_commit"])' 2>/dev/null || true)"
host_head="$(ssh -o BatchMode=yes "$HOST" 'cd ~/code/cybernetic_influence_v3 && git rev-parse HEAD' 2>/dev/null || true)"
if [[ -n "$already" && "$full_commit" == "$already"* && "$host_head" == "$full_commit" ]]; then
  echo "host already serves $commit; nothing to deploy and no reason to reload"
  exit 0
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
  # last look before the destructive step: work can start between the gate
  # check and here, and the reload kills whatever is executing
  if python3 -c \"
import json, os, sys, time
store = os.path.expanduser('~/Library/Application Support/cybernetic-influence-waltzman')
runs = os.path.join(store, 'runs')
now = time.time()
for name in (os.listdir(runs) if os.path.isdir(runs) else []):
    if not name.endswith('.json'):
        continue
    path = os.path.join(runs, name)
    if now - os.path.getmtime(path) > 3600:
        continue
    try:
        doc = json.load(open(path))
    except Exception:
        continue
    if doc.get('status') in ('running', 'narrating', 'pause_requested'):
        print(name); sys.exit(3)
\"; then :; else
    echo 'a run started between the gate check and the reload; aborting' >&2
    exit 4
  fi
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

# A 200 from the page and a working API both pass while the page is visibly
# broken, because neither resolves the page's own asset references. This does,
# against the exact URL a reader will be given.
echo "checking the shareable URL loads its assets..."
if ! python3 "$(dirname "$0")/check_public_assets.py" "$PAGE_URL"; then
  echo "the shareable URL is serving a broken page" >&2
  exit 5
fi
echo
echo "share this URL, with the trailing slash: $PAGE_URL"
