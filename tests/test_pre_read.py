from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from standup_pre_read.cli import build_pre_read, main, parse_args
from standup_pre_read.collectors import (
    load_chat_sample,
    load_github_pr_sample,
    load_jira_mcp_sample,
    load_jira_sample,
    load_prior_standup,
)
from standup_pre_read.config import Config
from standup_pre_read.connectors import (
    ConnectorContractError,
    JiraMcpConnector,
    JiraMcpRuntimeUnavailableError,
    JiraMcpSampleSourceConnector,
    SampleSourceConnector,
    SourceData,
    source_connector_for,
    validate_source_data,
)
from standup_pre_read.generator import generate_pre_read, generate_pre_read_document
from standup_pre_read.models import Activity
from standup_pre_read.normalizer import (
    normalize_all,
    normalize_chat,
    normalize_github,
    normalize_jira,
    normalize_prior,
    parse_datetime,
)

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


def test_chat_sample_data_can_be_loaded_and_normalized() -> None:
    chat_data = load_chat_sample(Path("examples/chat-rich-sample.json"))
    activities = normalize_chat(chat_data)

    assert len(activities) == 4
    assert {activity.activity_type for activity in activities} == {
        "chat_blocker",
        "chat_decision",
        "chat_follow_up",
        "chat_signal",
    }
    assert all(activity.source_system == "chat" for activity in activities)
    assert not any("Good morning team" in activity.description for activity in activities)


def test_chat_signals_appear_without_noisy_chatter_and_include_sources(tmp_path: Path) -> None:
    output_path = tmp_path / "chat-pre-read.md"

    markdown = build_pre_read(
        Config(
            jira_path=Path("examples/jira-rich-sample.json"),
            github_path=Path("examples/github-pr-rich-sample.json"),
            prior_standup_path=Path("examples/prior-standup-rich.md"),
            chat_path=Path("examples/chat-rich-sample.json"),
            output_path=output_path,
        )
    )

    assert "Chat blocker: Blocked on SAMPLE-212" in markdown
    assert "Source: chat-001." in markdown
    assert "Chat decision requested: Decision needed for SAMPLE-213" in markdown
    assert "Source: chat-002." in markdown
    assert "Follow up with the release checklist owner for SAMPLE-214" in markdown
    assert "Who can clarify ownership or next steps from chat: Who owns SAMPLE-214 now" in markdown
    assert "https://chat.example.local/archives/sample-team-standup/p001" in markdown
    assert "Good morning team" not in markdown


def test_json_output_includes_chat_derived_items(tmp_path: Path) -> None:
    markdown_output_path = tmp_path / "chat-pre-read.md"
    json_output_path = tmp_path / "chat-pre-read.json"

    build_pre_read(
        Config(
            jira_path=Path("examples/jira-rich-sample.json"),
            github_path=Path("examples/github-pr-rich-sample.json"),
            prior_standup_path=Path("examples/prior-standup-rich.md"),
            chat_path=Path("examples/chat-rich-sample.json"),
            output_path=markdown_output_path,
            json_output_path=json_output_path,
        )
    )
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))

    assert any("chat-001" in item["source_refs"] for item in payload["blockers"])
    assert any("chat-002" in item["source_refs"] for item in payload["decisions"])
    assert any("chat-003" in item["source_refs"] for item in payload["carryover"])
    assert any(reference["source_system"] == "chat" for reference in payload["source_references"])



def test_parse_args_accepts_real_jira_mcp_mode(tmp_path: Path) -> None:
    output_path = tmp_path / "real-mcp-pre-read.md"
    config = parse_args(["--source-mode", "jira_mcp", "--output-path", str(output_path)])

    assert config.source_mode == "jira_mcp"
    assert config.output_path == output_path
    assert isinstance(source_connector_for(config), JiraMcpConnector)


def test_config_loads_real_jira_mcp_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "team.yaml"
    config_path.write_text(
        """team:
  name: Example Team
sources:
  jira:
    enabled: true
    mode: jira_mcp
    mcp_server_name: placeholder-jira-mcp
    jql: project in (EXAMPLE) AND updated >= -1d
    project_keys:
      - EXAMPLE
    include_comments: true
    max_results: 25
security:
  allow_live_connectors: true
""",
        encoding="utf-8",
    )

    config = parse_args(["--config", str(config_path)])

    assert config.source_mode == "jira_mcp"
    assert config.jira_enabled is True
    assert config.jira_mcp_server_name == "placeholder-jira-mcp"
    assert config.jira_jql == "project in (EXAMPLE) AND updated >= -1d"
    assert config.jira_project_keys == ("EXAMPLE",)
    assert config.jira_include_comments is True
    assert config.jira_max_results == 25
    assert config.allow_live_connectors is True


