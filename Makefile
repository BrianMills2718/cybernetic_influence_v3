VENV ?= .venv
PYTHON := $(VENV)/bin/python
LLM_CLIENT_ROOT ?= ../active/llm_client
HOST ?= 127.0.0.1
PORT ?= 8620

.PHONY: install ui-install ui-build ui-sync assets-check ui-smoke ui-visibility claims-check authoring-route-health authoring-route-refresh test typecheck deploy-check check serve

install: ui-install
	python3 -m venv $(VENV) || virtualenv --clear $(VENV)
	$(PYTHON) -m pip install -r requirements-dev.lock
	$(PYTHON) -m pip install -e . --no-deps
	@if test -d '$(LLM_CLIENT_ROOT)/llm_client'; then \
		$(PYTHON) -m pip install -e '$(LLM_CLIENT_ROOT)[structured]'; \
	else \
		echo "Set LLM_CLIENT_ROOT to enable live runs."; \
	fi

ui-install:
	npm --prefix frontend ci

ui-build:
	npm --prefix frontend run build

# vite writes into web/, which cybernetic_influence.api:app serves locally. The
# public demo is a different app on a different root (public_waltzman.py), and
# nothing copied between them -- so ui-build passed for ten days while the demo
# served a bundle from 2026-08-16. Building and shipping are two acts; this is
# the second one.
ui-sync: ui-build
	cp web/graph-canvas.js web/graph-canvas.css public/waltzman/
	@echo "copied the built bundle into public/waltzman/"

# Checks the result, not the mechanism: builds the current source into a scratch
# directory and byte-compares it against what the demo actually serves.
assets-check:
	$(PYTHON) scripts/check_served_bundle_matches_source.py

ui-smoke:
	$(PYTHON) scripts/verify_demo_ui.py --base-url http://$(HOST):$(PORT)

# Fails when a primary control is not where a human can see or reach it.
# Exists because three defects of that exact shape shipped in three days, each
# found by the operator: every one satisfied "exists and is not hidden", which
# is what automation asserts and is not what matters.
ui-visibility:
	$(PYTHON) scripts/check_primary_controls_visible.py --base-url http://$(HOST):$(PORT)

# Warns before the authoring route's certification lapses. Needs the service
# environment, so it is normally run on the deployment host.
# Fails when the page states something the retained runs do not support. The
# worst defect this demo had was well-rendered prose describing an experiment it
# was not running, which every element-level check passed over.
claims-check:
	$(PYTHON) scripts/check_page_claims_match_evidence.py

authoring-route-health:
	$(PYTHON) scripts/check_authoring_route_health.py

# Re-certifies and installs the authoring route when its margin is short, so a
# lapsed certification never has to be noticed as a disabled button. Reads the
# service environment from the launchd plist itself; deployment host only.
authoring-route-refresh:
	$(PYTHON) scripts/refresh_authoring_certification.py $(REFRESH_ARGS)

test:
	$(PYTHON) -m pytest -q tests

typecheck:
	$(PYTHON) -m mypy

deploy-check:
	bash -n deploy/run-with-provider-secret.sh

check: typecheck test ui-build assets-check deploy-check

serve:
	$(PYTHON) -m uvicorn cybernetic_influence.api:app --host $(HOST) --port $(PORT)

PROJECT_STATUS_PYTHON ?= $(if $(strip $(PYTHON)),$(PYTHON),$(if $(wildcard .venv/bin/python),.venv/bin/python,python3))
PROJECT_STATUS_SCRIPT ?= scripts/meta/project_status.py
status:  ## Verify repository authority freshness and show branch status
	@$(PROJECT_STATUS_PYTHON) $(PROJECT_STATUS_SCRIPT) --repo-root .

