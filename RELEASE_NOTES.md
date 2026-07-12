# Release Notes

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
