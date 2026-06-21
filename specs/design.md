# Design

## Architecture Overview

The first version is a local thin-slice worker that reads sample data and generates a markdown pre-read. It should be designed so collectors can later be swapped from file-based collectors to live API collectors.

Future runtime target is an EKS CronJob for the team pilot.

## Flow

1. Load configuration.
2. Read sample Jira activity.
3. Read sample GitHub activity.
4. Read prior standup notes.
5. Normalize all activity into a shared model.
6. Generate the pre-read.
7. Save the markdown draft.
8. Run tests against expected structure.

## Core Components

### Configuration Loader

Loads team-specific settings such as team name, standup time, timezone, lookback window, stale PR threshold, input paths, and output path.

### Source Connector Abstraction

Selects a source connector from configuration and returns one raw payload containing Jira, GitHub, and prior standup inputs. The current supported mode is `sample_files`, which keeps the MVP local while preserving a seam for future live API connectors.

### Jira File Collector

Reads sample Jira JSON and maps issue fields into normalized activity records.

### GitHub File Collector

Reads sample GitHub pull request JSON and maps PR fields into normalized activity records.

### Prior Notes Collector

Reads prior standup markdown and extracts unresolved blockers, open decisions, and carryover action items.

### Activity Normalizer

Converts Jira, GitHub, and prior notes into a shared format.

Recommended normalized fields:

- `source_system`
- `source_id`
- `source_url`
- `title`
- `description`
- `owner`
- `team`
- `project`
- `activity_type`
- `status`
- `timestamp`
- `related_work_items`
- `blocker_signal`
- `decision_signal`
- `risk_signal`
- `confidence`

### Pre-Read Generator

Generates a markdown document with required sections. It may start as deterministic template logic using source data. Later versions can add an AI summarizer once the expected structure is stable.

### Publisher

Writes the draft to a local markdown file.

## Guardrails

The assistant must use only supplied source data.

The assistant must include source references for important claims.

The assistant must use neutral delivery language.

The assistant must avoid individual performance judgments.

The assistant must mark uncertain items as needing confirmation.

The assistant must prioritize blockers, risks, and decisions over routine activity.

## Future Extensions

Replace file collectors with Jira and GitHub API collectors.

Add Teams or Slack collector.

Add Harness collector.

Add Grafana or Prometheus health signals.

Add EKS CronJob manifests.

Add Backstage plugin for configuration and review.