# >>> META-PROCESS WORKTREE TARGETS >>>
PYTHON ?= python3
WORKTREE_CREATE_SCRIPT := scripts/meta/worktree-coordination/create_worktree.py
WORKTREE_REMOVE_SCRIPT := scripts/meta/worktree-coordination/safe_worktree_remove.py
WORKTREE_CLAIMS_SCRIPT := scripts/meta/worktree-coordination/../check_coordination_claims.py
WORKTREE_SESSION_START_SCRIPT := scripts/meta/worktree-coordination/../session_start.py
WORKTREE_SESSION_HEARTBEAT_SCRIPT := scripts/meta/worktree-coordination/../session_heartbeat.py
WORKTREE_SESSION_STATUS_SCRIPT := scripts/meta/worktree-coordination/../session_status.py
WORKTREE_SESSION_END_SCRIPT := scripts/meta/worktree-coordination/../session_end.py
WORKTREE_SESSION_FINISH_SCRIPT := scripts/meta/worktree-coordination/../session_finish.py
WORKTREE_SESSION_CLOSE_SCRIPT := scripts/meta/worktree-coordination/../session_close.py
WORKTREE_REVIEW_CLAIM_SCRIPT := scripts/meta/worktree-coordination/create_review_claim.py
WORKTREE_RAISE_CONCERN_SCRIPT := scripts/meta/worktree-coordination/raise_concern.py
WORKTREE_PLAN_READINESS_SCRIPT := scripts/meta/worktree-coordination/../check_plan_readiness.py
SURFACE_RUNTIME_SCRIPT := scripts/meta/worktree-coordination/../surface_runtime.py
WORKTREE_DIR ?= $(shell $(PYTHON) "$(WORKTREE_CREATE_SCRIPT)" --repo-root . --print-default-worktree-dir)
WORKTREE_START_POINT ?= HEAD
WORKTREE_PROJECT ?= $(shell $(PYTHON) "$(WORKTREE_CREATE_SCRIPT)" --repo-root . --print-canonical-project)
WORKTREE_AGENT ?= $(shell if [ -n "$$CODEX_THREAD_ID" ]; then printf codex; elif [ -n "$$CLAUDE_SESSION_ID" ] || [ -n "$$CLAUDE_CODE_SSE_PORT" ]; then printf claude-code; elif [ -n "$$OPENCLAW_SESSION_ID" ] || [ -n "$$OPENCLAW_RUN_ID" ]; then printf openclaw; fi)
SESSION_GOAL ?=
SESSION_PHASE ?=
SESSION_NEXT ?=
SESSION_DEPENDS ?=
SESSION_STOP_CONDITIONS ?=
SESSION_NOTE ?=
SESSION_ALLOW_PARALLEL ?=
ALLOW_UNPLANNED ?=
PLAN_RESUME ?=
WORKTREE_EXECUTION_PROFILE ?= coordinated
PLAN_PROJECT ?= $(WORKTREE_PROJECT)
PLAN_READINESS_COMMAND ?=
SESSION_CLAIM_TYPE ?= program
SESSION_PARENT_SCOPE ?=
SESSION_WRITE_PATHS ?=
SESSION_READ_PATHS ?=
WORKTREE_DISPOSITION ?= merged
WORKTREE_DISPOSITION_REASON ?=
WORKTREE_RECOVERY_REF ?=
WORKTREE_ALLOW_DISCARD_UNIQUE ?=
WORKTREE_MERGE_COMMIT ?=
REVIEW_SCOPE ?=
REVIEW_NOTES ?=
RECIPIENT ?=

.PHONY: worktree maintenance-worktree worktree-list worktree-remove session-start session-heartbeat session-status session-end session-finish session-close review-claim raise-concern verification-batch-freeze verification-batch-check verification-batch-thaw surface-up surface-preview surface-status surface-down surface-audit

verification-batch-freeze:  ## Freeze clean HEAD for DECISION="..." VERIFY_COMMAND="..."
	@test -n "$(DECISION)" || (echo "DECISION is required" && exit 1)
	@test -n "$(VERIFY_COMMAND)" || (echo "VERIFY_COMMAND is required" && exit 1)
	$(PYTHON) scripts/meta/verification_batch.py --repo-root . freeze --decision "$(DECISION)" --command "$(VERIFY_COMMAND)" $(if $(ALLOW_UNTRACKED),--allow-untracked "$(ALLOW_UNTRACKED)",)

verification-batch-check:  ## Require the active batch to match exact clean HEAD
	$(PYTHON) scripts/meta/verification_batch.py --repo-root . check --require-active

verification-batch-thaw:  ## Invalidate the batch with REASON="..." before a scoped fix
	@test -n "$(REASON)" || (echo "REASON is required" && exit 1)
	$(PYTHON) scripts/meta/verification_batch.py --repo-root . thaw --reason "$(REASON)"

