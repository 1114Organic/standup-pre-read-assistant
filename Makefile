.PHONY: test lint typecheck demo check

test:
	python -m pytest

lint:
	python -m ruff check .

typecheck:
	python -m mypy

demo:
	PYTHONPATH=src python -m standup_pre_read.cli --source-mode sample --output-path output/standup-pre-read.md

check: test lint typecheck
