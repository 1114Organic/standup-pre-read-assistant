# Release Notes

## Unreleased / v0.6.0 Draft: Real Jira MCP Connector Readiness

- Added the `jira_mcp` source mode as the application-side boundary for a future approved real Jira MCP connector.
- Added safe Jira MCP configuration fields for `sources.jira.enabled`, `mode`, `mcp_server_name`, `jql`, `project_keys`, `include_comments`, and `max_results` without adding credentials, tokens, real Jira URLs, or work-specific data.
- Added `security.allow_live_connectors` config loading so live connector paths stay disabled by default unless a future approved runtime explicitly opts in.
- Added source health metadata to markdown and JSON so required source failures, optional source failures, and skipped optional sources are visible.
- Real `jira_mcp` execution now fails clearly in this local repository runtime unless an approved MCP runtime implementation is supplied; no credentials, network calls, or Jira requests are attempted.
- Kept `jira_mcp_sample` as the deterministic local MCP-shaped test path and preserved sample/evaluation workflows.

## Unreleased / v0.5.0 Draft: Integration Config Foundation

- Added `ROADMAP.md` to show the path from local MVP through one-team pilot and identify expected inputs, outputs, success criteria, and out-of-scope items for upcoming live integration milestones.
- Added `config/example-team.yaml` as a sanitized, generic team configuration template for future Jira, GitHub, chat, output, review, posting, and security settings.
- Added optional `--config` YAML loading for supported local CLI settings, with explicit CLI flags overriding loaded values.
- Live Jira MCP, GitHub API, Slack, Teams, posting, credentials, deployment, and work-specific data remain out of scope.

## Release: v0.4.0 Connector Contract and Validation

- Added `docs/CONNECTOR_CONTRACT.md` to document source connector purpose, `SourceData` expectations, required and optional fields, source references, timestamp and confidence guidance, validation/error handling, security/no-secrets rules, local-only versus live connector boundaries, and future Jira MCP, GitHub API, and Slack/Teams connector examples.
- Added lightweight connector payload validation for the current local `sample` and `jira_mcp_sample` adapters so malformed required fields fail early with clear field-path errors before normalization.
- Added tests proving both local connector modes satisfy the contract, invalid payloads fail clearly, and the existing evaluation scenarios remain covered.
- No live Jira, Jira MCP, GitHub API, Slack, Teams, deployment, credentials, tokens, or environment-specific configuration were added.


## Release: v0.3.0 Draft GitHub PR Intelligence

This unreleased draft improves local/sample pull request intelligence before any live GitHub API work. It remains generic and local-only.

## What changed

- Expanded the checked-in GitHub PR fixtures to cover review requested, changes requested, approved, merged, failing CI, stale open PRs, blocked PRs, PRs with no linked issue, unclear owner, and PRs waiting on decisions.
- Extended normalization to preserve PR metadata including review state, CI state, merge state, linked issues, reviewers, approvals, requested changes, draft status, owner/author, timestamps, and source references.
- Updated generation so merged PRs appear as progress; failing CI, stale, blocked, and changes-requested PRs appear as risks; waiting-review PRs feed agenda/questions; missing linked issues become questions; and decision-dependent PRs appear in decisions/questions.
- Added PR metadata to structured JSON items where useful and tuned deterministic priority scoring so PR risks rank with other high-signal standup topics.
- Updated the evaluation harness and tests to validate local PR intelligence coverage while preserving sample, `jira_mcp_sample`, rich sample, chat sample, markdown, JSON, facilitator review, and CI-compatible behavior.

## What remains out of scope

- Live GitHub API integration.
- Real Jira MCP or live Jira integration.
- Live Slack, Teams, deployment, credentials, work-specific project keys, URLs, channel names, or team names.

## Release: v0.2.0 Evaluation Harness

This release checkpoint documents v0.2.0 as the local evaluation and validation release for the standup pre-read assistant. It keeps the application behavior unchanged and focuses on repeatable quality checks against checked-in generic sample data.

