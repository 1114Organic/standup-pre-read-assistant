from __future__ import annotations

from datetime import date

from standup_pre_read.collectors import load_github_pr_sample, load_jira_sample, load_prior_standup
from standup_pre_read.config import Config
from standup_pre_read.generator import generate_pre_read
from standup_pre_read.normalizer import normalize_all, normalize_github, normalize_jira, normalize_prior
from standup_pre_read.cli import build_pre_read


REQUIRED_SECTIONS = [
    "## Executive Summary",
    "## Progress Since Last Standup",
    "## Blockers Needing Action",
    "## Decisions Needed",
    "## Risks and Aging Work",
    "## Carryover From Yesterday",
    "## Suggested Standup Agenda",
    "## Source References",
]


def _sample_markdown() -> str:
    activities = normalize_all(
        load_jira_sample(Config.jira_path),
        load_github_pr_sample(Config.github_path),
        load_prior_standup(Config.prior_standup_path),
    )
    return generate_pre_read(activities, "Example Platform Team", stale_pr_days=5, today=date(2026, 6, 16))


def test_generated_pre_read_includes_required_sections() -> None:
    markdown = _sample_markdown()

    for section in REQUIRED_SECTIONS:
        assert section in markdown


def test_normalized_activity_model_preserves_jira_github_and_prior_signals() -> None:
    jira = normalize_jira(load_jira_sample(Config.jira_path))
    github = normalize_github(load_github_pr_sample(Config.github_path))
    prior = normalize_prior(load_prior_standup(Config.prior_standup_path))

    blocked = next(activity for activity in jira if activity.source_id == "DEMO-103")
    failing_pr = next(activity for activity in github if activity.related_work_items == ("DEMO-104",))

    assert blocked.blocker_signal == "Waiting on IAM approval."
    assert failing_pr.related_work_items == ("DEMO-104",)
    assert failing_pr.ci_state == "failing"
    assert failing_pr.review_state == "review_required"
    assert failing_pr.updated_timestamp is not None
    assert any(activity.source_id == "DEMO-103" and activity.activity_type == "prior_carryover" for activity in prior)
    assert all("Confirm documentation acceptance criteria" not in activity.title for activity in prior)


def test_generated_pre_read_includes_data_driven_items_and_sources() -> None:
    markdown = _sample_markdown()
    github = normalize_github(load_github_pr_sample(Config.github_path))
    failing_pr = next(activity for activity in github if activity.related_work_items == ("DEMO-104",))

    assert "DEMO-101 is done" in markdown
    assert "DEMO-102 moved to review" in markdown
    assert "DEMO-103 is blocked Waiting on IAM approval" in markdown
    assert "Decide whether search relevance tuning is global or workspace-only. (DEMO-104)" in markdown
    assert f"{failing_pr.source_id} is open for 6 days since June 10, has failing CI linked to DEMO-104" in markdown
    assert "Follow up with IAM approver for DEMO-103" in markdown
    assert "Confirm documentation acceptance criteria for DEMO-101" not in markdown
    assert "https://jira.example.local/browse/DEMO-104" in markdown
    assert failing_pr.source_url in markdown


def test_generator_uses_alternate_issue_keys_and_pr_numbers() -> None:
    jira_data = {
        "team": "Example Team",
        "issues": [
            {
                "key": "ALT-100",
                "title": "Ship reporting export",
                "status": "Blocked",
                "assignee": "Dev One",
                "updated": "2026-06-15T12:00:00+00:00",
                "sprint": "Sprint 1",
                "url": "https://jira.example.local/browse/ALT-100",
                "summary": "Export work cannot continue until storage policy is approved.",
                "blocker": True,
                "blocked_reason": "Waiting on storage policy approval.",
            },
            {
                "key": "ALT-101",
                "title": "Pick rollout scope",
                "status": "In Progress",
                "assignee": "Dev Two",
                "updated": "2026-06-15T12:00:00+00:00",
                "sprint": "Sprint 1",
                "url": "https://jira.example.local/browse/ALT-101",
                "summary": "Rollout implementation is underway.",
                "blocker": False,
                "decision_needed": "Choose beta-only or all-user rollout.",
            },
        ],
    }
    github_data = {
        "repositories": [
            {
                "name": "alternate-service",
                "pull_requests": [
                    {
                        "number": 9001,
                        "title": "Add export worker",
                        "author": "dev-one",
                        "state": "open",
                        "review_state": "changes_requested",
                        "created": "2026-06-01T12:00:00+00:00",
                        "updated": "2026-06-08T12:00:00+00:00",
                        "merged": False,
                        "url": "https://github.com/example/alternate-service/pull/9001",
                        "linked_issues": ["ALT-100"],
                        "ci_state": "failing",
                        "summary": "Export worker has failing tests.",
                    }
                ],
            }
        ],
    }
    prior = """# Prior\n\n## Carryover From Yesterday\n\n- Follow up on ALT-100 approval. Status: unresolved.\n- Retest OLD-1. Status: resolved.\n"""

    markdown = generate_pre_read(normalize_all(jira_data, github_data, prior), "Example Team", stale_pr_days=5, today=date(2026, 6, 16))

    assert "ALT-100 is blocked Waiting on storage policy approval" in markdown
    assert "Choose beta-only or all-user rollout. (ALT-101)" in markdown
    assert "PR #9001 is open for 15 days since June 1, has failing CI, requested review changes, no updates for 8 days linked to ALT-100" in markdown
    assert "Follow up on ALT-100 approval" in markdown
    assert "Retest OLD-1" not in markdown
    assert "DEMO-" not in markdown
    assert "example-platform-service" not in markdown


def test_build_pre_read_writes_configured_output(tmp_path) -> None:
    output_path = tmp_path / "standup-pre-read.md"
    config = Config(output_path=output_path)

    markdown = build_pre_read(config)

    assert output_path.read_text(encoding="utf-8") == markdown
    assert "# Standup Pre-Read: Example Platform Team" in markdown