def test_real_jira_mcp_fails_safely_without_approved_runtime(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import socket

    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network connection attempted")

    monkeypatch.setattr(socket, "create_connection", fail_network)

    with pytest.raises(JiraMcpRuntimeUnavailableError) as excinfo:
        build_pre_read(Config(source_mode="jira_mcp", output_path=tmp_path / "real-mcp.md"))

    message = str(excinfo.value)
    assert "disabled by default" in message
    assert "security.allow_live_connectors is false" in message
    assert "approved work environment" in message
    assert "No credentials, network calls, or Jira requests were attempted" in message
    assert not (tmp_path / "real-mcp.md").exists()


def test_real_jira_mcp_disabled_config_message_is_clear() -> None:
    with pytest.raises(JiraMcpRuntimeUnavailableError) as excinfo:
        JiraMcpConnector(Config(source_mode="jira_mcp", jira_enabled=False, allow_live_connectors=True)).load()

    assert "disabled by config" in str(excinfo.value)
    assert "sources.jira.enabled is false" in str(excinfo.value)


def test_real_jira_mcp_runtime_boundary_message_is_clear_when_live_switch_enabled() -> None:
    with pytest.raises(JiraMcpRuntimeUnavailableError) as excinfo:
        JiraMcpConnector(Config(source_mode="jira_mcp", allow_live_connectors=True)).load()

    message = str(excinfo.value)
    assert "approved MCP runtime" in message
    assert "sources.jira.mcp_server_name" in message
    assert "No credentials, network calls, or Jira requests were attempted" in message


def test_jira_mcp_sample_response_loads_and_normalizes() -> None:
    jira_data = load_jira_mcp_sample(Path("examples/jira-mcp-sample-response.json"))
    activities = normalize_jira(jira_data)

    assert {issue["key"] for issue in jira_data["issues"]} == {"MCP-101", "MCP-102", "MCP-103", "MCP-104", "MCP-105"}
    assert all(activity.activity_type == "jira_issue" for activity in activities)
    blocked = next(activity for activity in activities if activity.source_id == "MCP-103")
    decision = next(activity for activity in activities if activity.source_id == "MCP-104")
    unclear = next(activity for activity in activities if activity.source_id == "MCP-105")
    assert blocked.blocker_signal == "Waiting on generic dependency approval."
    assert decision.decision_signal == "Decide whether the sample rollout uses option A or option B."
    assert unclear.owner is None
    assert unclear.status == "Unknown"
    assert blocked.source_url == "https://jira.example.invalid/browse/MCP-103"


def test_parse_args_accepts_jira_mcp_sample_options(tmp_path: Path) -> None:
    output_path = tmp_path / "mcp-pre-read.md"
    config = parse_args(
        [
            "--source-mode",
            "jira_mcp_sample",
            "--jira-mcp-path",
            "examples/jira-mcp-sample-response.json",
            "--github-path",
            "examples/github-pr-rich-sample.json",
            "--prior-standup-path",
            "examples/prior-standup-rich.md",
            "--chat-path",
            "examples/chat-rich-sample.json",
            "--output-path",
            str(output_path),
        ]
    )

    assert config.source_mode == "jira_mcp_sample"
    assert config.jira_mcp_path == Path("examples/jira-mcp-sample-response.json")
    assert config.output_path == output_path


def test_jira_mcp_sample_generates_markdown_and_json_with_sources(tmp_path: Path) -> None:
    markdown_output_path = tmp_path / "jira-mcp-pre-read.md"
    json_output_path = tmp_path / "jira-mcp-pre-read.json"

    markdown = build_pre_read(
        Config(
            source_mode="jira_mcp_sample",
            jira_mcp_path=Path("examples/jira-mcp-sample-response.json"),
            output_path=markdown_output_path,
            json_output_path=json_output_path,
        )
    )
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))

    assert payload["source_mode"] == "jira_mcp_sample"
    assert "MCP-101 is done" in markdown
    assert "MCP-102 is in progress" in markdown
    assert "MCP-103 is blocked Waiting on generic dependency approval" in markdown
    assert "Decide whether the sample rollout uses option A or option B. (MCP-104)." in markdown
    assert "Who owns MCP-105 and what is its current status; missing owner, status" in markdown
    assert "https://jira.example.invalid/browse/MCP-104" in markdown
    assert any("MCP-101" in item["source_refs"] for item in payload["progress"])
    assert any("MCP-103" in item["source_refs"] for item in payload["blockers"])
    assert any("MCP-104" in item["source_refs"] for item in payload["decisions"])
    assert any("MCP-105" in item["source_refs"] for item in payload["suggested_questions"])
    assert any(reference["url"].endswith("/MCP-103") for reference in payload["source_references"])


