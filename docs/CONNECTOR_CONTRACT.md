# Connector Contract

This project is still local-only. The connector contract defines the shape that any current sample adapter or future live connector must return before normalization and pre-read generation. It is intentionally lightweight so connector work can be validated without adding live integrations, credentials, deployment, or environment-specific configuration.

## Purpose of Source Connectors

Source connectors collect raw activity from an approved source and return a `SourceData` payload. A connector should only load and adapt source data; it should not summarize, score priorities, decide standup sections, or write output files. Normalization and generation remain shared application responsibilities.

Current connectors are local fixtures only:

- `sample` reads checked-in Jira-style issue JSON, GitHub PR JSON, prior standup markdown, and optional chat JSON.
- `jira_mcp_sample` reads a checked-in mock Jira MCP-style JSON response and adapts it to the same local Jira sample shape.

## `SourceData` Expectations

A connector returns one `SourceData` object with these fields:

| Field | Required | Expected shape | Notes |
| --- | --- | --- | --- |
| `jira_data` | Yes | Dictionary with a non-empty `issues` list | Issues must be adapted into the local Jira sample shape before normalization. |
| `github_data` | Yes | Dictionary with a `repositories` list | The list may be empty for connectors that do not provide PR data, but each repository must include `name` and `pull_requests`. |
| `prior_markdown` | Yes | String | Prior standup notes may be empty, but must be a string. |
| `chat_data` | Yes | Dictionary with a `channels` list | Use `{"channels": []}` when chat is not configured. |

## Required Fields

### Jira-style issue records

Each item in `jira_data.issues` must include:

- `key`: non-empty work item identifier.
- `status`: non-empty source status.

The normalizer also expects these optional-but-useful fields when available: `title`, `summary`, `assignee`, `updated`, `sprint`, `url`, `blocker`, `blocked_reason`, and `decision_needed`.

### GitHub-style PR records

Each repository in `github_data.repositories` must include:

- `name`: non-empty repository display name.
- `pull_requests`: list of PR records.

Each PR record must include:

- `number`: PR number or stable source number.
- `title`: non-empty title.
- `state`: non-empty source state such as `open` or `closed`.

### Chat message records

Each channel in `chat_data.channels` may include a `messages` list. Each message must include:

- `id`: non-empty stable message identifier.
- `text`: non-empty message body.

## Optional Fields

Connectors should preserve optional fields that increase evidence quality without inventing values:

- Source URLs: `url` or source-specific links.
- Owners/authors: `assignee`, `author`, or message `author`.
- Relationships: `linked_issues`, `related_work_items`.
- PR metadata: `review_state`, `ci_state`, `merge_state`, `reviewers`, `approvals`, `requested_changes`, `draft`, `stale_days`, `age_days`, `blocked_reason`, `decision_needed`.
- Team/project context: `team`, repository `name`, `sprint`, channel `name`, workspace name.

## Source Reference Expectations

Every important generated claim should trace back to a source reference after normalization. Connectors should provide stable, human-recognizable identifiers:

- Jira issues use the issue `key`.
- Pull requests use `PR #<number>` after normalization.
- Chat messages use message `id` and should include `url` when available.
- Prior standup items should include a referenced work item if present in the note.

Future live connectors must not replace stable source identifiers with transient database IDs when a user-facing key is available.

## Timestamp Expectations

Timestamp fields are optional unless the source has them, but when supplied they must be ISO-8601 strings. Accepted examples include offsets such as `2026-06-16T09:15:00+00:00` and UTC `Z` suffixes such as `2026-06-16T09:15:00Z`.

Connectors should preserve source timestamps instead of converting them to local time. The shared normalizer handles parsing and downstream data-window calculation.

## Confidence Expectations

Connectors should not inflate confidence. Current normalized confidence defaults are:

- `high` for structured Jira and GitHub records.
- `medium` for prior standup and chat-derived signals.

Future connectors may provide richer evidence, but confidence should reflect source quality and ambiguity. When a source is unclear, preserve the uncertainty so the generated pre-read can ask for confirmation.

## Error Handling Expectations

Connectors should fail fast with clear errors when required payload shape is missing or invalid. The shared `validate_source_data` helper checks the current lightweight contract and raises `ConnectorContractError` with field paths such as `jira_data.issues[0].key`.

A connector should not silently drop malformed required records if that would hide source coverage problems. Optional fields can be omitted when unavailable.

## Security and No-Secrets Guidance

Do not commit credentials, tokens, workspace URLs, private project keys, channel names, customer data, or environment-specific configuration. Local examples must stay generic and sanitized. Live connectors should receive credentials only through an approved secrets mechanism in a future milestone; this repository should not contain those secrets.

Connector logs and errors should avoid dumping full raw payloads if they could contain sensitive content. Prefer concise field-path errors.

## Local-only Versus Live Connectors

Local-only connectors read checked-in sample files and perform no network calls. They are safe for CI and deterministic evaluation.

Live connectors are future work. A live connector may call an approved API or MCP server only after a later milestone defines configuration, authentication, security review, and operational behavior. Until then, unsupported source modes must continue to fail clearly.

## Future Connector Examples

### Real Jira MCP connector

A future real Jira MCP connector would call an approved Jira MCP server, adapt issue results to `jira_data.issues`, preserve issue keys and URLs, and pass `validate_source_data` before normalization. It must not be added as part of the local sample milestone.

### GitHub API connector

A future GitHub API connector would fetch pull requests from approved repositories, adapt them into `github_data.repositories[*].pull_requests`, preserve PR numbers, URLs, review/CI/merge metadata where available, and avoid storing GitHub tokens in the repository.

### Slack or Teams connector

A future messaging connector would read approved channels only, adapt relevant messages into `chat_data.channels[*].messages`, preserve message IDs and links, and avoid broad workspace scraping. Channel names and workspace identifiers in checked-in examples must remain generic.