## What changed

- Added a local-only evaluation harness that runs representative pre-read generation scenarios without calling external services.
- Generates scenario-specific markdown and JSON pre-read outputs under `output/evaluation/` for facilitator review.
- Writes consolidated evaluation reports at `output/evaluation-report.md` and `output/evaluation-report.json`.
- Documents `make evaluate` as the repeatable validation command alongside the existing `make check` quality gate.

## Evaluation scenarios covered

The v0.2.0 harness covers these local sample scenarios:

- `default_sample`: default local issue, pull request, and prior-standup fixtures.
- `rich_sample`: richer local issue, pull request, and prior-standup fixtures without chat input.
- `rich_chat_sample`: richer local fixtures plus local sample Slack/Teams-style chat messages.
- `jira_mcp_sample`: checked-in local mock Jira MCP-style response fixture adapted into the existing sample flow.

All scenarios use generic repository fixtures only. They do not introduce live Jira, real Jira MCP, GitHub API, live Slack or Teams, deployment, credentials, or work-specific data.

## What the harness validates

The evaluation harness validates that generated outputs include the expected MVP shape and quality signals, including:

- Required markdown sections for the standup pre-read.
- Expected blockers, decisions, carryover, and resolved-carryover exclusion behavior.
- Source references for generated summary content.
- Structured JSON output shape and priority fields.
- JSON `review_status` metadata for facilitator-review draft behavior.

## How to run the evaluation

Run the v0.2.0 evaluation harness with:

```bash
make evaluate
```

The harness writes consolidated reports to:

- `output/evaluation-report.md`
- `output/evaluation-report.json`

## Quality checks

Run the full local quality gate with:

```bash
make check
```

`make check` runs tests, linting, and static type checking. For a release checkpoint, run both:

```bash
make check
make evaluate
```

## What remains out of scope

- Live Jira integration.
- Real Jira MCP integration.
- GitHub API integration.
- Live Slack or Teams integration.
- Backstage integration.
- EKS, deployment automation, or cloud runtime configuration.
- Authentication, authorization, and secret management for external systems.
- Persistent storage beyond local generated markdown and JSON files.
- Work-specific names, URLs, project keys, channel names, team names, or proprietary data.

## Release: v0.1.0 Local MVP

This release checkpoint documents the current local MVP as a stable demo baseline before adding live integrations. It is intentionally documentation-focused and preserves the current application behavior.

## What this MVP does

- Generates a local standup pre-read from checked-in sample data.
- Normalizes sample issue, pull request, prior standup, optional chat, and local mock Jira MCP-style activity into a shared activity model.
- Produces concise, source-backed sections for executive summary, progress, blockers, decisions, risks, carryover, suggested agenda, suggested standup questions, and source references.
- Writes generated pre-reads as facilitator-review drafts by default.
- Supports local facilitator review metadata with `draft`, `approved`, and `rejected` review statuses.
- Optionally writes a machine-readable structured JSON pre-read from the same generated document as the markdown output.

## Supported source modes

- `sample`: reads local sample Jira issue JSON plus local sample GitHub PR JSON, prior standup markdown, and optional chat JSON.
- `jira_mcp_sample`: reads a checked-in local mock Jira MCP-style response JSON instead of the direct Jira issue sample, while still using local sample GitHub PR JSON, prior standup markdown, and optional chat JSON.

Both modes are local-only and do not call live services.

## Supported sample inputs

- Jira sample JSON: `examples/jira-sample.json` and the richer `examples/jira-rich-sample.json` fixture.
- GitHub PR sample JSON: `examples/github-pr-sample.json` and the richer `examples/github-pr-rich-sample.json` fixture.
- Prior standup markdown: `examples/prior-standup.md` and the richer `examples/prior-standup-rich.md` fixture.
- Chat sample JSON: `examples/chat-rich-sample.json` for local Slack/Teams-style sample messages.
- Jira MCP-style sample response JSON: `examples/jira-mcp-sample-response.json` for mock MCP adapter validation.

