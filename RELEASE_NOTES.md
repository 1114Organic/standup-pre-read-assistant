# Release Notes

## v0.1.0 MVP Demo Baseline

This checkpoint captures the local sample-mode MVP as a stable demo baseline before adding live integrations.

### What the MVP Does

- Generates a local standup pre-read markdown draft from repository sample data.
- Normalizes sample issue, pull request, prior standup, and optional sample chat activity into a shared activity model.
- Produces an executive summary, recent progress, blockers, decisions, risks, carryover, suggested agenda, suggested standup questions, and source references.
- Writes facilitator review metadata into generated markdown and JSON output.
- Supports local review decisions with `draft`, `approved`, and `rejected` statuses.
- Optionally writes a structured JSON version of the same pre-read content.
- Optionally writes a separate approved markdown copy when a facilitator marks the draft as approved.

### Supported Inputs

The MVP supports local sample inputs only:

- Sample issue JSON, defaulting to `examples/jira-sample.json`.
- Sample pull request JSON, defaulting to `examples/github-pr-sample.json`.
- Prior standup markdown, defaulting to `examples/prior-standup.md`.
- Optional sample Slack/Teams-style chat JSON via `--chat-path`, such as `examples/chat-rich-sample.json`.

The only supported source mode is `sample`.

### Supported Outputs

- Markdown standup pre-read drafts, defaulting to `output/standup-pre-read.md`.
- Optional structured JSON output via `--json-output-path`.
- Optional approved markdown copy via `--approved-output-path` when `--review-status approved` is set.

### Facilitator Review Workflow

Generated pre-reads start as local facilitator-review drafts. A facilitator can:

1. Generate a draft markdown pre-read and optional JSON output.
2. Review the generated sections and source references locally.
3. Re-run the CLI with `--review-status approved` or `--review-status rejected`.
4. Include `--reviewer` and `--review-notes` to record local review context.
5. Provide `--approved-output-path` to write a separate approved markdown copy only for approved pre-reads.

Rejected pre-reads keep review metadata in normal markdown and JSON outputs but do not write an approved copy.

### Intentionally Out of Scope

This MVP intentionally does not include:

- Live Jira API or Jira MCP integrations.
- Live GitHub API integrations.
- Slack, Teams, email, or notification delivery.
- Backstage, Harness, EKS, or cloud deployment automation.
- Authentication, authorization, or secret management for external systems.
- Persistent storage beyond local markdown and JSON files.
- Work-specific project names, URLs, keys, repositories, or team data.

### Run the Standard Demo

```bash
make demo
```

Equivalent direct command:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli \
  --source-mode sample \
  --output-path output/standup-pre-read.md
```

### Run the Rich Chat Demo

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

### Run the Approved Review Demo

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli \
  --source-mode sample \
  --output-path output/reviewed-pre-read.md \
  --json-output-path output/reviewed-pre-read.json \
  --review-status approved \
  --reviewer "Facilitator" \
  --review-notes "Ready to share." \
  --approved-output-path output/approved-pre-read.md
```

### Run Quality Checks

```bash
make check
```

`make check` runs the unit test suite, Ruff linting, and mypy type checking.
