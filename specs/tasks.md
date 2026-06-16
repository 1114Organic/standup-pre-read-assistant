# Implementation Tasks

## Epic 1: Project Setup

- Create application structure.
- Add configuration format.
- Add local run command.
- Add baseline logging.
- Add tests folder.

## Epic 2: Sample Collectors

- Implement Jira sample file reader.
- Implement GitHub sample file reader.
- Implement prior standup markdown reader.
- Add tests for sample file loading.

## Epic 3: Activity Normalization

- Define normalized activity model.
- Map Jira records into normalized records.
- Map GitHub PR records into normalized records.
- Map prior notes into normalized records.
- Deduplicate related Jira and GitHub records.
- Add tests for normalized output.

## Epic 4: Pre-Read Generation

- Create markdown pre-read template.
- Generate all required sections.
- Include source references.
- Carry forward unresolved prior items.
- Flag stale PRs.
- Flag blockers and decisions.
- Add tests for required sections and key content.

## Epic 5: Local Publishing

- Write generated pre-read to local markdown output.
- Include team name, generation time, and data window.
- Add output path configuration.

## Epic 6: Pilot Readiness

- Add README usage instructions.
- Add Codex starter prompt.
- Document future API integration points.
- Document EKS CronJob as the target pilot runtime.

## Thin-Slice Definition of Done

- The assistant reads all sample files.
- The assistant generates a complete markdown pre-read.
- The generated pre-read includes all required sections.
- The generated pre-read includes source references.
- Unresolved prior blockers carry forward.
- Stale PRs are flagged.
- Tests validate the generated output.

