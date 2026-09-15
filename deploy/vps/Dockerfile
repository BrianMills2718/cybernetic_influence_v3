# Public Waltzman simulator backend for the personal netcup VPS (ADR-016).
#
# Build context (assembled by personal-vps `apps/waltzman/deploy.sh`):
#   app/         this repository at the deployed commit (git archive)
#   llm_client/  a git clone of BrianMills2718/llm_client checked out at the pinned
#                revision, .git included, so `installed_llm_client_revision()` reports
#                the exact commit SHA instead of a package version.
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends git sqlite3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app

# Exact tested simulator environment, including the pinned Concordia revision.
COPY app/requirements-dev.lock /opt/app/requirements-dev.lock
RUN pip install --no-cache-dir -r /opt/app/requirements-dev.lock

# Shared LLM client at its pinned revision. The package files are root-owned and the
# service runs as `app`, so git must be told the checkout is safe or it refuses to
# report HEAD and the revision silently degrades to `package:<version>`.
COPY llm_client /opt/llm_client
RUN pip install --no-cache-dir -e /opt/llm_client \
    && git config --system --add safe.directory /opt/llm_client

COPY app /opt/app
WORKDIR /opt/app
RUN pip install --no-cache-dir -e . --no-deps \
    && install -d -o app -g app /opt/app/artifacts /data

ARG BUILD_COMMIT=unknown
# Must equal the checked-out llm_client HEAD: the app validates the claim against the
# installed checkout, and route-certification observations record this value, so an unset
# variable makes every certification carry `package:<version>` and never match the app.
ARG LLM_CLIENT_REVISION
RUN test -n "${LLM_CLIENT_REVISION}" \
    && test "$(git -C /opt/llm_client rev-parse HEAD)" = "${LLM_CLIENT_REVISION}"
ENV CYBERNETIC_INFLUENCE_BUILD_COMMIT=${BUILD_COMMIT} \
    LLM_CLIENT_REVISION=${LLM_CLIENT_REVISION} \
    CYBERNETIC_INFLUENCE_LIVE=1 \
    CYBERNETIC_INFLUENCE_RUNS_DIR=/data/runs \
    CYBERNETIC_INFLUENCE_SPEND_STATE=/data/spend_controls.json \
    LLM_CLIENT_DATA_ROOT=/data/llm_client/logs \
    LLM_CLIENT_DB_PATH=/data/llm_client/llm_observability.db \
    LLM_ROUTE_CERTIFICATION_ROOT=/data/llm_route_certification \
    LLM_CLIENT_PROJECT=cybernetic_influence_v3 \
    LLM_CLIENT_TIMEOUT_POLICY=allow \
    PYTHONUNBUFFERED=1 \
    HOME=/home/app

USER app
EXPOSE 8621
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8621/api/config', timeout=8)"
CMD ["python", "-m", "uvicorn", "cybernetic_influence.public_waltzman:app", "--host", "0.0.0.0", "--port", "8621"]
