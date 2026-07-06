# Standup Pre-Read Assistant

AI-powered assistant that generates a daily standup pre-read from Jira, GitHub, optional sample chat messages, and prior standup notes. Inspired from Ryan Nystrom's interview here - https://www.chatprd.ai/how-i-ai/ryan-nystrom-notion-workflows-for-engineering-velocity

For a snapshot of the current MVP state and planned milestones, see [PROJECT_STATUS.md](PROJECT_STATUS.md).

The first build target is a thin-slice MVP: 

1. Read sample Jira JSON.
2. Read sample GitHub pull request JSON.
3. Read prior standup notes.
4. Optionally read local sample Slack/Teams-style chat messages.
5. Generate a markdown standup pre-read, including concise suggested standup questions.
6. Save the draft locally.
7. Add tests that verify the output structure.

Live APIs, Teams notifications, Harness, and EKS deployment are intentionally deferred until the generated pre-read quality is proven with sample data.

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

The default configuration reads the issue, pull request, and prior-standup sample files in `examples/`. Add `--chat-path examples/chat-rich-sample.json` to include local sample Slack/Teams-style messages; chat messages are normalized into the same activity model and can contribute blockers, decisions, carryover/follow-ups, standup questions, and source references. The generated markdown includes a `Suggested Standup Questions` section that derives facilitator questions from the same normalized activity data as the pre-read, covering blockers, risky pull requests, decisions, carryover, and detectable ownership/status gaps. Live Jira, Jira MCP, GitHub API, and live messaging connectors are intentionally out of scope for this thin-slice MVP; unsupported source modes fail with a CLI error.

To write a machine-readable JSON version alongside the markdown, pass `--json-output-path`:

```bash
PYTHONPATH=src python3 -m standup_pre_read.cli \
  --source-mode sample \
  --output-path output/standup-pre-read.md \
  --json-output-path output/standup-pre-read.json
```

The JSON output is generated from the same structured pre-read document as markdown, so enabling it does not change the markdown draft. It includes metadata (`generated_at`, `team_name` when configured, `source_mode`, and a `data_window` when source timestamps are available), `executive_summary`, `progress`, `blockers`, `decisions`, `risks`, `carryover`, `suggested_agenda`, `suggested_questions`, and `source_references`. Each structured list item includes `text` and `source_refs`, plus `priority`, `confidence`, and `related_work_items` when those values are available; markdown sections keep their existing format while using priority to put high-signal topics first.

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

## Makefile Commands

Use these convenience targets for the local workflow. The Makefile defaults to `python3`; use an override such as `PYTHON=python make demo` if your environment needs a different interpreter.

```bash
make test       # runs python3 -m pytest by default
make lint       # runs python3 -m ruff check . by default
make typecheck  # runs python3 -m mypy by default
make demo       # runs the sample CLI and writes output/standup-pre-read.md
make check      # runs test, lint, and typecheck
```

## Quality Checks

Before opening a pull request, run the same local checks used by contributors:

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