def test_jira_mcp_sample_does_not_attempt_real_connection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import socket

    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network connection attempted")

    monkeypatch.setattr(socket, "create_connection", fail_network)

    markdown = build_pre_read(
        Config(
            source_mode="jira_mcp_sample",
            jira_mcp_path=Path("examples/jira-mcp-sample-response.json"),
            output_path=tmp_path / "jira-mcp-pre-read.md",
        )
    )

    assert "MCP-101 is done" in markdown

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
    rich_github = normalize_github(load_github_pr_sample(Path("examples/github-pr-rich-sample.json")))
    stale_pr = next(activity for activity in rich_github if activity.source_id == "PR #1202")
    blocked_pr = next(activity for activity in rich_github if activity.source_id == "PR #1204")
    assert stale_pr.stale_days == 8
    assert blocked_pr.risk_signal == "merge blocked, Pending dependency approval in sample environment."
    unowned_pr = next(activity for activity in github if activity.source_id == "PR #504")
    decision_pr = next(activity for activity in github if activity.source_id == "PR #505")
    assert unowned_pr.owner is None
    assert unowned_pr.reviewers == ("reviewer-a",)
    assert unowned_pr.related_work_items == ()
    assert unowned_pr.merge_state == "clean"
    assert decision_pr.merge_state == "waiting_on_decision"
    assert decision_pr.decision_signal == "Decide which search rollout guardrail is required before merge."
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
    assert "PR #503 merged after approval" in markdown
    assert "PR #504" in markdown
    assert "Should PR #504 be linked to an issue" in markdown
    assert "Decide which search rollout guardrail is required before merge. (PR #505)." in markdown
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


def test_build_pre_read_rejects_unknown_source_mode(tmp_path: Path) -> None:
    config = Config(source_mode="unknown", output_path=tmp_path / "standup-pre-read.md")

    with pytest.raises(ValueError, match="Unsupported source_mode 'unknown'"):
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


def test_parse_args_accepts_alternate_sample_paths(tmp_path: Path) -> None:
    output_path = tmp_path / "rich-pre-read.md"

    config = parse_args(
        [
            "--source-mode",
            "sample",
            "--jira-path",
            "examples/jira-rich-sample.json",
            "--github-path",
            "examples/github-pr-rich-sample.json",
            "--prior-standup-path",
            "examples/prior-standup-rich.md",
            "--chat-path",
            "examples/chat-rich-sample.json",
            "--output-path",
            str(output_path),
        ]
    )

    assert config.source_mode == "sample"
    assert config.jira_path == Path("examples/jira-rich-sample.json")
    assert config.github_path == Path("examples/github-pr-rich-sample.json")
    assert config.prior_standup_path == Path("examples/prior-standup-rich.md")
    assert config.chat_path == Path("examples/chat-rich-sample.json")
    assert config.output_path == output_path


def test_rich_sample_scenario_generates_expected_demo_signals(tmp_path: Path) -> None:
    output_path = tmp_path / "rich-pre-read.md"

    markdown = build_pre_read(
        Config(
            jira_path=Path("examples/jira-rich-sample.json"),
            github_path=Path("examples/github-pr-rich-sample.json"),
            prior_standup_path=Path("examples/prior-standup-rich.md"),
            output_path=output_path,
        )
    )

    assert output_path.read_text(encoding="utf-8") == markdown
    assert "SAMPLE-210 is done" in markdown
    assert "SAMPLE-211 moved to review" in markdown
    assert "SAMPLE-212 is blocked Waiting on service credential approval" in markdown
    assert "Decide whether notifications launch to pilot users or all workspaces. (SAMPLE-213)." in markdown
    assert "PR #1202 is open for" in markdown
    assert "has failing CI" in markdown
    assert "no updates for" in markdown
    assert "PR #1204 is open for" in markdown
    assert "blocked from merging" in markdown
    assert "PR #1204 is has failing CI" not in markdown
    assert "Follow up on SAMPLE-212 credential approval" in markdown
    assert "Confirm SAMPLE-214 owner and current status" in markdown
    assert "Verify SAMPLE-210 checklist acceptance" not in markdown
    assert "Who owns SAMPLE-214 and what is its current status; missing owner" in markdown
    assert "What action is needed today to unblock SAMPLE-212" in markdown
    assert "Who can make or facilitate the decision for SAMPLE-213" in markdown
    assert "Should we keep carrying over SAMPLE-214" in markdown
    assert "DEMO-" not in markdown
    assert "example-platform-service" not in markdown


