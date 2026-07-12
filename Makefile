PYTHON ?= python3

.PHONY: test lint typecheck demo evaluate check

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy

demo:
	PYTHONPATH=src $(PYTHON) -m standup_pre_read.cli --source-mode sample --output-path output/standup-pre-read.md

evaluate:
	PYTHONPATH=src $(PYTHON) -m standup_pre_read.evaluation

check: test lint typecheck
