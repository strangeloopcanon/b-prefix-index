VENV := .venv
PYTHON := $(VENV)/bin/python

.PHONY: setup check test llm-live deps-audit all release clean format lint type bandit detect-secrets

$(VENV)/bin/activate: requirements-dev.txt scripts/bootstrap_env.py
	@if [ ! -d $(VENV) ]; then python3 -m venv $(VENV); fi
	$(PYTHON) scripts/bootstrap_env.py

setup: $(VENV)/bin/activate
	@echo "Environment ready."

format: $(VENV)/bin/activate
	$(PYTHON) -m black prefix_indexer tests

lint: $(VENV)/bin/activate
	$(PYTHON) -m ruff check prefix_indexer tests

type: $(VENV)/bin/activate
	$(PYTHON) -m mypy prefix_indexer

bandit: $(VENV)/bin/activate
	$(PYTHON) -m bandit -q -r prefix_indexer

detect-secrets: $(VENV)/bin/activate
	$(VENV)/bin/detect-secrets scan --all-files --exclude-files '(^|/)(\.venv|\.mypy_cache|\.pytest_cache|\.ruff_cache)/'

check: format lint type bandit detect-secrets

test: $(VENV)/bin/activate
	$(PYTHON) -m pytest

llm-live: $(VENV)/bin/activate
	@echo "llm-live: no LLM integrations defined; skipping."

deps-audit: $(VENV)/bin/activate
	mkdir -p $(VENV)/cache/pip-audit
	PIP_AUDIT_CACHE_DIR=$(VENV)/cache/pip-audit $(VENV)/bin/pip-audit --progress-spinner off --cache-dir $(VENV)/cache/pip-audit -r requirements-dev.txt

all: check test llm-live

release:
	@echo "Release automation not configured for baseline mode."

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache
