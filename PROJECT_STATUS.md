# Project Status

This document summarizes the current generic MVP state for the Standup Pre-Read Assistant and the likely next milestones. It intentionally avoids work-specific names, URLs, project keys, and team names.

## v0.6.0 Draft Status: Real Jira MCP Connector Readiness

The current draft milestone adds the application-side `jira_mcp` source mode, Jira MCP config fields, source health reporting, and a safe `JiraMcpConnector` boundary for a future approved work-environment implementation. Real execution remains disabled by default through `security.allow_live_connectors: false`; this repository raises a clear runtime-unavailable error before credentials, network calls, or Jira requests can be attempted. `jira_mcp_sample` remains the deterministic local MCP-shaped path for CI and evaluation.

## v0.4.0 Draft Status: Real Connector Readiness

The v0.4.0 connector contract validation exists and documents/enforces the connector boundary without adding live integrations. The connector contract in [docs/CONNECTOR_CONTRACT.md](docs/CONNECTOR_CONTRACT.md) defines the `SourceData` envelope, required and optional payload fields, source reference expectations, timestamp and confidence guidance, clear validation errors, local-only versus live connector rules, and no-secrets guidance. The local `sample` and `jira_mcp_sample` connectors now run lightweight validation before normalization so future connector work has a clear compatibility target while CI and evaluation remain deterministic.

## v0.3.0 Draft Status: Local GitHub PR Intelligence

The current draft milestone improves sample-only GitHub PR understanding while keeping live integrations out of scope. Local PR fixtures include richer states for review requested, changes requested, approved, merged, failing CI, stale open PRs, blocked merge state, missing linked issue, unclear owner, and decision-dependent PRs. Normalized PR activities preserve review, CI, merge, reviewer, approval, requested-change, draft, author/owner, linked-issue, timestamp, and source-reference metadata.

The generator uses those signals to route merged PRs to progress, CI/stale/blocked/changes-requested PRs to risks, decision-dependent PRs to decisions and questions, waiting-review PRs to agenda/questions, and no-linked-issue PRs to questions. Structured JSON includes PR metadata on PR-derived items, and the evaluation harness now checks for PR intelligence coverage in addition to the existing sample quality gates.

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


## Integration Reality Check

The local MVP is useful for validating summary structure, source references, PR intelligence, review metadata, and evaluation quality. Real product value for a pilot still requires approved live Jira, GitHub, and Slack or Teams integrations so the pre-read reflects actual team activity instead of checked-in fixtures. The next live integration milestone is the real Jira MCP connector, because issue status, blockers, decisions, and carryover are the core inputs for a trustworthy standup pre-read. The application now recognizes `jira_mcp` and has a safe adapter boundary, but real execution still must be tested and wired only inside an approved work MCP environment.

The v0.5.0 integration config foundation adds `config/example-team.yaml` for sanitized team-level settings, and v0.6.0 adds Jira MCP readiness without live connector network calls or secrets.

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

The repository now includes a local mock Jira MCP sample adapter for fixture-based validation. The real MCP-based issue connector mode is now recognized and fails safely in local runtimes. Loading live issue data remains work-environment implementation/testing work and should only run in an approved MCP environment while preserving the existing normalized activity model.

### Future GitHub API Connector

Add a future source hosting connector that can load live pull request and repository activity through an API while preserving sample mode for tests and demos.
