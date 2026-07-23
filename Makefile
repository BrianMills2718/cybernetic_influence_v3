VENV ?= .venv
PYTHON := $(VENV)/bin/python
LLM_CLIENT_ROOT ?= ../active/llm_client
HOST ?= 127.0.0.1
PORT ?= 8620

.PHONY: install test typecheck check serve

install:
	python3 -m venv $(VENV) || virtualenv --clear $(VENV)
	$(PYTHON) -m pip install -r requirements-dev.lock
	$(PYTHON) -m pip install -e . --no-deps
	@if test -d '$(LLM_CLIENT_ROOT)/llm_client'; then \
		$(PYTHON) -m pip install -e '$(LLM_CLIENT_ROOT)[structured]'; \
	else \
		echo "Set LLM_CLIENT_ROOT to enable live runs."; \
	fi

test:
	$(PYTHON) -m pytest -q

typecheck:
	$(PYTHON) -m mypy

check: typecheck test

serve:
	$(PYTHON) -m uvicorn cybernetic_influence.api:app --host $(HOST) --port $(PORT)