def test_parse_args_accepts_json_output_path(tmp_path: Path) -> None:
    json_output_path = tmp_path / "pre-read.json"

    config = parse_args(["--json-output-path", str(json_output_path)])

    assert config.json_output_path == json_output_path


def test_build_pre_read_writes_json_output_with_expected_sections_and_sources(tmp_path: Path) -> None:
    markdown_output_path = tmp_path / "standup-pre-read.md"
    json_output_path = tmp_path / "standup-pre-read.json"

    markdown = build_pre_read(Config(output_path=markdown_output_path, json_output_path=json_output_path))
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))

    assert markdown_output_path.read_text(encoding="utf-8") == markdown
    assert "## Progress Since Last Standup" in markdown
    assert set(payload) >= {
        "generated_at",
        "team_name",
        "source_mode",
        "data_window",
        "executive_summary",
        "progress",
        "blockers",
        "decisions",
        "risks",
        "carryover",
        "suggested_agenda",
        "suggested_questions",
        "source_references",
    }
    assert payload["source_mode"] == "sample"
    assert payload["progress"]
    assert all("text" in item and "source_refs" in item for item in payload["progress"])
    assert any(item["source_refs"] for item in payload["blockers"] + payload["risks"] + payload["suggested_questions"])


def test_pr_metadata_in_json_includes_staleness_and_review_signals(tmp_path: Path) -> None:
    markdown_output_path = tmp_path / "rich-pre-read.md"
    json_output_path = tmp_path / "rich-pre-read.json"

    build_pre_read(
        Config(
            jira_path=Path("examples/jira-rich-sample.json"),
            github_path=Path("examples/github-pr-rich-sample.json"),
            prior_standup_path=Path("examples/prior-standup-rich.md"),
            output_path=markdown_output_path,
            json_output_path=json_output_path,
        )
    )
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))
    metadata_items = [
        metadata
        for section in ("progress", "risks", "decisions", "suggested_questions")
        for item in payload[section]
        for metadata in item.get("pr_metadata", [])
    ]

    assert any(metadata.get("stale_days") == 8 and metadata.get("age_days") == 8 for metadata in metadata_items)
    assert any(metadata.get("review_state") == "changes_requested" for metadata in metadata_items)
    assert any(metadata.get("merge_state") == "waiting_on_decision" for metadata in metadata_items)


def test_generated_json_uses_same_structured_data_as_markdown() -> None:
    activities = normalize_all(
        load_jira_sample(Config.jira_path),
        load_github_pr_sample(Config.github_path),
        load_prior_standup(Config.prior_standup_path),
    )

    document = generate_pre_read_document(
        activities,
        "Example Platform Team",
        stale_pr_days=5,
        today=date(2026, 6, 16),
        source_mode="sample",
    )
    markdown = generate_pre_read(activities, "Example Platform Team", stale_pr_days=5, today=date(2026, 6, 16))
    payload = document.to_json_dict()

    assert payload["progress"][0]["text"] in markdown
    assert payload["blockers"][0]["source_refs"] == ["DEMO-103"]
    assert payload["blockers"][0]["confidence"] == "high"
    assert "DEMO-103" in payload["blockers"][0]["related_work_items"]
    assert payload["blockers"][0]["priority"] > min(item["priority"] for item in payload["progress"])


