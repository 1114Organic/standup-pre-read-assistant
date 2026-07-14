# Standup Pre-Read Assistant

AI-powered assistant that generates a daily standup pre-read from Jira, GitHub, optional sample chat messages, and prior standup notes. Inspired from Ryan Nystrom's interview here - https://www.chatprd.ai/how-i-ai/ryan-nystrom-notion-workflows-for-engineering-velocity

For a snapshot of the current MVP state and planned milestones, see [PROJECT_STATUS.md](PROJECT_STATUS.md). The integration path is tracked in [ROADMAP.md](ROADMAP.md). Connector payload expectations for current local adapters and future live connectors are documented in [docs/CONNECTOR_CONTRACT.md](docs/CONNECTOR_CONTRACT.md).

The first build target is a thin-slice MVP: 

1. Read sample Jira JSON.
2. Read sample GitHub pull request JSON.
3. Read prior standup notes.
4. Optionally read local sample Slack/Teams-style chat messages.
5. Generate a markdown standup pre-read, including concise suggested standup questions.
6. Save the draft locally with review metadata so generated pre-reads start as facilitator-review drafts.
7. Add tests that verify the output structure.

Live APIs, Teams notifications, Harness, and EKS deployment are intentionally deferred until the generated pre-read quality is proven with sample data. The `jira_mcp_sample` mode is also local-only: it reads a checked-in mock Jira MCP-style response and does not contact a real Jira MCP server. The `jira_mcp` mode is recognized for connector readiness, but it is disabled at runtime unless a future approved MCP environment supplies the real adapter and server configuration.

## v0.4.0 Draft: Real Connector Readiness

The v0.4.0 draft prepares for future live connectors without adding any live integrations. The new [connector contract](docs/CONNECTOR_CONTRACT.md) documents `SourceData` expectations, required and optional source fields, source references, timestamp and confidence guidance, error handling, security/no-secrets rules, and examples for future Jira MCP, GitHub API, and Slack/Teams connectors. Local `sample` and `jira_mcp_sample` connector outputs are now validated with lightweight contract checks before normalization so malformed source payloads fail with clear field-path errors while preserving existing sample, rich sample, chat sample, markdown, JSON, priority scoring, facilitator review, and evaluation workflows.

## v0.3.0 Draft: Local GitHub PR Intelligence

The v0.3.0 draft expands local/sample pull request intelligence without adding live GitHub API integration. The generic GitHub fixtures now cover review requested, changes requested, approved, merged, failing CI, stale open PRs, blocked PRs, PRs with no linked issue, unclear owner, and decision-dependent PRs. Normalization preserves PR metadata such as review state, CI state, merge state, reviewers, approvals, requested changes, draft status, owner/author, linked issues, timestamps, and source references.

Generated pre-reads now place merged PRs in progress, failing CI/stale/blocked PRs in risks, decision-dependent PRs in decisions/questions, waiting-on-review PRs in the suggested agenda/questions, and missing linked issue PRs in questions. JSON output includes useful `pr_metadata` on PR-derived items so downstream evaluators can inspect the same signals. The evaluation harness validates these local PR signals while preserving sample, `jira_mcp_sample`, rich sample, chat sample, markdown, JSON, priority scoring, facilitator review, and CI-compatible workflows.

## v0.2.0 Evaluation Harness and v0.1.0 MVP Demo

The v0.2.0 evaluation workflow is the current release checkpoint. It adds `make evaluate`, which runs `default_sample`, `rich_sample`, `rich_chat_sample`, and `jira_mcp_sample`, then writes `output/evaluation-report.md` plus `output/evaluation-report.json`. The v0.1.0 MVP remains the local sample-mode demo baseline. It generates markdown and optional JSON standup pre-reads from repository sample issue, pull request, prior standup, and optional chat files; generated output starts as a facilitator-review draft and can be locally approved or rejected. Live Jira, Jira MCP, GitHub API, Slack, Teams, Backstage, EKS, and work-specific data are intentionally out of scope for this checkpoint. See [RELEASE_NOTES.md](RELEASE_NOTES.md) for the full v0.2.0 and v0.1.0 summaries.

