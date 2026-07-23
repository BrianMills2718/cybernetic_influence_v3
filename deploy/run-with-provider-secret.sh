#!/bin/bash
# Launch one command with an OpenRouter key from an approved host-native source.

set -euo pipefail

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
  if [[ -z "$secret_file" || ! -f "$secret_file" ]]; then
    echo "OpenRouter credential is unavailable from Keychain or secret file." >&2
    exit 78
  fi
  secret_owner="$(/usr/bin/stat -f '%Su' "$secret_file")"
  secret_mode="$(/usr/bin/stat -f '%Lp' "$secret_file")"
  if [[ "$secret_owner" != "$(id -un)" || "$secret_mode" != "600" ]]; then
    echo "OpenRouter secret file must be owned by the service user with mode 600." >&2
    exit 78
  fi
  openrouter_api_key="$(<"$secret_file")"
fi
if [[ -z "$openrouter_api_key" ]]; then
  echo "OpenRouter credential is empty." >&2
  exit 78
fi

export OPENROUTER_API_KEY="$openrouter_api_key"
unset openrouter_api_key
exec "$@"
