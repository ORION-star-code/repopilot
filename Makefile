PYTHON ?= python

.PHONY: setup dev test lint harness-check check

setup:
	$(PYTHON) -m pip install -e ".[dev]"

dev:
	$(PYTHON) scripts/repopilot.py --help

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) scripts/lint.py

harness-check:
	$(PYTHON) harness/validate.py

check:
	$(PYTHON) scripts/check.py
