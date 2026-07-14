# Integration Roadmap

This roadmap shows the intended path from local sample MVP to a one-team pilot. It complements, but does not duplicate, the connector payload rules in [docs/CONNECTOR_CONTRACT.md](docs/CONNECTOR_CONTRACT.md).

## Completed and Current Foundation

| Milestone | Status | Focus |
| --- | --- | --- |
| v0.1.0 Local MVP | Completed | Generate local markdown and optional JSON pre-reads from generic sample Jira, GitHub, and prior-standup data. |
| v0.2.0 Evaluation Harness | Completed | Add repeatable local evaluation scenarios and reports. |
| v0.3.0 GitHub PR Intelligence | Completed | Improve local/sample PR signals for review, CI, stale, blocked, merged, and decision-dependent pull requests. |
| v0.4.0 Connector Contract and Validation | Completed | Define and validate the source connector boundary without live calls. |
| v0.5.0 Integration Config Foundation | Completed | Add editable team-level integration configuration while keeping live connectors disabled. |
| v0.6.0 Real Jira MCP Connector Readiness | Completed | Add the `jira_mcp` mode and safe adapter boundary; real execution awaits approved work-environment MCP testing. |
| v0.7.0 Connector Resilience and Source Health | Draft | Define source health, degraded-source handling, and connector resilience expectations before live pilot integrations. |

## Completed Milestone Details

### v0.5.0 Integration Config Foundation

- **Objective:** Provide a sanitized, easy-to-edit team configuration file and CLI loading path for future live integrations.
- **Expected inputs:** Generic YAML configuration with team metadata, source settings, output paths, review defaults, posting preferences, and security switches.
- **Expected outputs:** Local sample generation can be driven by `--config`, with explicit CLI flags taking precedence where supported.
- **Success criteria:** The example config contains no secrets or work-specific identifiers, loads in tests, preserves sample-mode behavior, and documents live connectors as future work.
- **Out of scope:** Real Jira MCP calls, GitHub API calls, Slack or Teams calls, secrets management, deployment, and automated posting.

### v0.6.0 Real Jira MCP Connector Readiness

- **Objective:** Add the application-side source mode and adapter boundary for the first approved live issue connector by reading Jira issues through a configured MCP server in an approved environment.
- **Expected inputs:** Team config selecting Jira MCP mode, approved JQL or project filters, read-only credentials supplied by an external secrets mechanism, and a configured MCP server name.
- **Expected outputs:** Jira issue activity adapted to the existing connector contract and normalized into standup progress, blockers, decisions, risks, and source references.
- **Success criteria:** `jira_mcp` is recognized, live connector paths are disabled by default through `security.allow_live_connectors`, unavailable local execution fails clearly without credentials or network calls, live Jira MCP output passes connector validation when later tested in the approved work environment, sample mode remains deterministic, no credentials are committed, and failures produce clear field-path or connector errors.
- **Out of scope:** Jira writes, workflow transitions, broad unfiltered queries, deployment automation, and GitHub or messaging live connectors.

## Upcoming Milestones

### v0.7.0 Connector Resilience and Source Health

- **Objective:** Define the health and resilience behavior future live connectors must expose before a one-team pilot depends on them.
- **Expected inputs:** Connector health state, source availability checks, non-secret error categories, lookback windows, and configured source allowlists.
- **Expected outputs:** Clear source-health metadata indicating whether each configured source is healthy, degraded, skipped, or unavailable, plus safe partial-output guidance when some sources fail.
- **Success criteria:** Connector failures are visible without exposing credentials or private URLs, malformed required records still fail clearly, partial results remain source-backed, sample and evaluation workflows stay deterministic, and local `jira_mcp` continues to fail safely outside an approved MCP runtime.
- **Out of scope:** New live API calls, credentials, automated retries against real services, deployment monitoring, and posting or write-back behavior.

### v0.8.0 Real GitHub Connector

- **Objective:** Load live pull request activity from approved repositories while preserving the local PR intelligence behavior.
- **Expected inputs:** Repository allowlist, lookback/staleness settings, read-only token supplied outside the repository, and review/check inclusion flags.
- **Expected outputs:** GitHub PR records with review, CI, merge, stale, linked-issue, owner, and source-reference metadata adapted to the connector contract.
- **Success criteria:** Live PR records preserve stable PR numbers and URLs, risky PRs route consistently to generated sections/questions, and sample fixtures continue to pass evaluation.
- **Out of scope:** Writing PR comments, changing labels, merging PRs, organization-wide discovery, and messaging/posting integrations.

### v0.9.0 Slack/Teams Message Connector

- **Objective:** Add an approved messaging connector for standup-relevant signals from configured channels.
- **Expected inputs:** Provider selection, approved channel allowlist, lookback window, thread inclusion setting, signal keywords, and read-only credentials supplied externally.
- **Expected outputs:** Relevant chat messages adapted to `chat_data.channels[*].messages` with stable message IDs, timestamps, optional links, and concise source references.
- **Success criteria:** Connector avoids noisy chatter, does not scrape unapproved channels, preserves message traceability, and keeps generated summaries neutral and source-backed.
- **Out of scope:** Broad workspace search, private/direct messages, posting, moderation workflows, and non-approved channels.

### v1.0.0 Facilitator Approval and Posting Workflow

- **Objective:** Add a controlled workflow for facilitator approval before sharing a generated pre-read to a team channel.
- **Expected inputs:** Generated pre-read, review status, reviewer metadata, posting provider, destination channel, and post-only-approved setting.
- **Expected outputs:** Approved pre-read copy and optional post to the configured destination when posting is enabled and approval requirements are satisfied.
- **Success criteria:** Drafts and rejected outputs are never posted, approved posts are traceable, posting can be disabled by config, and local file outputs remain available.
- **Out of scope:** Auto-approval, broad broadcast lists, deployment automation, and modifying source systems.

### v1.1.0 One-Team Pilot

- **Objective:** Validate end-to-end usefulness with one approved team using live read-only integrations and facilitator-controlled sharing.
- **Expected inputs:** Sanitized team configuration, approved source allowlists, externally managed credentials, operational runbook, and pilot feedback criteria.
- **Expected outputs:** Daily source-backed pre-read drafts, evaluation reports, facilitator approval records, and pilot learnings for product fit and operational readiness.
- **Success criteria:** Facilitators find the pre-read useful, source references are trusted, no secrets or work-specific data are committed, and sample/evaluation workflows remain healthy.
- **Out of scope:** Multi-team rollout, dashboards, deployment hardening beyond pilot needs, write-back automation, and individual performance scoring.
