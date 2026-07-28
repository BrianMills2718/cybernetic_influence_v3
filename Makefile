VENV ?= .venv
PYTHON := $(VENV)/bin/python
LLM_CLIENT_ROOT ?= ../active/llm_client
HOST ?= 127.0.0.1
PORT ?= 8620

.PHONY: install ui-install ui-build test typecheck deploy-check check serve

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

test:
	$(PYTHON) -m pytest -q tests

typecheck:
	$(PYTHON) -m mypy

deploy-check:
	bash -n deploy/run-with-provider-secret.sh

check: typecheck test ui-build deploy-check

serve:
	$(PYTHON) -m uvicorn cybernetic_influence.api:app --host $(HOST) --port $(PORT)