def test_priority_orders_high_signal_items_before_routine_items() -> None:
    activities = [
        Activity(
            source_system="issue_tracker",
            source_id="ALT-301",
            source_url=None,
            title="Routine progress",
            description="Implementation is proceeding.",
            owner="dev-one",
            team=None,
            project=None,
            activity_type="jira_issue",
            status="In Progress",
            timestamp=parse_datetime("2026-06-15T12:00:00+00:00"),
        ),
        Activity(
            source_system="issue_tracker",
            source_id="ALT-302",
            source_url=None,
            title="Unowned dependency",
            description="Cannot proceed until partner API is enabled.",
            owner=None,
            team=None,
            project=None,
            activity_type="jira_issue",
            status="Blocked",
            timestamp=parse_datetime("2026-06-15T12:00:00+00:00"),
            blocker_signal="Partner API access is unavailable.",
        ),
        Activity(
            source_system="issue_tracker",
            source_id="ALT-303",
            source_url=None,
            title="Choose rollout path",
            description="Routine implementation continues after choice.",
            owner="facilitator",
            team=None,
            project=None,
            activity_type="jira_issue",
            status="In Progress",
            timestamp=parse_datetime("2026-06-15T12:00:00+00:00"),
            decision_signal="Choose pilot or full rollout.",
        ),
        Activity(
            source_system="source_host",
            source_id="PR #303",
            source_url=None,
            title="Routine refactor",
            description="Ready for review.",
            owner="dev-two",
            team=None,
            project=None,
            activity_type="github_pr",
            status="open",
            timestamp=parse_datetime("2026-06-15T12:00:00+00:00"),
            related_work_items=("ALT-301",),
            updated_timestamp=parse_datetime("2026-06-15T12:00:00+00:00"),
            ci_state="passing",
            review_state="review_required",
        ),
        Activity(
            source_system="source_host",
            source_id="PR #304",
            source_url=None,
            title="Risky migration",
            description="Migration tests are failing.",
            owner="dev-three",
            team=None,
            project=None,
            activity_type="github_pr",
            status="open",
            timestamp=parse_datetime("2026-06-01T12:00:00+00:00"),
            related_work_items=("ALT-302",),
            updated_timestamp=parse_datetime("2026-06-02T12:00:00+00:00"),
            ci_state="failing",
            review_state="changes_requested",
        ),
        Activity(
            source_system="prior_standup",
            source_id="ALT-301",
            source_url=None,
            title="Routine status update from yesterday.",
            description="Routine status update from yesterday.",
            owner="dev-one",
            team=None,
            project=None,
            activity_type="prior_carryover",
            status="unresolved",
            timestamp=None,
        ),
        Activity(
            source_system="prior_standup",
            source_id="ALT-302",
            source_url=None,
            title="Unresolved partner API blocker from yesterday.",
            description="Unresolved partner API blocker from yesterday.",
            owner=None,
            team=None,
            project=None,
            activity_type="prior_blocker",
            status="unresolved",
            timestamp=None,
        ),
    ]

    document = generate_pre_read_document(
        activities,
        "Example Team",
        stale_pr_days=5,
        today=date(2026, 6, 16),
    )
    payload = document.to_json_dict()

    assert document.blockers[0].source_refs == ("ALT-302",)
    assert document.decisions[0].source_refs == ("ALT-303",)
    assert document.risks[0].source_refs == ("PR #304",)
    assert document.carryover[0].text == "Unresolved partner API blocker from yesterday."
    assert document.progress[0].source_refs[0] == "ALT-301"
    assert document.suggested_questions[0].priority is not None
    assert document.suggested_questions[-1].priority is not None
    assert document.suggested_questions[0].priority >= document.suggested_questions[-1].priority
    assert document.suggested_questions[0].priority == document.risks[0].priority
    assert payload["risks"][0]["priority"] > payload["progress"][0]["priority"]
    assert payload["carryover"][0]["priority"] > payload["carryover"][1]["priority"]


def test_rich_sample_scenario_writes_json_output(tmp_path: Path) -> None:
    markdown_output_path = tmp_path / "rich-pre-read.md"
    json_output_path = tmp_path / "rich-pre-read.json"

    build_pre_read(
        Config(
            jira_path=Path("examples/jira-rich-sample.json"),
            github_path=Path("examples/github-pr-rich-sample.json"),
            prior_standup_path=Path("examples/prior-standup-rich.md"),
            output_path=markdown_output_path,
            json_output_path=json_output_path,
        )
    )
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))

    assert payload["progress"]
    assert any("SAMPLE-212" in item["source_refs"] for item in payload["blockers"])
    assert any("PR #1202" in item["source_refs"] for item in payload["risks"])
    assert any(item.get("related_work_items") for item in payload["risks"])
    assert any(
        metadata.get("ci_state") == "failing"
        for item in payload["risks"]
        for metadata in item.get("pr_metadata", [])
    )
    assert any("PR #1205" in item["source_refs"] for item in payload["suggested_questions"])
    assert any("PR #1206" in item["source_refs"] for item in payload["decisions"])
    assert payload["source_references"]