worktree:  ## Create claimed worktree (BRANCH=name TASK="..." [PLAN=N] [AGENT=name])
ifndef BRANCH
	$(error BRANCH is required. Usage: make worktree BRANCH=plan-42-feature TASK="Describe the task")
endif
ifndef TASK
	$(error TASK is required. Usage: make worktree BRANCH=plan-42-feature TASK="Describe the task")
endif
ifndef SESSION_GOAL
	$(error SESSION_GOAL is required. Name the broader objective, not the local branch)
endif
ifndef SESSION_PHASE
	$(error SESSION_PHASE is required. Describe the current execution phase)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@if [ ! -f "$(WORKTREE_CREATE_SCRIPT)" ]; then \
		echo "Missing worktree coordination module: $(WORKTREE_CREATE_SCRIPT)"; \
		echo "Install or sync the sanctioned worktree-coordination module before using make worktree."; \
		exit 1; \
	fi
	@if [ ! -f "$(WORKTREE_CLAIMS_SCRIPT)" ]; then \
		echo "Missing worktree coordination module: $(WORKTREE_CLAIMS_SCRIPT)"; \
		echo "Install or sync the sanctioned worktree-coordination module before using make worktree."; \
		exit 1; \
	fi
	@if [ ! -f "$(WORKTREE_SESSION_START_SCRIPT)" ]; then \
		echo "Missing session lifecycle module: $(WORKTREE_SESSION_START_SCRIPT)"; \
		echo "Install or sync the sanctioned session lifecycle module before using make worktree."; \
		exit 1; \
	fi
	@$(PYTHON) "$(WORKTREE_PLAN_READINESS_SCRIPT)" \
		$(if $(PLAN),--qualified-plan-id "$(PLAN_PROJECT)#$(PLAN)",) \
		--execution-profile "$(WORKTREE_EXECUTION_PROFILE)" \
		$(if $(PLAN_READINESS_COMMAND),--query-command "$(PLAN_READINESS_COMMAND)",) \
		--repository "$(WORKTREE_PROJECT)" \
		--lane-id "$(BRANCH)" \
		$(if $(SESSION_PARENT_SCOPE),--parent-lane-id "$(SESSION_PARENT_SCOPE)",) \
		--branch "$(BRANCH)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		--agent "$(WORKTREE_AGENT)" \
		--scope "$(BRANCH)" \
		$(if $(ALLOW_UNPLANNED),--allow-unplanned,) \
		$(if $(PLAN_RESUME),--resume,)
	@$(PYTHON) "$(WORKTREE_CLAIMS_SCRIPT)" --claim \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--intent "$(TASK)" \
		--claim-type "$(SESSION_CLAIM_TYPE)" \
		--branch "$(BRANCH)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		--session-name "$(SESSION_GOAL)" \
		$(if $(SESSION_PARENT_SCOPE),--parent-scope "$(SESSION_PARENT_SCOPE)",) \
		$(if $(filter 1 true yes,$(SESSION_ALLOW_PARALLEL)),--allow-parallel,) \
		$(foreach path,$(SESSION_WRITE_PATHS),--write-path "$(path)") \
		$(foreach path,$(SESSION_READ_PATHS),--read-path "$(path)") \
		$(if $(PLAN),--plan "$(PLAN_PROJECT)#$(PLAN)",)
	@mkdir -p "$(WORKTREE_DIR)"
	@if ! $(PYTHON) "$(WORKTREE_CREATE_SCRIPT)" --repo-root . --path "$(WORKTREE_DIR)/$(BRANCH)" --branch "$(BRANCH)" --start-point "$(WORKTREE_START_POINT)"; then \
		$(PYTHON) "$(WORKTREE_CLAIMS_SCRIPT)" --release --agent "$(WORKTREE_AGENT)" --project "$(WORKTREE_PROJECT)" --scope "$(BRANCH)" >/dev/null 2>&1 || true; \
		exit 1; \
	fi
	@if ! $(PYTHON) "$(WORKTREE_SESSION_START_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--intent "$(TASK)" \
		--repo-root "$(CURDIR)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		--branch "$(BRANCH)" \
		--broader-goal "$(SESSION_GOAL)" \
		--current-phase "$(SESSION_PHASE)" \
		--claim-type "$(SESSION_CLAIM_TYPE)" \
		$(if $(SESSION_PARENT_SCOPE),--parent-scope "$(SESSION_PARENT_SCOPE)",) \
		$(if $(filter 1 true yes,$(SESSION_ALLOW_PARALLEL)),--allow-parallel,) \
		$(foreach path,$(SESSION_WRITE_PATHS),--write-path "$(path)") \
		$(foreach path,$(SESSION_READ_PATHS),--read-path "$(path)") \
		$(if $(PLAN),--plan "$(PLAN_PROJECT)#$(PLAN)",) \
		$(if $(ALLOW_UNPLANNED),--allow-unplanned,) \
		$(if $(SESSION_NEXT),--next-phase "$(SESSION_NEXT)",) \
		$(if $(SESSION_DEPENDS),--depends-on "$(SESSION_DEPENDS)",) \
		$(if $(SESSION_STOP_CONDITIONS),--stop-condition "$(SESSION_STOP_CONDITIONS)",) \
		$(if $(SESSION_NOTE),--notes "$(SESSION_NOTE)",); then \
		git worktree remove --force "$(WORKTREE_DIR)/$(BRANCH)" >/dev/null 2>&1 || true; \
		git branch -D "$(BRANCH)" >/dev/null 2>&1 || true; \
		$(PYTHON) "$(WORKTREE_CLAIMS_SCRIPT)" --release --agent "$(WORKTREE_AGENT)" --project "$(WORKTREE_PROJECT)" --scope "$(BRANCH)" >/dev/null 2>&1 || true; \
		exit 1; \
	fi
	@echo ""
	@echo "Worktree created at $(WORKTREE_DIR)/$(BRANCH)"
	@echo "Claim created for branch $(BRANCH)"
	@echo "Session contract started for $(SESSION_GOAL)"

