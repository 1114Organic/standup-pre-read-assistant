# Project Status

This document summarizes the current generic MVP state for the Standup Pre-Read Assistant and the likely next milestones. It intentionally avoids work-specific names, URLs, project keys, and team names.

## 1. What the App Does Today

The current MVP generates a local markdown standup pre-read from sample input files. In sample mode, it:

- Loads sample issue data, a local mock Jira MCP-style response file, sample pull request data, optional sample chat messages, and prior standup notes from the repository.
- Normalizes those inputs into a common activity model.
- Produces a markdown pre-read with sections for executive summary, recent progress, blockers, decisions, risks, carryover, a suggested agenda, concise source-backed standup questions, and source references, including useful chat-derived signals when a chat sample is supplied.
- Optionally writes a structured JSON version of the same pre-read content for downstream tools, including local facilitator review metadata.
- Marks generated pre-reads as `draft` by default, with local-only `approved` and `rejected` review statuses available through CLI options.
- Writes the generated markdown draft to a local output path, defaulting to `output/standup-pre-read.md`.
- Fails fast with a clear CLI error when an unsupported source mode is requested.
- Provides a v0.2.0 sample evaluation harness through `make evaluate`, covering default sample, rich sample, rich chat sample, and local `jira_mcp_sample` scenarios with markdown and JSON outputs.

The MVP is designed as a thin slice that proves the pre-read generation flow before adding live integrations.

The local MVP has been documented as the `v0.1.0` demo baseline in `RELEASE_NOTES.md` for use as a stable checkpoint before live connector work begins.

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

To also write structured JSON output:

```bash
PYTHONPATH=src python -m standup_pre_read.cli \
  --source-mode sample \
  --chat-path examples/chat-rich-sample.json \
  --output-path output/custom-pre-read.md \
  --json-output-path output/custom-pre-read.json
```

Run the local mock Jira MCP sample mode:

```bash
PYTHONPATH=src python -m standup_pre_read.cli \
  --source-mode jira_mcp_sample \
  --jira-mcp-path examples/jira-mcp-sample-response.json \
  --output-path output/jira-mcp-standup-pre-read.md \
  --json-output-path output/jira-mcp-standup-pre-read.json
```

The JSON file is generated from the same structured pre-read document as the markdown draft. It includes `generated_at`, `source_mode`, `team_name` when configured, data window when available, the executive summary, progress, blockers, decisions, risks, carryover, suggested agenda, suggested questions, and source references. List items include `text` and `source_refs`, plus confidence and related work items when available. Review metadata includes `review_status` by default and may include `reviewed_at`, `reviewer`, and `review_notes`.

To approve a local draft and write a separate approved markdown copy:

```bash
PYTHONPATH=src python -m standup_pre_read.cli \
  --source-mode sample \
  --output-path output/reviewed-pre-read.md \
  --json-output-path output/reviewed-pre-read.json \
  --review-status approved \
  --reviewer "Facilitator" \
  --review-notes "Ready to share." \
  --approved-output-path output/approved-pre-read.md
```

To reject a draft locally without writing an approved copy:

```bash
PYTHONPATH=src python -m standup_pre_read.cli \
  --source-mode sample \
  --output-path output/rejected-pre-read.md \
  --json-output-path output/rejected-pre-read.json \
  --review-status rejected \
  --reviewer "Facilitator" \
  --review-notes "Needs edits." \
  --approved-output-path output/should-not-be-written.md
```

You can also use the Makefile demo target:

```bash
make demo
```

## 3. What Data Sources Are Supported Today

Supported today:

- Sample issue JSON stored in the repository through `--source-mode sample`.
- Local mock Jira MCP-style response JSON stored in the repository through `--source-mode jira_mcp_sample` and `--jira-mcp-path examples/jira-mcp-sample-response.json`.
- Sample pull request JSON stored in the repository.
- Sample prior standup markdown stored in the repository.
- Optional local sample Slack/Teams-style chat JSON stored in the repository via `--chat-path`.

Supported source modes are `sample` and `jira_mcp_sample`. The Jira MCP sample mode is a local mock/sample connector only: it adapts a generic MCP tool-response fixture into the existing normalized activity model, does not contact a real MCP server, does not call Jira, and requires no credentials. The source loading layer is intentionally separated from normalization and generation so future connectors can be added without rewriting the whole flow.

## 4. What Is Intentionally Out of Scope for the MVP

The MVP intentionally does not include:

- Live issue tracker API calls.
- Live source hosting API calls.
- MCP-backed live connectors. Real Jira MCP integration remains future work and requires an approved work environment, approved connection details, and appropriate credentials/secrets handling.
- Live chat, email, or notification delivery. Local sample chat JSON ingestion is supported for MVP validation.
- Deployment automation or cloud runtime configuration.
- Authentication, authorization, or secret management for external services.
- Persistent storage beyond writing generated markdown/JSON and approved markdown copies locally.
- Project-specific naming, URLs, keys, or team-specific assumptions.

These are deferred until the generated pre-read format and quality are useful with sample data.

## 5. What Quality Checks Exist

Current quality checks are available through Makefile targets:

```bash
make test
make lint
make typecheck
make check
make evaluate
```

`make check` runs the full local verification set:

- Unit tests with `pytest`.
- Linting with `ruff`.
- Static type checking with `mypy`.

The evaluation harness writes `output/evaluation-report.md` and `output/evaluation-report.json` and validates required sections, blockers, decisions, carryover, resolved carryover exclusion, source references, JSON priority fields, and JSON `review_status`. The test suite verifies scenario definitions, validation checks, report writing, default draft review status, approved and rejected review metadata, approved-output write behavior, generated markdown and JSON output structures, key data-driven content, source-backed bullets and standup questions, configurable output writing, CLI argument parsing, default sample-mode behavior, rich sample JSON generation, chat sample loading and generation, and clean failure for unsupported source modes.

## 6. Suggested Next Milestones

### Richer Sample Dataset

Expand the sample inputs to cover more realistic edge cases, such as multiple repositories, more issue statuses, aging work, resolved carryover, missing optional fields, and mixed review or CI states.

### Standup Question Mode

Standup question mode is now part of the markdown MVP output. A future enhancement could expose the same source-backed questions as a separate CLI/output mode for facilitators who only need the question list.

### Facilitator Review Mode

Facilitator review mode is now available as a local file-based workflow. Future enhancements can refine review metadata or add schema versioning while preserving the no-live-integration MVP boundary.

### Structured Output JSON

Structured JSON output is now available via `--json-output-path`. Future enhancements can add schema versioning after the local sample-mode shape is validated.

### Future Jira MCP Connector

The repository now includes a local mock Jira MCP sample adapter for fixture-based validation. A real MCP-based issue connector that loads live issue data remains future work and should only be added in an approved work environment while preserving the existing normalized activity model.

### Future GitHub API Connector

Add a future source hosting connector that can load live pull request and repository activity through an API while preserving sample mode for tests and demos.