def test_main_writes_configured_output_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_path = tmp_path / "cli-pre-read.md"

    main(["--source-mode", "sample", "--output-path", str(output_path)])

    assert output_path.exists()
    assert "# Standup Pre-Read: Example Platform Team" in output_path.read_text(encoding="utf-8")
    assert str(output_path) in capsys.readouterr().out


def test_main_rejects_unavailable_jira_mcp_mode_cleanly(tmp_path: Path) -> None:
    output_path = tmp_path / "cli-pre-read.md"

    with pytest.raises(SystemExit, match="security.allow_live_connectors is false"):
        main(["--source-mode", "jira_mcp", "--output-path", str(output_path)])

    assert not output_path.exists()


def test_parse_datetime_accepts_utc_z_suffix() -> None:
    parsed = parse_datetime("2026-06-16T12:30:00Z")

    assert parsed is not None
    assert parsed.isoformat() == "2026-06-16T12:30:00+00:00"


def test_build_pre_read_can_create_default_config() -> None:
    markdown = build_pre_read()

    assert "# Standup Pre-Read: Example Platform Team" in markdown


def test_default_review_status_is_draft_in_markdown_and_json(tmp_path: Path) -> None:
    markdown_output_path = tmp_path / "draft.md"
    json_output_path = tmp_path / "draft.json"

    markdown = build_pre_read(Config(output_path=markdown_output_path, json_output_path=json_output_path))
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))

    assert "## Review Metadata" in markdown
    assert "- Status: draft" in markdown
    assert payload["review_status"] == "draft"
    assert "reviewed_at" not in payload


def test_approved_review_status_appears_and_writes_approved_output(tmp_path: Path) -> None:
    markdown_output_path = tmp_path / "approved-draft.md"
    json_output_path = tmp_path / "approved.json"
    approved_output_path = tmp_path / "approved.md"

    markdown = build_pre_read(
        Config(
            output_path=markdown_output_path,
            json_output_path=json_output_path,
            review_status="approved",
            reviewer="Facilitator",
            review_notes="Ready to share.",
            approved_output_path=approved_output_path,
        )
    )
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))

    assert "- Status: approved" in markdown
    assert "- Reviewer: Facilitator" in markdown
    assert "- Notes: Ready to share." in markdown
    assert payload["review_status"] == "approved"
    assert payload["reviewer"] == "Facilitator"
    assert payload["review_notes"] == "Ready to share."
    assert "reviewed_at" in payload
    assert approved_output_path.read_text(encoding="utf-8") == markdown


def test_rejected_review_status_appears_without_approved_output(tmp_path: Path) -> None:
    markdown_output_path = tmp_path / "rejected.md"
    json_output_path = tmp_path / "rejected.json"
    approved_output_path = tmp_path / "should-not-exist.md"

    markdown = build_pre_read(
        Config(
            output_path=markdown_output_path,
            json_output_path=json_output_path,
            review_status="rejected",
            reviewer="Facilitator",
            review_notes="Needs edits.",
            approved_output_path=approved_output_path,
        )
    )
    payload = json.loads(json_output_path.read_text(encoding="utf-8"))

    assert "- Status: rejected" in markdown
    assert "- Reviewer: Facilitator" in markdown
    assert "- Notes: Needs edits." in markdown
    assert payload["review_status"] == "rejected"
    assert payload["reviewer"] == "Facilitator"
    assert payload["review_notes"] == "Needs edits."
    assert "reviewed_at" in payload
    assert not approved_output_path.exists()


def test_parse_args_accepts_review_options(tmp_path: Path) -> None:
    approved_output_path = tmp_path / "approved.md"

    config = parse_args(
        [
            "--review-status",
            "approved",
            "--reviewer",
            "Facilitator",
            "--review-notes",
            "Ready.",
            "--approved-output-path",
            str(approved_output_path),
        ]
    )

    assert config.review_status == "approved"
    assert config.reviewer == "Facilitator"
    assert config.review_notes == "Ready."
    assert config.approved_output_path == approved_output_path