maintenance-worktree:  ## Create a claimed light maintenance worktree without a numbered plan
	@if [ -n "$(PLAN)" ]; then \
		echo "maintenance-worktree is only for explicitly unplanned light maintenance; use make worktree PLAN=N for plan-owned work."; \
		exit 2; \
	fi
	@$(MAKE) worktree \
		BRANCH="$(BRANCH)" TASK="$(TASK)" WORKTREE_AGENT="$(WORKTREE_AGENT)" \
		SESSION_GOAL="$(SESSION_GOAL)" SESSION_PHASE="$(SESSION_PHASE)" \
		SESSION_NEXT="$(SESSION_NEXT)" SESSION_DEPENDS="$(SESSION_DEPENDS)" \
		SESSION_STOP_CONDITIONS="$(SESSION_STOP_CONDITIONS)" SESSION_NOTE="$(SESSION_NOTE)" \
		SESSION_CLAIM_TYPE="$(SESSION_CLAIM_TYPE)" SESSION_PARENT_SCOPE="$(SESSION_PARENT_SCOPE)" \
		SESSION_ALLOW_PARALLEL="$(SESSION_ALLOW_PARALLEL)" \
		SESSION_WRITE_PATHS="$(SESSION_WRITE_PATHS)" SESSION_READ_PATHS="$(SESSION_READ_PATHS)" \
		WORKTREE_EXECUTION_PROFILE=light ALLOW_UNPLANNED=1

session-start:  ## Create or refresh the active session contract for BRANCH=name
ifndef BRANCH
	$(error BRANCH is required. Usage: make session-start BRANCH=plan-42-feature TASK="..." SESSION_GOAL="..." SESSION_PHASE="...")
endif
ifndef TASK
	$(error TASK is required. Usage: make session-start BRANCH=plan-42-feature TASK="...")
endif
ifndef SESSION_GOAL
	$(error SESSION_GOAL is required. Name the broader objective, not the local branch)
endif
ifndef SESSION_PHASE
	$(error SESSION_PHASE is required. Describe the current execution phase)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@$(PYTHON) "$(WORKTREE_SESSION_START_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--intent "$(TASK)" \
		--repo-root "$(CURDIR)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		--branch "$(BRANCH)" \
		--broader-goal "$(SESSION_GOAL)" \
		--current-phase "$(SESSION_PHASE)" \
		--claim-type "$(SESSION_CLAIM_TYPE)" \
		$(if $(SESSION_PARENT_SCOPE),--parent-scope "$(SESSION_PARENT_SCOPE)",) \
		$(if $(filter 1 true yes,$(SESSION_ALLOW_PARALLEL)),--allow-parallel,) \
		$(foreach path,$(SESSION_WRITE_PATHS),--write-path "$(path)") \
		$(foreach path,$(SESSION_READ_PATHS),--read-path "$(path)") \
		$(if $(PLAN),--plan "Plan #$(PLAN)",) \
		$(if $(ALLOW_UNPLANNED),--allow-unplanned,) \
		$(if $(SESSION_NEXT),--next-phase "$(SESSION_NEXT)",) \
		$(if $(SESSION_DEPENDS),--depends-on "$(SESSION_DEPENDS)",) \
		$(if $(SESSION_STOP_CONDITIONS),--stop-condition "$(SESSION_STOP_CONDITIONS)",) \
		$(if $(SESSION_NOTE),--notes "$(SESSION_NOTE)",)

