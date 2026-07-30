#!/bin/bash
# Launch the simulator with ChatGPT Codex auth and optional OpenRouter access.

set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH}"

if ! command -v codex >/dev/null 2>&1; then
  echo "Codex CLI is unavailable; install it before starting the simulator." >&2
  exit 78
fi
codex_login_status="$(codex login status 2>&1 || true)"
if [[ "$codex_login_status" != *"Logged in using ChatGPT"* ]]; then
  echo "Codex CLI is not logged in with ChatGPT." >&2
  exit 78
fi
unset codex_login_status

keychain_service="${CYBERNETIC_INFLUENCE_OPENROUTER_KEYCHAIN_SERVICE:-cybernetic-influence-v3-openrouter}"
keychain_account="${CYBERNETIC_INFLUENCE_OPENROUTER_KEYCHAIN_ACCOUNT:-$(id -un)}"

openrouter_api_key="$(
  /usr/bin/security find-generic-password \
    -a "$keychain_account" \
    -s "$keychain_service" \
    -w 2>/dev/null || true
)"
if [[ -z "$openrouter_api_key" ]]; then
  secret_file="${CYBERNETIC_INFLUENCE_OPENROUTER_KEY_FILE:-}"
  if [[ -n "$secret_file" && -f "$secret_file" ]]; then
    secret_owner="$(/usr/bin/stat -f '%Su' "$secret_file")"
    secret_mode="$(/usr/bin/stat -f '%Lp' "$secret_file")"
    if [[ "$secret_owner" != "$(id -un)" || "$secret_mode" != "600" ]]; then
      echo "OpenRouter secret file must be owned by the service user with mode 600." >&2
      exit 78
    fi
    openrouter_api_key="$(<"$secret_file")"
  fi
fi
if [[ -n "$openrouter_api_key" ]]; then
  export OPENROUTER_API_KEY="$openrouter_api_key"
fi

unset openrouter_api_key
exec "$@"
