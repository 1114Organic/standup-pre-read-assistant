from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from standup_pre_read.cli import build_pre_read, main, parse_args
from standup_pre_read.collectors import load_github_pr_sample, load_jira_sample, load_prior_standup
from standup_pre_read.config import Config
from standup_pre_read.generator import generate_pre_read
from standup_pre_read.models import Activity
from standup_pre_read.normalizer import normalize_all, normalize_github, normalize_jira, normalize_prior, parse_datetime

REQUIRED_SECTIONS = [
    "## Executive Summary",
    "## Progress Since Last Standup",
    "## Blockers Needing Action",
    "## Decisions Needed",
    "## Risks and Aging Work",
    "## Carryover From Yesterday",
    "## Suggested Standup Agenda",
    "## Suggested Standup Questions",
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
    assert failing_pr.source_url is not None
    assert failing_pr.source_url in markdown


def test_suggested_questions_cover_standup_question_mode_signals() -> None:
    markdown = _sample_markdown()

    assert "## Suggested Standup Questions" in markdown
    assert "What action is needed today to unblock DEMO-103: Waiting on IAM approval? Source: DEMO-103." in markdown
    assert "What is the next step to reduce risk on PR #502:" in markdown
    assert "Source: PR #502." in markdown
    assert (
        "Who can make or facilitate the decision for DEMO-104: "
        "Decide whether search relevance tuning is global or workspace-only? Source: DEMO-104."
    ) in markdown
    assert "Should we keep carrying over DEMO-103" in markdown
    assert "Source: DEMO-103." in markdown


def test_suggested_questions_are_data_driven_and_detect_missing_owner_status() -> None:
    activities = [
        Activity(
            source_system="issue_tracker",
            source_id="ALT-200",
            source_url="https://example.invalid/issues/ALT-200",
            title="Unowned blocked work",
            description="Needs dependency approval.",
            owner=None,
            team=None,
            project=None,
            activity_type="jira_issue",
            status="Blocked",
            timestamp=parse_datetime("2026-06-15T12:00:00+00:00"),
            related_work_items=("ALT-200",),
            blocker_signal="Needs dependency approval.",
        ),
        Activity(
            source_system="source_host",
            source_id="PR #77",
            source_url="https://example.invalid/pulls/77",
            title="Stale risky change",
            description="Waiting for review.",
            owner="contributor",
            team=None,
            project="sample-repo",
            activity_type="github_pr",
            status="open",
            timestamp=parse_datetime("2026-06-01T12:00:00+00:00"),
            related_work_items=("ALT-200",),
            updated_timestamp=parse_datetime("2026-06-02T12:00:00+00:00"),
            ci_state="passing",
            review_state="changes_requested",
        ),
        Activity(
            source_system="issue_tracker",
            source_id="ALT-201",
            source_url="https://example.invalid/issues/ALT-201",
            title="Choose launch option",
            description="Implementation is pending scope choice.",
            owner="facilitator",
            team=None,
            project=None,
            activity_type="jira_issue",
            status="In Progress",
            timestamp=parse_datetime("2026-06-15T12:00:00+00:00"),
            related_work_items=("ALT-201",),
            decision_signal="Choose narrow or broad launch.",
        ),
        Activity(
            source_system="prior_standup",
            source_id="ALT-202",
            source_url=None,
            title="Follow up on unresolved dependency.",
            description="Follow up on unresolved dependency.",
            owner=None,
            team=None,
            project=None,
            activity_type="prior_carryover",
            status="unresolved",
            timestamp=None,
            related_work_items=("ALT-202",),
        ),
    ]

    markdown = generate_pre_read(activities, "Example Team", stale_pr_days=5, today=date(2026, 6, 16))

    assert "What action is needed today to unblock ALT-200: Needs dependency approval? Source: ALT-200." in markdown
    assert "What is the next step to reduce risk on PR #77:" in markdown
    assert (
        "Who can make or facilitate the decision for ALT-201: Choose narrow or broad launch? Source: ALT-201."
        in markdown
    )
    assert "Should we keep carrying over ALT-202" in markdown
    assert "Who owns ALT-200 and what is its current status; missing owner? Source: ALT-200." in markdown
    assert "DEMO-" not in markdown
    assert "example-platform-service" not in markdown


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
    prior = (
        "# Prior\n\n"
        "## Carryover From Yesterday\n\n"
        "- Follow up on ALT-100 approval. Status: unresolved.\n"
        "- Retest OLD-1. Status: resolved.\n"
    )

    markdown = generate_pre_read(
        normalize_all(jira_data, github_data, prior),
        "Example Team",
        stale_pr_days=5,
        today=date(2026, 6, 16),
    )

    assert "ALT-100 is blocked Waiting on storage policy approval" in markdown
    assert "Choose beta-only or all-user rollout. (ALT-101)" in markdown
    assert (
        "PR #9001 is open for 15 days since June 1, has failing CI, "
        "requested review changes, no updates for 8 days linked to ALT-100" in markdown
    )
    assert "Follow up on ALT-100 approval" in markdown
    assert "Retest OLD-1" not in markdown
    assert "DEMO-" not in markdown
    assert "example-platform-service" not in markdown


def test_build_pre_read_writes_configured_output(tmp_path: Path) -> None:
    output_path = tmp_path / "standup-pre-read.md"
    config = Config(output_path=output_path)

    markdown = build_pre_read(config)

    assert output_path.read_text(encoding="utf-8") == markdown
    assert "# Standup Pre-Read: Example Platform Team" in markdown


def test_config_defaults_to_sample_source_mode() -> None:
    assert Config().source_mode == "sample"


def test_build_pre_read_uses_default_sample_source_mode(tmp_path: Path) -> None:
    output_path = tmp_path / "standup-pre-read.md"

    markdown = build_pre_read(Config(output_path=output_path))

    assert output_path.read_text(encoding="utf-8") == markdown
    assert "DEMO-101 is done" in markdown
    assert "PR #502" in markdown
    assert "Follow up with IAM approver for DEMO-103" in markdown


def test_build_pre_read_rejects_unsupported_source_mode(tmp_path: Path) -> None:
    config = Config(source_mode="jira_mcp", output_path=tmp_path / "standup-pre-read.md")

    with pytest.raises(ValueError, match="Unsupported source_mode 'jira_mcp'"):
        build_pre_read(config)


def test_parse_args_defaults_to_sample_source_and_default_output() -> None:
    config = parse_args([])

    assert config.source_mode == "sample"
    assert config.output_path == Path("output/standup-pre-read.md")


def test_parse_args_accepts_source_mode_and_output_path(tmp_path: Path) -> None:
    output_path = tmp_path / "custom-pre-read.md"

    config = parse_args(["--source-mode", "sample", "--output-path", str(output_path)])

    assert config.source_mode == "sample"
    assert config.output_path == output_path


def test_main_writes_configured_output_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_path = tmp_path / "cli-pre-read.md"

    main(["--source-mode", "sample", "--output-path", str(output_path)])

    assert output_path.exists()
    assert "# Standup Pre-Read: Example Platform Team" in output_path.read_text(encoding="utf-8")
    assert str(output_path) in capsys.readouterr().out


def test_main_rejects_unsupported_source_mode_cleanly(tmp_path: Path) -> None:
    output_path = tmp_path / "cli-pre-read.md"

    with pytest.raises(SystemExit, match="Unsupported source_mode 'jira_mcp'"):
        main(["--source-mode", "jira_mcp", "--output-path", str(output_path)])

    assert not output_path.exists()


def test_parse_datetime_accepts_utc_z_suffix() -> None:
    parsed = parse_datetime("2026-06-16T12:30:00Z")

    assert parsed is not None
    assert parsed.isoformat() == "2026-06-16T12:30:00+00:00"


def test_build_pre_read_can_create_default_config() -> None:
    markdown = build_pre_read()

    assert "# Standup Pre-Read: Example Platform Team" in markdown