def test_sample_connector_output_satisfies_connector_contract() -> None:
    source_data = SampleSourceConnector(Config()).load()

    validate_source_data(source_data)
    assert source_data.jira_data["issues"]
    assert source_data.github_data["repositories"]
    assert isinstance(source_data.prior_markdown, str)
    assert source_data.chat_data == {"channels": []}


def test_jira_mcp_sample_connector_output_satisfies_connector_contract() -> None:
    source_data = JiraMcpSampleSourceConnector(Config(source_mode="jira_mcp_sample")).load()

    validate_source_data(source_data)
    assert source_data.jira_data["issues"]
    assert all(issue["key"].startswith("MCP-") for issue in source_data.jira_data["issues"])


def test_connector_contract_rejects_missing_required_payloads() -> None:
    invalid_source_data = SourceData(
        jira_data={"issues": [{"title": "Missing key and status"}]},
        github_data={
            "repositories": [{"name": "sample-repo", "pull_requests": [{"title": "Missing number and state"}]}]
        },
        prior_markdown="# Prior standup",
        chat_data={"channels": []},
    )

    with pytest.raises(ConnectorContractError) as excinfo:
        validate_source_data(invalid_source_data)

    message = str(excinfo.value)
    assert "jira_data.issues[0].key is required" in message
    assert "jira_data.issues[0].status is required" in message
    assert "github_data.repositories[0].pull_requests[0].number is required" in message
    assert "github_data.repositories[0].pull_requests[0].state is required" in message


def test_connector_contract_rejects_invalid_timestamps_with_clear_path() -> None:
    invalid_source_data = SourceData(
        jira_data={"issues": [{"key": "BAD-1", "status": "In Progress", "updated": "yesterday"}]},
        github_data={"repositories": []},
        prior_markdown="# Prior standup",
        chat_data={"channels": [{"messages": [{"id": "chat-1", "text": "Blocked", "timestamp": "soon"}]}]},
    )

    with pytest.raises(ConnectorContractError) as excinfo:
        validate_source_data(invalid_source_data)

    message = str(excinfo.value)
    assert "jira_data.issues[0].updated must be a valid ISO-8601 timestamp" in message
    assert "chat_data.channels[0].messages[0].timestamp must be a valid ISO-8601 timestamp" in message


def test_example_team_config_loads_without_secrets() -> None:
    config_text = Path("config/example-team.yaml").read_text(encoding="utf-8")
    lowered = config_text.lower()

    assert "xox" not in lowered
    assert "ghp_" not in lowered
    assert "bearer " not in lowered
    assert "password:" not in lowered
    assert "http://" not in lowered
    assert "https://" not in lowered

    config = parse_args(["--config", "config/example-team.yaml"])

    assert config.team_name == "Example Team"
    assert config.source_mode == "sample"
    assert config.output_path == Path("output/standup-pre-read.md")
    assert config.json_output_path == Path("output/standup-pre-read.json")
    assert config.review_status == "draft"
    assert config.stale_pr_days == 5


def test_cli_flags_override_example_team_config(tmp_path: Path) -> None:
    output_path = tmp_path / "override.md"
    json_path = tmp_path / "override.json"

    config = parse_args(
        [
            "--config",
            "config/example-team.yaml",
            "--source-mode",
            "jira_mcp_sample",
            "--output-path",
            str(output_path),
            "--json-output-path",
            str(json_path),
            "--reviewer",
            "CLI Reviewer",
            "--stale-pr-days",
            "2",
        ]
    )

    assert config.source_mode == "jira_mcp_sample"
    assert config.output_path == output_path
    assert config.json_output_path == json_path
    assert config.reviewer == "CLI Reviewer"
    assert config.stale_pr_days == 2


def test_example_team_config_preserves_sample_mode_generation(tmp_path: Path) -> None:
    output_path = tmp_path / "configured.md"
    json_path = tmp_path / "configured.json"

    config = parse_args(
        [
            "--config",
            "config/example-team.yaml",
            "--output-path",
            str(output_path),
            "--json-output-path",
            str(json_path),
        ]
    )
    markdown = build_pre_read(config)
    payload = json.loads(json_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert payload["team_name"] == "Example Team"
    assert payload["source_mode"] == "sample"
    assert "## Executive Summary" in markdown
