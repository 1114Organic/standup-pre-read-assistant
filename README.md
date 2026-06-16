# Standup Pre-Read Assistant

AI-powered assistant that generates a daily standup pre-read from Jira, GitHub, and prior standup notes.

The first build target is a thin-slice MVP:

1. Read sample Jira JSON.
2. Read sample GitHub pull request JSON.
3. Read prior standup notes.
4. Generate a markdown standup pre-read.
5. Save the draft locally.
6. Add tests that verify the output structure.

Live APIs, Teams notifications, Harness, and EKS deployment are intentionally deferred until the generated pre-read quality is proven with sample data.

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

