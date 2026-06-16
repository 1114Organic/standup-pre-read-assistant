from __future__ import annotations

from datetime import date

from standup_pre_read.collectors import load_github_pr_sample, load_jira_sample, load_prior_standup
from standup_pre_read.config import Config
from standup_pre_read.generator import generate_pre_read
from standup_pre_read.normalizer import normalize_all
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
    return generate_pre_read(activities, "Tenant Success ART", stale_pr_days=5, today=date(2026, 6, 16))


def test_generated_pre_read_includes_required_sections() -> None:
    markdown = _sample_markdown()

    for section in REQUIRED_SECTIONS:
        assert section in markdown


def test_generated_pre_read_includes_key_expected_items_and_sources() -> None:
    markdown = _sample_markdown()

    assert "BIP-2422 is done" in markdown
    assert "BIP-2417 moved to review" in markdown
    assert "BIP-2429 is blocked waiting on IAM approval" in markdown
    assert "Decide whether search relevance tuning for BIP-2431" in markdown
    assert "PR #322 has been open since June 10 and has failing CI" in markdown
    assert "Follow up with IAM approver for BIP-2429" in markdown
    assert "Confirm documentation acceptance criteria for BIP-2422" not in markdown
    assert "https://jira.example.local/browse/BIP-2431" in markdown
    assert "https://github.com/example/tenant-success-portal/pull/322" in markdown


def test_build_pre_read_writes_configured_output(tmp_path) -> None:
    output_path = tmp_path / "standup-pre-read.md"
    config = Config(output_path=output_path)

    markdown = build_pre_read(config)

    assert output_path.read_text(encoding="utf-8") == markdown
    assert "# Standup Pre-Read: Tenant Success ART" in markdown
