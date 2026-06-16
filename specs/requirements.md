# Requirements

## Product Name

AI-Powered Standup Pre-Read Assistant

## Product Objective

Create a daily pre-read that helps teams enter standup already aligned on progress, blockers, risks, and decisions needed. The assistant should reduce manual preparation time and shift standups away from status reporting toward meaningful coordination.

## Primary Users

The primary users are scrum masters, RTEs, product owners, engineering leads, and team members.

## Core User Stories

As a scrum master, I want a daily pre-read generated before standup so I can facilitate a focused conversation without manually collecting updates.

As an RTE or delivery lead, I want blockers and risks surfaced across teams so I can help remove impediments before they become delivery issues.

As a product owner, I want to see progress tied to sprint work so I understand whether the team is moving toward the sprint goal.

As a team member, I want relevant updates summarized before standup so I do not need to repeat information already visible in Jira or GitHub.

As a facilitator, I want to review and edit the pre-read before it is posted so I can correct context before the team sees it.

## MVP Functional Requirements

The assistant shall read sample Jira issue updates from `examples/jira-sample.json`.

The assistant shall read sample GitHub pull request activity from `examples/github-pr-sample.json`.

The assistant shall ingest prior standup notes from `examples/prior-standup.md`.

The assistant shall generate a pre-read with these sections: executive summary, progress since last standup, blockers needing action, decisions needed, risks and aging work, carryover from yesterday, suggested agenda, and source references.

The assistant shall include source references for Jira issues, GitHub pull requests, and prior carryover items.

The assistant shall flag uncertainty when a status cannot be confirmed from source data.

The assistant shall write the generated pre-read to a local markdown file.

## Acceptance Criteria

A pre-read is generated from sample files.

The pre-read includes all required sections.

Every major summary item includes a source reference.

Unresolved blockers from the prior standup are carried forward.

Resolved carryover items are not repeated as active blockers.

Stale pull requests are flagged based on a configurable threshold.

The assistant does not claim work is complete unless Jira or GitHub data confirms completion.

Automated tests verify the generated output structure.

## Out of Scope for MVP

Teams or Slack message analysis.

Harness build and deployment integration.

Live Jira or GitHub API calls.

Automatic Jira updates.

Leadership dashboard rollups.

Individual performance scoring.

Backstage plugin UI.

Multi-team enterprise configuration.

