from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from standup_pre_read.evaluation import SCENARIOS, render_markdown_report, run_evaluation, validate_scenario


def test_evaluation_defines_expected_scenarios() -> None:
    assert [scenario.name for scenario in SCENARIOS] == [
        "default_sample",
        "rich_sample",
        "rich_chat_sample",
        "jira_mcp_sample",
    ]
    assert all(scenario.config.json_output_path is not None for scenario in SCENARIOS)
    jira_mcp = next(scenario for scenario in SCENARIOS if scenario.name == "jira_mcp_sample")
    assert jira_mcp.config.source_mode == "jira_mcp_sample"


def test_validate_scenario_reports_missing_required_checks(tmp_path: Path) -> None:
    base = SCENARIOS[0]
    scenario = replace(
        base,
        config=replace(
            base.config,
            output_path=tmp_path / "missing.md",
            json_output_path=tmp_path / "missing.json",
        ),
    )
    payload = {
        "blockers": [{"text": "Blocked", "source_refs": [scenario.expected_blocker_ref]}],
        "decisions": [{"text": "Decision", "source_refs": [scenario.expected_decision_ref]}],
        "carryover": [{"text": scenario.expected_carryover_text, "source_refs": ["DEMO-103"]}],
        "source_references": [],
        "review_status": "approved",
    }

    failures = validate_scenario(scenario, "# incomplete", payload)

    assert "markdown output file was not written" in failures
    assert any(failure.startswith("missing markdown section") for failure in failures)
    assert "JSON source references are empty" in failures
    assert "one or more JSON items are missing priority" in failures
    assert "JSON review_status is not draft" in failures


def test_run_evaluation_writes_markdown_and_json_reports(tmp_path: Path) -> None:
    markdown_report_path = tmp_path / "evaluation-report.md"
    json_report_path = tmp_path / "evaluation-report.json"

    report = run_evaluation(markdown_report_path, json_report_path)

    assert report["passed"] is True
    assert report["scenario_count"] == 4
    assert markdown_report_path.exists()
    assert json_report_path.exists()
    assert json.loads(json_report_path.read_text(encoding="utf-8")) == report
    assert "## default_sample" in markdown_report_path.read_text(encoding="utf-8")


def test_render_markdown_report_includes_failures() -> None:
    markdown = render_markdown_report(
        {
            "evaluation_scope": "test scope",
            "passed": False,
            "scenarios": [
                {
                    "name": "scenario",
                    "description": "description",
                    "passed": False,
                    "failures": ["missing section"],
                    "markdown_output_path": "out.md",
                    "json_output_path": "out.json",
                }
            ],
        }
    )

    assert "Overall status: FAIL" in markdown
    assert "- missing section" in markdown