## Supported outputs

- Markdown pre-read, written with `--output-path` and defaulting to `output/standup-pre-read.md`.
- Structured JSON pre-read, written when `--json-output-path` is provided.

The JSON output is generated from the same structured pre-read document as the markdown output, so enabling JSON does not change the markdown draft.

## Priority scoring

The MVP uses deterministic priority scoring to order higher-signal items before routine updates. Blockers, decisions, carryover, failing CI, requested changes, stale or idle pull requests, risk signals, and unclear ownership/status increase priority. Generated questions and structured JSON items carry priority values when available so facilitators can see which topics should be reviewed first.

## Facilitator review workflow

1. Generate a local markdown draft and, optionally, structured JSON output.
2. Review the source-backed summary, agenda, questions, and references.
3. Re-run the CLI with `--review-status approved` or `--review-status rejected` if a local review decision should be stamped into the outputs.
4. Optionally include `--reviewer` and `--review-notes` for local review context.
5. Optionally include `--approved-output-path` to write a separate approved markdown copy only when `--review-status approved` is used.

Rejected drafts keep review metadata in the normal markdown and JSON outputs but do not write an approved copy.

## Demo commands

Standard demo using `make demo`:

```bash
make demo
```

Rich chat demo with markdown and JSON output:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli \
  --source-mode sample \
  --jira-path examples/jira-rich-sample.json \
  --github-path examples/github-pr-rich-sample.json \
  --prior-standup-path examples/prior-standup-rich.md \
  --chat-path examples/chat-rich-sample.json \
  --output-path output/rich-standup-pre-read.md \
  --json-output-path output/rich-standup-pre-read.json
```

Mock Jira MCP demo with markdown and JSON output:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli \
  --source-mode jira_mcp_sample \
  --jira-mcp-path examples/jira-mcp-sample-response.json \
  --output-path output/jira-mcp-standup-pre-read.md \
  --json-output-path output/jira-mcp-standup-pre-read.json
```

## v0.2.0 sample evaluation workflow

`make evaluate` runs a local-only sample evaluation harness across four scenarios: default sample, rich sample, rich chat sample, and local `jira_mcp_sample`. Each scenario writes both markdown and JSON pre-read outputs under `output/evaluation/`. The harness validates required sections, expected blockers, decisions, carryover, resolved carryover exclusion, source references, JSON priorities, and JSON `review_status`, then writes `output/evaluation-report.md` and `output/evaluation-report.json`. The workflow uses only checked-in generic sample data and does not introduce live Jira, real Jira MCP, GitHub API, Slack/Teams, deployment, credentials, or work-specific data.

## Quality checks

Run individual checks:

```bash
make test
make lint
make typecheck
make evaluate
```

Run the full check target:

```bash
make check
```

`make check` runs tests, linting, and type checking.

## What is intentionally out of scope

- Live Jira integration.
- Real Jira MCP integration.
- GitHub API integration.
- Live Slack or Teams integration.
- Backstage integration.
- EKS, deployment automation, or cloud runtime configuration.
- Authentication, authorization, and secret management for external systems.
- Persistent storage beyond local generated markdown and JSON files.
- Work-specific names, URLs, project keys, channel names, team names, or proprietary data.

## Suggested next milestones

- Expand generic sample data to cover more edge cases and multi-repository scenarios.
- Add schema versioning for structured JSON output after the local shape is validated.
- Refine facilitator review metadata while preserving the local-only review workflow.
- Add a real Jira MCP connector only after sample-mode quality is proven and an approved work environment exists.
- Add a future GitHub API connector while preserving sample fixtures for tests and demos.
- Evaluate live chat and notification integrations only after data access, privacy, and review workflows are agreed.
