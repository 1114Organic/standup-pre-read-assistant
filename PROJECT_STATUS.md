# Project Status

This document summarizes the current generic MVP state for the Standup Pre-Read Assistant and the likely next milestones. It intentionally avoids work-specific names, URLs, project keys, and team names.

## 1. What the App Does Today

The current MVP generates a local markdown standup pre-read from sample input files. In sample mode, it:

- Loads sample issue data, sample pull request data, and prior standup notes from the repository.
- Normalizes those inputs into a common activity model.
- Produces a markdown pre-read with sections for executive summary, recent progress, blockers, decisions, risks, carryover, a suggested agenda, and source references.
- Writes the generated draft to a local output path, defaulting to `output/standup-pre-read.md`.
- Fails fast with a clear CLI error when an unsupported source mode is requested.

The MVP is designed as a thin slice that proves the pre-read generation flow before adding live integrations.

## 2. How to Run It Locally

Create and activate a virtual environment, then install the project with development tooling:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the generator in the default sample mode:

```bash
PYTHONPATH=src python -m standup_pre_read.cli
```

Or, after installing the package, run:

```bash
standup-pre-read
```

To choose an explicit output path:

```bash
PYTHONPATH=src python -m standup_pre_read.cli --source-mode sample --output-path output/custom-pre-read.md
```

You can also use the Makefile demo target:

```bash
make demo
```

## 3. What Data Sources Are Supported Today

Supported today:

- Sample issue JSON stored in the repository.
- Sample pull request JSON stored in the repository.
- Sample prior standup markdown stored in the repository.

The only supported source mode is `sample`. The source loading layer is intentionally separated from normalization and generation so future connectors can be added without rewriting the whole flow.

## 4. What Is Intentionally Out of Scope for the MVP

The MVP intentionally does not include:

- Live issue tracker API calls.
- Live source hosting API calls.
- MCP-backed live connectors.
- Chat, email, or notification delivery.
- Deployment automation or cloud runtime configuration.
- Authentication, authorization, or secret management for external services.
- Persistent storage beyond writing the generated markdown file locally.
- Project-specific naming, URLs, keys, or team-specific assumptions.

These are deferred until the generated pre-read format and quality are useful with sample data.

## 5. What Quality Checks Exist

Current quality checks are available through Makefile targets:

```bash
make test
make lint
make typecheck
make check
```

`make check` runs the full local verification set:

- Unit tests with `pytest`.
- Linting with `ruff`.
- Static type checking with `mypy`.

The test suite verifies the generated output structure, key data-driven content, source references, configurable output writing, CLI argument parsing, default sample-mode behavior, and clean failure for unsupported source modes.

## 6. Suggested Next Milestones

### Richer Sample Dataset

Expand the sample inputs to cover more realistic edge cases, such as multiple repositories, more issue statuses, aging work, resolved carryover, missing optional fields, and mixed review or CI states.

### Standup Question Mode

Add a mode that outputs suggested questions for the standup facilitator, such as who needs help, which decisions are blocking progress, and which stale items need explicit follow-up.

### Structured Output JSON

Add an optional structured JSON output alongside markdown so downstream tools can consume summaries, blockers, decisions, risks, carryover items, and source references programmatically.

### Future Jira MCP Connector

Add a future MCP-based issue connector that can load live issue data through a configurable integration while preserving the existing normalized activity model.

### Future GitHub API Connector

Add a future source hosting connector that can load live pull request and repository activity through an API while preserving sample mode for tests and demos.
