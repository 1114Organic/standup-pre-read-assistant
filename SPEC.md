# AI-Powered Standup Pre-Read Assistant Spec

## 1. Product Objective

Build an AI-powered assistant that prepares a daily standup pre-read by gathering team activity from trusted work systems, summarizing meaningful progress, identifying blockers, carrying forward unresolved items, and recommending the topics that deserve discussion during standup.

The goal is not to create another status report. The goal is to help the team spend less time reciting updates and more time resolving blockers, making decisions, and improving delivery flow.

## 2. Primary Users

The primary users are scrum masters, RTEs, product owners, engineering leads, and team members.

A facilitator uses the pre-read before the meeting to understand what changed. Team members use it to arrive aligned. Leaders use it to spot delivery risk, aging blockers, and decisions that need escalation.

## 3. Core Problem

Daily standups often degrade into repetitive status updates. Important signals are spread across Jira, GitHub, CI/CD systems, team communication channels, and previous meeting notes. The facilitator spends time manually gathering context, and the team can miss blockers, risks, or decisions hiding in the workstream.

This assistant solves that by preparing a concise, evidence-backed standup brief before the meeting begins.

## 4. MVP Scope

The MVP shall use sample data first, then be extended to live APIs.

The first working version shall:

- Read sample Jira issue data.
- Read sample GitHub pull request data.
- Read a prior standup markdown file.
- Normalize those inputs into a shared activity model.
- Generate a dated standup pre-read markdown draft.
- Include source references for every important claim.
- Include tests for the required output structure.

The first working version shall not call live Jira, GitHub, Teams, Slack, Harness, or observability APIs.

## 5. Future Runtime Target

Prototype: local dry run using sample data.

Pilot: scheduled container job.

Production: EKS CronJob or small EKS-hosted internal service with team-level configuration, secrets management, logs, metrics, and optional Backstage integration.

## 6. Data Sources

MVP sample inputs:

- `examples/jira-sample.json`
- `examples/github-pr-sample.json`
- `examples/prior-standup.md`

Future live inputs:

- Jira issues updated during the lookback window.
- GitHub pull requests opened, merged, reviewed, blocked, or stale.
- Prior standup notes.
- Optional Teams or Slack channel messages from approved channels.
- Optional Harness build and deployment status.

## 7. Pre-Read Output

The assistant shall generate a dated pre-read with these sections:

- Executive Summary
- Progress Since Last Standup
- Blockers Needing Action
- Decisions Needed
- Risks and Aging Work
- Carryover From Yesterday
- Suggested Standup Agenda
- Source References

## 8. AI and Summarization Rules

The assistant must not invent status. If the source data is unclear, it should say the item needs confirmation.

The assistant must distinguish between activity and progress. A comment, commit, or message is not automatically meaningful progress.

The assistant must cite or link back to source records for important claims.

The assistant must avoid assigning blame or making subjective judgments about individual performance.

The assistant must use neutral language suitable for team collaboration.

The assistant must flag uncertainty when confidence is low.

## 9. Acceptance Criteria

A pre-read is generated from the sample files.

The pre-read includes all required sections.

Every major summary item includes a source reference.

Unresolved blockers from the prior standup are carried forward.

Resolved carryover items are not repeated as active blockers.

Stale pull requests are flagged based on a configurable threshold.

The assistant does not claim work is complete unless the source data supports completion.

The generated output is deterministic enough for automated structure tests.

## 10. Out of Scope for the Thin-Slice MVP

- Live Jira API integration.
- Live GitHub API integration.
- Teams or Slack notification.
- Harness build and deployment integration.
- Automatic Jira updates.
- Leadership dashboard rollups.
- Individual performance scoring.
- Backstage plugin UI.
- EKS deployment manifests.

## 11. Success Metrics

- Generated pre-read contains all required sections.
- Summary items trace back to source data.
- Carryover items are handled correctly.
- Risks and blockers are separated from normal progress.
- The output is useful enough for a facilitator to review and edit.

## 12. Build Instructions for Codex

Build the thin-slice MVP first:

1. Read the three sample input files in `/examples`.
2. Create a normalized activity model.
3. Generate a markdown pre-read matching the structure of `/examples/expected-pre-read.md`.
4. Write the output to a local file.
5. Add tests that validate the output contains the required sections and expected key items.
6. Keep the design easy to extend to live APIs later.

