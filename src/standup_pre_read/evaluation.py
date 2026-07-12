from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cli import build_pre_read
from .config import Config

REQUIRED_MARKDOWN_SECTIONS = (
    "## Executive Summary",
    "## Progress Since Last Standup",
    "## Blockers Needing Action",
    "## Decisions Needed",
    "## Risks and Aging Work",
    "## Carryover From Yesterday",
    "## Suggested Standup Agenda",
    "## Suggested Standup Questions",
    "## Source References",
)

REPORT_MARKDOWN_PATH = Path("output/evaluation-report.md")
REPORT_JSON_PATH = Path("output/evaluation-report.json")


@dataclass(frozen=True)
class EvaluationScenario:
    name: str
    description: str
    config: Config
    expected_blocker_ref: str
    expected_decision_ref: str
    expected_carryover_text: str
    resolved_carryover_text: str


SCENARIOS = (
    EvaluationScenario(
        name="default_sample",
        description="Default sample Jira, GitHub, and prior standup data.",
        config=Config(
            output_path=Path("output/evaluation/default-sample.md"),
            json_output_path=Path("output/evaluation/default-sample.json"),
        ),
        expected_blocker_ref="DEMO-103",
        expected_decision_ref="DEMO-104",
        expected_carryover_text="Follow up with IAM approver for DEMO-103.",
        resolved_carryover_text="Verify DEMO-101 release notes are published.",
    ),
    EvaluationScenario(
        name="rich_sample",
        description="Richer generic sample data without chat messages.",
        config=Config(
            jira_path=Path("examples/jira-rich-sample.json"),
            github_path=Path("examples/github-pr-rich-sample.json"),
            prior_standup_path=Path("examples/prior-standup-rich.md"),
            output_path=Path("output/evaluation/rich-sample.md"),
            json_output_path=Path("output/evaluation/rich-sample.json"),
        ),
        expected_blocker_ref="SAMPLE-212",
        expected_decision_ref="SAMPLE-213",
        expected_carryover_text="Follow up on SAMPLE-212 credential approval.",
        resolved_carryover_text="Verify SAMPLE-210 checklist acceptance.",
    ),
    EvaluationScenario(
        name="rich_chat_sample",
        description="Richer generic sample data with local sample chat signals.",
        config=Config(
            jira_path=Path("examples/jira-rich-sample.json"),
            github_path=Path("examples/github-pr-rich-sample.json"),
            prior_standup_path=Path("examples/prior-standup-rich.md"),
            chat_path=Path("examples/chat-rich-sample.json"),
            output_path=Path("output/evaluation/rich-chat-sample.md"),
            json_output_path=Path("output/evaluation/rich-chat-sample.json"),
        ),
        expected_blocker_ref="chat-001",
        expected_decision_ref="chat-002",
        expected_carryover_text="Follow up with the release checklist owner for SAMPLE-214",
        resolved_carryover_text="Verify SAMPLE-210 checklist acceptance.",
    ),
    EvaluationScenario(
        name="jira_mcp_sample",
        description="Local mock Jira MCP-style sample response with sample GitHub and prior standup data.",
        config=Config(
            source_mode="jira_mcp_sample",
            jira_mcp_path=Path("examples/jira-mcp-sample-response.json"),
            output_path=Path("output/evaluation/jira-mcp-sample.md"),
            json_output_path=Path("output/evaluation/jira-mcp-sample.json"),
        ),
        expected_blocker_ref="MCP-103",
        expected_decision_ref="MCP-104",
        expected_carryover_text="Follow up with IAM approver for DEMO-103.",
        resolved_carryover_text="Verify DEMO-101 release notes are published.",
    ),
)


def _check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate_scenario(scenario: EvaluationScenario, markdown: str, payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    _check(scenario.config.output_path.exists(), "markdown output file was not written", failures)
    json_output_written = scenario.config.json_output_path is not None and scenario.config.json_output_path.exists()
    _check(json_output_written, "JSON output file was not written", failures)
    for section in REQUIRED_MARKDOWN_SECTIONS:
        _check(section in markdown, f"missing markdown section: {section}", failures)
    has_blocker = any(
        scenario.expected_blocker_ref in item.get("source_refs", []) for item in payload.get("blockers", [])
    )
    has_decision = any(
        scenario.expected_decision_ref in item.get("source_refs", []) for item in payload.get("decisions", [])
    )
    has_carryover = any(
        scenario.expected_carryover_text in item.get("text", "") for item in payload.get("carryover", [])
    )
    _check(has_blocker, "expected blocker was not present in JSON blockers", failures)
    _check(has_decision, "expected decision was not present in JSON decisions", failures)
    _check(has_carryover, "expected carryover was not present in JSON carryover", failures)
    _check(scenario.resolved_carryover_text not in markdown, "resolved carryover appeared in markdown", failures)
    validated_item_keys = ("progress", "blockers", "decisions", "risks", "carryover", "suggested_questions")
    all_items = [item for key in validated_item_keys for item in payload.get(key, [])]
    _check(
        all(item.get("source_refs") for item in all_items),
        "one or more JSON items are missing source references",
        failures,
    )
    _check(bool(payload.get("source_references")), "JSON source references are empty", failures)
    _check(all("priority" in item for item in all_items), "one or more JSON items are missing priority", failures)
    _check(payload.get("review_status") == "draft", "JSON review_status is not draft", failures)
    return failures


def run_evaluation(
    markdown_report_path: Path = REPORT_MARKDOWN_PATH,
    json_report_path: Path = REPORT_JSON_PATH,
) -> dict[str, Any]:
    results = []
    for scenario in SCENARIOS:
        markdown = build_pre_read(scenario.config)
        assert scenario.config.json_output_path is not None
        payload = json.loads(scenario.config.json_output_path.read_text(encoding="utf-8"))
        failures = validate_scenario(scenario, markdown, payload)
        results.append(
            {
                "name": scenario.name,
                "description": scenario.description,
                "passed": not failures,
                "failures": failures,
                "markdown_output_path": str(scenario.config.output_path),
                "json_output_path": str(scenario.config.json_output_path),
            }
        )
    report = {
        "evaluation_scope": "v0.2.0 sample evaluation harness",
        "passed": all(result["passed"] for result in results),
        "scenario_count": len(results),
        "scenarios": results,
    }
    markdown_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.parent.mkdir(parents=True, exist_ok=True)
    json_report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_report_path.write_text(render_markdown_report(report), encoding="utf-8")
    return report


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Evaluation Report",
        "",
        f"Scope: {report['evaluation_scope']}",
        "",
        f"Overall status: {'PASS' if report['passed'] else 'FAIL'}",
        "",
    ]
    for scenario in report["scenarios"]:
        lines.extend(
            [
                f"## {scenario['name']}",
                "",
                scenario["description"],
                "",
                f"Status: {'PASS' if scenario['passed'] else 'FAIL'}",
                f"Markdown output: `{scenario['markdown_output_path']}`",
                f"JSON output: `{scenario['json_output_path']}`",
                "",
            ]
        )
        if scenario["failures"]:
            lines.extend(f"- {failure}" for failure in scenario["failures"])
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    report = run_evaluation()
    if not report["passed"]:
        raise SystemExit(1)
    print(f"Wrote {REPORT_MARKDOWN_PATH}")
    print(f"Wrote {REPORT_JSON_PATH}")


if __name__ == "__main__":
    main()
