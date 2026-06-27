# Standup Pre-Read Assistant

AI-powered assistant that generates a daily standup pre-read from Jira, GitHub, and prior standup notes. Inspired from Ryan Nystrom's interview here - https://www.chatprd.ai/how-i-ai/ryan-nystrom-notion-workflows-for-engineering-velocity

For a snapshot of the current MVP state and planned milestones, see [PROJECT_STATUS.md](PROJECT_STATUS.md).

The first build target is a thin-slice MVP: 

1. Read sample Jira JSON.
2. Read sample GitHub pull request JSON.
3. Read prior standup notes.
4. Generate a markdown standup pre-read.
5. Save the draft locally.
6. Add tests that verify the output structure.

Live APIs, Teams notifications, Harness, and EKS deployment are intentionally deferred until the generated pre-read quality is proven with sample data.

## Local Usage

Create an isolated development environment and install the project with its test/lint tooling:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run the sample-mode generator from a local checkout with:

```bash
PYTHONPATH=src python -m standup_pre_read.cli
# or, after installation:
standup-pre-read
```

The CLI defaults to `--source-mode sample` and writes `output/standup-pre-read.md`. You can make those defaults explicit or choose a different output file:

```bash
PYTHONPATH=src python -m standup_pre_read.cli --source-mode sample --output-path output/custom-pre-read.md
# or, after installation:
standup-pre-read --source-mode sample --output-path output/custom-pre-read.md
```

The default configuration reads the sample files in `examples/`. Live Jira, Jira MCP, GitHub API, and messaging connectors are intentionally out of scope for this thin-slice MVP; unsupported source modes fail with a CLI error.

## Makefile Commands

Use these convenience targets for the local workflow:

```bash
make test       # runs python -m pytest
make lint       # runs python -m ruff check .
make typecheck  # runs python -m mypy
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
python -m pytest
python -m ruff check .
python -m mypy
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