session-heartbeat:  ## Refresh heartbeat and optional phase for BRANCH=name
ifndef BRANCH
	$(error BRANCH is required. Usage: make session-heartbeat BRANCH=plan-42-feature)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@$(PYTHON) "$(WORKTREE_SESSION_HEARTBEAT_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--branch "$(BRANCH)" \
		$(if $(SESSION_PHASE),--current-phase "$(SESSION_PHASE)",)

session-status:  ## Show live session summaries for this repo
	@$(PYTHON) "$(WORKTREE_SESSION_STATUS_SCRIPT)" --project "$(WORKTREE_PROJECT)"

session-end:  ## Retire this runtime session's live claims without deleting Git work
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@$(PYTHON) "$(WORKTREE_SESSION_END_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		$(if $(SESSION_NOTE),--reason "$(SESSION_NOTE)",)

session-finish:  ## Finish the session for BRANCH=name; blocks if the worktree is dirty
ifndef BRANCH
	$(error BRANCH is required. Usage: make session-finish BRANCH=plan-42-feature)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@$(PYTHON) "$(WORKTREE_SESSION_FINISH_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		$(if $(SESSION_NOTE),--note "$(SESSION_NOTE)",)

session-close:  ## Close the claimed lane for BRANCH=name: cleanup worktree + branch + claim together
ifndef BRANCH
	$(error BRANCH is required. Usage: make session-close BRANCH=plan-42-feature)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@$(PYTHON) "$(WORKTREE_SESSION_CLOSE_SCRIPT)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--scope "$(BRANCH)" \
		--worktree-path "$(WORKTREE_DIR)/$(BRANCH)" \
		--branch "$(BRANCH)" \
		--disposition "$(WORKTREE_DISPOSITION)" \
		--disposition-reason "$(WORKTREE_DISPOSITION_REASON)" \
		--recovery-ref "$(WORKTREE_RECOVERY_REF)" \
		$(if $(filter 1 true yes,$(WORKTREE_ALLOW_DISCARD_UNIQUE)),--allow-discard-unique,) \
		$(if $(WORKTREE_MERGE_COMMIT),--merge-commit "$(WORKTREE_MERGE_COMMIT)",) \
		$(if $(SESSION_NOTE),--note "$(SESSION_NOTE)",)

worktree-list:  ## Show claimed worktree coordination status
	@if [ ! -f "$(WORKTREE_CLAIMS_SCRIPT)" ]; then \
		echo "Missing worktree coordination module: $(WORKTREE_CLAIMS_SCRIPT)"; \
		echo "Install or sync the sanctioned worktree-coordination module before using make worktree-list."; \
		exit 1; \
	fi
	@$(PYTHON) "$(WORKTREE_CLAIMS_SCRIPT)" --list

worktree-remove:  ## Safely remove worktree for BRANCH=name
ifndef BRANCH
	$(error BRANCH is required. Usage: make worktree-remove BRANCH=plan-42-feature)
endif
	@if [ ! -f "$(WORKTREE_SESSION_CLOSE_SCRIPT)" ]; then \
		echo "Missing session lifecycle module: $(WORKTREE_SESSION_CLOSE_SCRIPT)"; \
		echo "Install or sync the sanctioned session lifecycle module before using make worktree-remove."; \
		exit 1; \
	fi
	@$(MAKE) session-close BRANCH="$(BRANCH)" \
		$(if $(WORKTREE_MERGE_COMMIT),WORKTREE_MERGE_COMMIT="$(WORKTREE_MERGE_COMMIT)",) \
		$(if $(SESSION_NOTE),SESSION_NOTE="$(SESSION_NOTE)",)

