# Codex Build Prompt

Read `SPEC.md`, the files in `specs/`, and the files in `examples/`.

Build the thin-slice MVP first:

- Read `examples/jira-sample.json`.
- Read `examples/github-pr-sample.json`.
- Read `examples/prior-standup.md`.
- Generate a standup pre-read markdown file matching the structure of `examples/expected-pre-read.md`.
- Do not call live APIs yet.
- Add tests for the generated output structure.
- Keep the implementation simple and easy to extend.

Implementation priorities:

1. Create a normalized activity model.
2. Implement sample file collectors.
3. Generate all required pre-read sections.
4. Include source references for key claims.
5. Carry forward unresolved prior standup items.
6. Flag stale or risky pull requests.
7. Write the generated pre-read to a local output file.
8. Add tests that verify the output contains required sections and expected key items.

Do not implement Teams, Slack, Harness, Jira API, GitHub API, Backstage, or EKS deployment in the first pass.

