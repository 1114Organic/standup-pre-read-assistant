# Connector Contract

This project is still local-only. The connector contract defines the shape that any current sample adapter or future live connector must return before normalization and pre-read generation. It is intentionally lightweight so connector work can be validated without adding live integrations, credentials, deployment, or environment-specific configuration.

## Purpose of Source Connectors

Source connectors collect raw activity from an approved source and return a `SourceData` payload. A connector should only load and adapt source data; it should not summarize, score priorities, decide standup sections, or write output files. Normalization and generation remain shared application responsibilities.

Current executable connectors are local fixtures only. A `jira_mcp` adapter boundary also exists, but it raises a runtime-unavailable error in this repository unless a future approved MCP runtime implementation is supplied:

- `sample` reads checked-in Jira-style issue JSON, GitHub PR JSON, prior standup markdown, and optional chat JSON.
- `jira_mcp_sample` reads a checked-in mock Jira MCP-style JSON response and adapts it to the same local Jira sample shape.
- `jira_mcp` is the real Jira MCP mode name; in this repo it does not call MCP, Jira, the network, or credentials and fails with clear guidance to use an approved runtime.

## `SourceData` Expectations

A connector returns one `SourceData` object with these fields:

| Field | Required | Expected shape | Notes |
| --- | --- | --- | --- |
| `jira_data` | Yes | Dictionary with a non-empty `issues` list | Issues must be adapted into the local Jira sample shape before normalization. |
| `github_data` | Yes | Dictionary with a `repositories` list | The list may be empty for connectors that do not provide PR data, but each repository must include `name` and `pull_requests`. |
| `prior_markdown` | Yes | String | Prior standup notes may be empty, but must be a string. |
| `chat_data` | Yes | Dictionary with a `channels` list | Use `{"channels": []}` when chat is not configured. |
| `source_health` | Yes | List of source health records | Records include source name, `ok`/`failed`/`skipped` status, required flag, and a concise message. |

## Required, Optional, and Disabled Sources

Current local Jira, GitHub, and prior-standup sources are required for sample generation. If one of those required sources cannot be loaded, the run fails clearly with the source name and does not write a partial pre-read.

Chat is optional. If optional chat is disabled, connectors return `{"channels": []}` and report the source as `skipped` in source health. If optional chat is configured but fails to load, the run continues with empty chat data and reports chat as `failed` in source health.

Future live sources should follow the same pattern: required source failures stop the run with a concise connector error, optional source failures are isolated and visible in source health, and disabled sources are reported as `skipped` rather than silently disappearing.

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

Required connector load failures should raise a clear source-specific error. Optional connector load failures should be captured in `source_health`, use a safe empty fallback payload, and allow the run to complete so facilitators can see which non-required source was unavailable.

## Security and No-Secrets Guidance

Do not commit credentials, tokens, workspace URLs, private project keys, channel names, customer data, or environment-specific configuration. Local examples must stay generic and sanitized. Live connectors should receive credentials only through an approved secrets mechanism in a future milestone; this repository should not contain those secrets.

Connector logs and errors should avoid dumping full raw payloads if they could contain sensitive content. Prefer concise field-path errors.

## Local-only Versus Live Connectors

Local-only connectors read checked-in sample files and perform no network calls. They are safe for CI and deterministic evaluation.

Live connectors require approved runtime configuration. The `jira_mcp` mode is recognized now but intentionally fails in this local runtime before any credential lookup, network call, or Jira request. The generic config switch `security.allow_live_connectors` defaults to `false` so live connector paths are disabled by default even before connector-specific checks run. A future work-environment implementation may call an approved MCP server only after configuration, authentication, security review, and operational behavior are supplied outside this repository.

## Future Connector Examples

### Real Jira MCP connector

The real Jira MCP connector boundary must require `security.allow_live_connectors: true`, call an approved Jira MCP server name from `sources.jira.mcp_server_name`, use `sources.jira.jql` or `sources.jira.project_keys`, honor `sources.jira.include_comments` and `sources.jira.max_results`, adapt issue results to `jira_data.issues`, preserve issue keys and URLs, and pass `validate_source_data` before normalization. Credentials must be supplied by the approved MCP runtime, not code or checked-in config. The current local implementation raises `JiraMcpRuntimeUnavailableError` instead of executing.

### GitHub API connector

A future GitHub API connector would fetch pull requests from approved repositories, adapt them into `github_data.repositories[*].pull_requests`, preserve PR numbers, URLs, review/CI/merge metadata where available, and avoid storing GitHub tokens in the repository.

### Slack or Teams connector

A future messaging connector would read approved channels only, adapt relevant messages into `chat_data.channels[*].messages`, preserve message IDs and links, and avoid broad workspace scraping. Channel names and workspace identifiers in checked-in examples must remain generic.