review-claim:  ## Create a review claim for TARGET_BRANCH=name WRITE_PATHS="a|b" TASK="..."
ifndef TARGET_BRANCH
	$(error TARGET_BRANCH is required. Usage: make review-claim TARGET_BRANCH=plan-42-feature WRITE_PATHS="src/foo.py|tests/test_foo.py" TASK="Review concern")
endif
ifndef WRITE_PATHS
	$(error WRITE_PATHS is required. Provide one or more repo-relative paths separated by '|')
endif
ifndef TASK
	$(error TASK is required. Describe the review intent)
endif
ifndef SESSION_GOAL
	$(error SESSION_GOAL is required. Name the broader review objective)
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
	@$(PYTHON) "$(WORKTREE_REVIEW_CLAIM_SCRIPT)" \
		--repo-root "$(CURDIR)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--target-branch "$(TARGET_BRANCH)" \
		--intent "$(TASK)" \
		--session-name "$(SESSION_GOAL)" \
		--write-path "$(WRITE_PATHS)" \
		$(if $(PLAN),--plan "Plan #$(PLAN)",) \
		$(if $(REVIEW_SCOPE),--scope "$(REVIEW_SCOPE)",) \
		$(if $(REVIEW_NOTES),--notes "$(REVIEW_NOTES)",)

raise-concern:  ## Route concern to TARGET_BRANCH via PR comment or local inbox
ifndef TARGET_BRANCH
	$(error TARGET_BRANCH is required. Usage: make raise-concern TARGET_BRANCH=plan-42-feature SUBJECT="..." MESSAGE="...")
endif
ifndef SUBJECT
	$(error SUBJECT is required. Usage: make raise-concern TARGET_BRANCH=plan-42-feature SUBJECT="..." MESSAGE="...")
endif
ifndef WORKTREE_AGENT
	$(error Unable to infer agent runtime. Set AGENT via WORKTREE_AGENT=codex|claude-code|openclaw)
endif
ifndef MESSAGE
ifndef MESSAGE_FILE
	$(error MESSAGE or MESSAGE_FILE is required. Provide inline content or a path to a concern file)
endif
endif
	@$(PYTHON) "$(WORKTREE_RAISE_CONCERN_SCRIPT)" \
		--repo-root "$(CURDIR)" \
		--agent "$(WORKTREE_AGENT)" \
		--project "$(WORKTREE_PROJECT)" \
		--target-branch "$(TARGET_BRANCH)" \
		--subject "$(SUBJECT)" \
		$(if $(MESSAGE),--content "$(MESSAGE)",) \
		$(if $(MESSAGE_FILE),--content-file "$(MESSAGE_FILE)",) \
		$(if $(RECIPIENT),--recipient "$(RECIPIENT)",)

surface-up:  ## Start the registered canonical UI (SURFACE=id)
	@test -n "$(SURFACE)" || { echo "SURFACE is required" >&2; exit 2; }
	$(PYTHON) "$(SURFACE_RUNTIME_SCRIPT)" --repo-root . up "$(SURFACE)"

surface-preview:  ## Start a registered preview on noncanonical ports (SURFACE=id)
	@test -n "$(SURFACE)" || { echo "SURFACE is required" >&2; exit 2; }
	$(PYTHON) "$(SURFACE_RUNTIME_SCRIPT)" --repo-root . up "$(SURFACE)" --mode preview

surface-status:  ## Show exact surface leases
	$(PYTHON) "$(SURFACE_RUNTIME_SCRIPT)" --repo-root . status

surface-down:  ## Stop the exact selected surface lease (SURFACE=id [LEASE=id])
	@test -n "$(SURFACE)" || { echo "SURFACE is required" >&2; exit 2; }
	$(PYTHON) "$(SURFACE_RUNTIME_SCRIPT)" --repo-root . down "$(SURFACE)" $(if $(LEASE),--lease-id "$(LEASE)",)

surface-audit:  ## Compare registry, lease, process, and served identity (SURFACE=id)
	@test -n "$(SURFACE)" || { echo "SURFACE is required" >&2; exit 2; }
	$(PYTHON) "$(SURFACE_RUNTIME_SCRIPT)" --repo-root . audit "$(SURFACE)" $(if $(REQUIRE_RUNNING),--require-running,)
# <<< META-PROCESS WORKTREE TARGETS <<<