Run the standard demo:

```bash
make demo
```

Run the rich chat demo with markdown and JSON output:

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

Run the local mock Jira MCP sample demo with markdown and JSON output:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli \
  --source-mode jira_mcp_sample \
  --jira-mcp-path examples/jira-mcp-sample-response.json \
  --output-path output/jira-mcp-standup-pre-read.md \
  --json-output-path output/jira-mcp-standup-pre-read.json
```

## Local Usage

Create an isolated development environment and install the project with its test/lint tooling:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Run the sample-mode generator from a local checkout with:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli
# or, after installation:
standup-pre-read
```

The CLI defaults to `--source-mode sample` and writes `output/standup-pre-read.md`. You can make those defaults explicit or choose a different output file:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli --source-mode sample --output-path output/custom-pre-read.md
# or, after installation:
standup-pre-read --source-mode sample --output-path output/custom-pre-read.md
```

The default configuration reads the issue, pull request, and prior-standup sample files in `examples/`. Use `--source-mode jira_mcp_sample --jira-mcp-path examples/jira-mcp-sample-response.json` to replace the direct sample Jira issue file with a local mock Jira MCP-style tool response while still optionally using local GitHub, prior standup, and chat sample paths. Add `--chat-path examples/chat-rich-sample.json` to include local sample Slack/Teams-style messages; chat messages are normalized into the same activity model and can contribute blockers, decisions, carryover/follow-ups, standup questions, and source references. The generated markdown includes a `Suggested Standup Questions` section that derives facilitator questions from the same normalized activity data as the pre-read, covering blockers, risky pull requests, decisions, carryover, and detectable ownership/status gaps. `jira_mcp_sample` and `jira_mcp` are intentionally different paths. `jira_mcp_sample` is the local CI/test path: it reads checked-in mock MCP-shaped JSON, requires no credentials or MCP server, and performs no network calls. `jira_mcp` is the real-connector application boundary: it requires an approved work environment, an externally configured MCP server, and credentials supplied outside this repository. In this repo/runtime, `jira_mcp` fails clearly before attempting credentials, network calls, or Jira requests.

To write a machine-readable JSON version alongside the markdown, pass `--json-output-path`:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli \
  --source-mode sample \
  --output-path output/standup-pre-read.md \
  --json-output-path output/standup-pre-read.json
```

The JSON output is generated from the same structured pre-read document as markdown, so enabling it does not change the markdown draft. It includes metadata (`generated_at`, `team_name` when configured, `source_mode`, `review_status`, optional `reviewed_at`, optional `reviewer`, optional `review_notes`, and a `data_window` when source timestamps are available), `executive_summary`, `progress`, `blockers`, `decisions`, `risks`, `carryover`, `suggested_agenda`, `suggested_questions`, and `source_references`. Each structured list item includes `text` and `source_refs`, plus `priority`, `confidence`, and `related_work_items` when those values are available; markdown sections keep their existing format while using priority to put high-signal topics first.

To run the richer demo-data scenario, point the same sample-mode CLI at the alternate example files:

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

The rich scenario remains generic demo data. It includes completed work, in-progress work, a blocker, a decision, stale/risky pull request signals, unresolved carryover, local chat blockers/decisions/follow-ups, and an item with unclear ownership/status so reviewers can evaluate the generated standup questions without relying on the default `DEMO-*` sample IDs.


## Integration Configuration

`config/example-team.yaml` is a sanitized, easy-to-edit starting point for future team-level integration settings. It includes generic placeholders for team metadata, Jira, GitHub, chat, output paths, facilitator review defaults, posting preferences, and security switches. It intentionally contains no real tokens, URLs, project keys, channel names, organization names, or work-specific data.

