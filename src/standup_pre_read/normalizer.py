from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from .collectors import extract_prior_items
from .models import Activity, ActivityType


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def normalize_jira(data: dict[str, Any]) -> list[Activity]:
    team = data.get("team")
    activities: list[Activity] = []
    for issue in data.get("issues", []):
        activities.append(
            Activity(
                source_system="jira",
                source_id=issue["key"],
                source_url=issue.get("url"),
                title=issue.get("title", issue["key"]),
                description=issue.get("summary", ""),
                owner=issue.get("assignee"),
                team=team,
                project=issue.get("sprint"),
                activity_type="jira_issue",
                status=issue.get("status", "Unknown"),
                timestamp=parse_datetime(issue.get("updated")),
                related_work_items=(issue["key"],),
                blocker_signal=issue.get("blocked_reason") if issue.get("blocker") else None,
                decision_signal=issue.get("decision_needed"),
                confidence="high",
                updated_timestamp=parse_datetime(issue.get("updated")),
            )
        )
    return activities


def normalize_github(data: dict[str, Any]) -> list[Activity]:
    activities: list[Activity] = []
    for repo in data.get("repositories", []):
        repo_name = repo.get("name")
        for pr in repo.get("pull_requests", []):
            risk = "CI failing" if pr.get("ci_state") == "failing" else None
            status = "merged" if pr.get("merged") else pr.get("state", "unknown")
            activities.append(
                Activity(
                    source_system="github",
                    source_id=f"PR #{pr['number']}",
                    source_url=pr.get("url"),
                    title=pr.get("title", f"PR #{pr['number']}"),
                    description=pr.get("summary", ""),
                    owner=pr.get("author"),
                    team=None,
                    project=repo_name,
                    activity_type="github_pr",
                    status=status,
                    timestamp=parse_datetime(pr.get("created")),
                    related_work_items=tuple(pr.get("linked_issues", [])),
                    blocker_signal=None,
                    decision_signal=None,
                    risk_signal=risk,
                    confidence="high",
                    updated_timestamp=parse_datetime(pr.get("updated")),
                    ci_state=pr.get("ci_state"),
                    review_state=pr.get("review_state"),
                )
            )
    return activities


def normalize_prior(markdown: str) -> list[Activity]:
    activities: list[Activity] = []
    for item in extract_prior_items(markdown):
        signal = item["title"]
        activities.append(
            Activity(
                source_system="prior_standup",
                source_id=item["source_id"],
                source_url=None,
                title=item["title"],
                description=item["title"],
                owner=None,
                team=None,
                project=None,
                activity_type=cast(ActivityType, item["type"]),
                status=item["status"],
                timestamp=None,
                related_work_items=(item["source_id"],) if item["source_id"] != "prior-standup" else tuple(),
                blocker_signal=signal if item["type"] in {"prior_blocker", "prior_carryover"} else None,
                decision_signal=signal if item["type"] == "prior_decision" else None,
                confidence="medium",
            )
        )
    return activities


def normalize_all(jira_data: dict[str, Any], github_data: dict[str, Any], prior_markdown: str) -> list[Activity]:
    return [*normalize_jira(jira_data), *normalize_github(github_data), *normalize_prior(prior_markdown)]
