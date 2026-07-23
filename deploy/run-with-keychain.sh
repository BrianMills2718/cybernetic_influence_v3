#!/bin/bash
# Launch one command with the OpenRouter key loaded from macOS Keychain.

set -euo pipefail

keychain_service="${CYBERNETIC_INFLUENCE_OPENROUTER_KEYCHAIN_SERVICE:-cybernetic-influence-v3-openrouter}"
keychain_account="${CYBERNETIC_INFLUENCE_OPENROUTER_KEYCHAIN_ACCOUNT:-$(id -un)}"

openrouter_api_key="$(
  /usr/bin/security find-generic-password \
    -a "$keychain_account" \
    -s "$keychain_service" \
    -w
)"
if [[ -z "$openrouter_api_key" ]]; then
  echo "OpenRouter credential is empty in macOS Keychain." >&2
  exit 78
fi

export OPENROUTER_API_KEY="$openrouter_api_key"
unset openrouter_api_key
exec "$@"
