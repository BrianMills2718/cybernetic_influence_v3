from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "wrangler.jsonc").read_text(encoding="utf-8"))
WORKER = (ROOT / "deploy/cloudflare/worker.js").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "Dockerfile.cloudflare").read_text(encoding="utf-8")
PREPARE = (ROOT / "deploy/cloudflare/prepare-build.sh").read_text(encoding="utf-8")


def test_cloudflare_route_uses_static_edge_and_one_container_backend() -> None:
    assert CONFIG["name"] == "world-substrate-visualization"
    assert CONFIG["assets"]["directory"] == "./public/waltzman"
    assert CONFIG["assets"]["run_worker_first"] is True
    assert CONFIG["routes"] == [
        {
            "pattern": "brianmills.dev/world-substrate-visualization*",
            "zone_name": "brianmills.dev",
        }
    ]
    assert CONFIG["containers"] == [
        {
            "class_name": "WaltzmanContainer",
            "image": "./Dockerfile.cloudflare",
            "max_instances": 1,
        }
    ]
    assert CONFIG["durable_objects"]["bindings"][0]["name"] == "WALTZMAN_CONTAINER"
    assert CONFIG["migrations"][0]["new_sqlite_classes"] == ["WaltzmanContainer"]


def test_worker_keeps_static_hook_off_container_and_strips_only_public_api_prefix() -> None:
    assert 'const PUBLIC_PREFIX = "/world-substrate-visualization"' in WORKER
    assert 'relative.startsWith("/api/")' in WORKER
    assert "const assetResponse = await env.ASSETS.fetch(staticAssetRequest(request))" in WORKER
    assert "return secureStaticResponse(assetResponse, relative)" in WORKER
    assert 'relative.startsWith("/assets/")' in WORKER
    assert 'getContainer(env.WALTZMAN_CONTAINER, BACKEND_INSTANCE)' in WORKER
    assert "startAndWaitForPorts" in WORKER
    assert 'sleepAfter = "2h"' in WORKER
    assert "stripPublicPrefix(request)" in WORKER


def test_container_build_preserves_existing_runtime_and_private_provider_boundary() -> None:
    assert "FROM python:3.12-slim" in DOCKERFILE
    for source in ("src", "public", "web", ".llm_client", ".route_certification"):
        assert f"COPY {source} " in DOCKERFILE
    assert "cybernetic_influence.public_waltzman:app" in DOCKERFILE
    assert "LLM_CLIENT_DEPLOY_KEY" not in DOCKERFILE
    assert "OPENROUTER_API_KEY" not in DOCKERFILE
    assert "590a8ca5ca8f3553bc3b156bcb29c31cefb218bf" in PREPARE
    assert "LLM_CLIENT_DEPLOY_KEY" in PREPARE
    assert "git -C .llm_client rev-parse HEAD" in PREPARE


def test_runtime_secrets_are_named_but_never_committed_as_values() -> None:
    required = {
        "OPENROUTER_API_KEY",
        "CYBERNETIC_INFLUENCE_CERT_SOL",
        "CYBERNETIC_INFLUENCE_CERT_AUTHORING_SOL",
        }
    for name in required:
        assert name in WORKER
    # Wrangler manages ordinary Worker secrets outside wrangler.jsonc. Keeping
    # a fake `secrets` config block would look enforced while being ignored.
    assert "secrets" not in CONFIG
    assert "sk-or-" not in WORKER
    assert "sk-proj-" not in WORKER


def test_worker_static_security_headers_match_public_inline_scripts() -> None:
    markup = (ROOT / "public/waltzman/index.html").read_text(encoding="utf-8")
    inline_bodies = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", markup, re.I | re.S)
    expected_hashes = [
        base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
        for body in inline_bodies
        if body.strip()
    ]
    assert len(expected_hashes) == 2
    for digest in expected_hashes:
        assert f"'sha256-{digest}'" in WORKER
    for header in (
        "Content-Security-Policy",
        "X-Content-Type-Options",
        "Referrer-Policy",
        "Permissions-Policy",
    ):
        assert header in WORKER
    assert 'headers.set("Cache-Control", "no-cache")' in WORKER
