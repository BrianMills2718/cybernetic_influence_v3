#!/usr/bin/env bash
set -euo pipefail

readonly DEFAULT_LLM_CLIENT_REVISION="590a8ca5ca8f3553bc3b156bcb29c31cefb218bf"
revision="${LLM_CLIENT_REVISION:-$DEFAULT_LLM_CLIENT_REVISION}"

prepare_provider() {
  if [[ -d .llm_client/.git ]]; then
    git -C .llm_client fetch --quiet --depth 1 origin "$revision" || true
    if git -C .llm_client cat-file -e "$revision^{commit}" 2>/dev/null; then
      git -C .llm_client checkout --quiet --detach "$revision"
    fi
  else
    [[ -n "${LLM_CLIENT_DEPLOY_KEY:-}" ]] || {
      echo "LLM_CLIENT_DEPLOY_KEY is required when .llm_client is absent" >&2
      exit 2
    }
    rm -rf .llm_client
    mkdir .llm_client
    git -C .llm_client init --quiet
    git -C .llm_client remote add origin git@github.com:BrianMills2718/llm_client.git
    key_file="$(mktemp)"
    trap 'rm -f "$key_file"' EXIT
    printf '%s\n' "$LLM_CLIENT_DEPLOY_KEY" > "$key_file"
    chmod 600 "$key_file"
    GIT_SSH_COMMAND="ssh -i $key_file -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
      git -C .llm_client fetch --quiet --depth 1 origin "$revision"
    git -C .llm_client checkout --quiet --detach FETCH_HEAD
  fi
  actual="$(git -C .llm_client rev-parse HEAD)"
  [[ "$actual" == "$revision" ]] || {
    echo "llm_client revision mismatch: expected $revision, got $actual" >&2
    exit 3
  }
}

prepare_certification() {
  if [[ -n "${LLM_ROUTE_CERTIFICATION_ARCHIVE_B64:-}" ]]; then
    rm -rf .route_certification
    mkdir -p .route_certification/observations
    printf '%s' "$LLM_ROUTE_CERTIFICATION_ARCHIVE_B64" \
      | base64 --decode \
      | tar -xz -C .route_certification
  else
    mkdir -p .route_certification/observations
  fi
}

prepare_provider
prepare_certification
printf 'Prepared llm_client %s and certification build context.\n' "$revision"