You can use it with local sample mode today:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli --config config/example-team.yaml
```

Explicit CLI flags override values loaded from the YAML config, for example:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli \
  --config config/example-team.yaml \
  --output-path output/custom-pre-read.md
```

The config file prepares the shape for Jira MCP, GitHub API, and Slack/Teams integrations. The real `jira_mcp` source mode is recognized but remains unavailable in this local repository runtime until tested in an approved work environment.
Example placeholder-only Jira MCP config values:

```yaml
sources:
  jira:
    enabled: true
    mode: jira_mcp
    mcp_server_name: placeholder-jira-mcp-server
    jql: project in (EXAMPLE) AND updated >= -1d
    project_keys:
      - EXAMPLE
    include_comments: false
    max_results: 50
```

Do not put credentials, tokens, real Jira URLs, or work-specific project keys in this file. `sources.jira.enabled: false` explicitly disables real Jira MCP execution, and the local runtime still fails safely even when `enabled` is true because no approved MCP adapter is wired here.
 Current supported runtime modes are still local-only sample adapters; real Jira MCP network calls, GitHub API calls, Slack calls, Teams calls, credentials, posting, and deployment code are intentionally not included. See [ROADMAP.md](ROADMAP.md) for the planned milestone sequence and [docs/CONNECTOR_CONTRACT.md](docs/CONNECTOR_CONTRACT.md) for connector payload expectations.

## Facilitator Review Mode

Generated pre-reads are local drafts by default. Markdown includes a small `Review Metadata` section near the top, and JSON includes `review_status` with the default value `draft`. A facilitator can stamp a local review decision without adding any web UI or external integrations:

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

Allowed review statuses are `draft`, `approved`, and `rejected`. When `--review-status approved` and `--approved-output-path` are both provided, the CLI also writes the approved markdown copy to that path. Rejected pre-reads keep the review metadata in the normal markdown and JSON outputs, but never write an approved output file.

## Makefile Commands

Use these convenience targets for the local workflow. The Makefile defaults to `python3`; use an override such as `PYTHON=python make demo` if your environment needs a different interpreter.

```bash
make test       # runs python3 -m pytest by default
make lint       # runs python3 -m ruff check . by default
make typecheck  # runs python3 -m mypy by default
make demo       # runs the sample CLI and writes output/standup-pre-read.md
make evaluate   # runs all four sample evaluation scenarios and writes output/evaluation-report.md/json
make check      # runs test, lint, and typecheck
```

## Quality Checks

Before opening a pull request, run the same local checks used by contributors. For v0.2.0 sample-quality review, also run `make evaluate`; it covers the default sample, rich sample, rich chat sample, and local `jira_mcp_sample` scenario, verifies markdown and JSON outputs, required sections, blockers, decisions, carryover behavior, source references, JSON priorities, and JSON `review_status`.

```bash
make check
```

The equivalent direct commands are:

```bash
python3 -m pytest
python3 -m ruff check .
python3 -m mypy
```

## Repository Structure

```text
.
├── SPEC.md
├── README.md
├── specs
│   ├── requirements.md
│   ├── design.md
│   └── tasks.md
├── examples
│   ├── jira-sample.json
│   ├── jira-mcp-sample-response.json
│   ├── github-pr-sample.json
│   ├── prior-standup.md
│   ├── jira-rich-sample.json
│   ├── github-pr-rich-sample.json
│   ├── prior-standup-rich.md
│   ├── chat-rich-sample.json
│   └── expected-pre-read.md
├── src
└── tests
```

## Codex Starter Prompt

```text
Read SPEC.md and the files in /examples. Build the thin-slice MVP first:

- read examples/jira-sample.json
- read examples/github-pr-sample.json
- read examples/prior-standup.md
- generate a standup pre-read markdown file matching examples/expected-pre-read.md
- do not call live APIs yet
- add tests for the generated output structure
- keep the implementation simple and easy to extend
```
