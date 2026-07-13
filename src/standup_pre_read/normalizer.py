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
            risk_signals = []
            if pr.get("ci_state") == "failing":
                risk_signals.append("CI failing")
            if pr.get("merge_state") == "blocked":
                risk_signals.append("merge blocked")
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
                    decision_signal=pr.get("decision_needed") or (
                        pr.get("summary") if pr.get("merge_state") == "waiting_on_decision" else None
                    ),
                    risk_signal=", ".join(risk_signals) if risk_signals else None,
                    confidence="high",
                    updated_timestamp=parse_datetime(pr.get("updated")),
                    ci_state=pr.get("ci_state"),
                    review_state=pr.get("review_state"),
                    merge_state=pr.get("merge_state"),
                    stale_days=pr.get("stale_days") or pr.get("age_days"),
                    reviewers=tuple(pr.get("reviewers", [])),
                    approvals=tuple(pr.get("approvals", [])),
                    requested_changes=tuple(pr.get("requested_changes", [])),
                    draft=pr.get("draft"),
                )
            )
    return activities


def _chat_activity_type(text: str) -> ActivityType | None:
    lowered = text.lower()
    if any(term in lowered for term in ("blocked", "blocker", "stuck", "cannot continue", "can't continue")):
        return "chat_blocker"
    if any(term in lowered for term in ("decision needed", "decide", "should we", "need a decision")):
        return "chat_decision"
    if any(term in lowered for term in ("follow up", "follow-up", "action item", "todo", "next step")):
        return "chat_follow_up"
    if any(term in lowered for term in ("who owns", "unclear who", "owner?", "ownership")):
        return "chat_signal"
    return None


def normalize_chat(data: dict[str, Any]) -> list[Activity]:
    activities: list[Activity] = []
    workspace = data.get("workspace")
    for channel in data.get("channels", []):
        channel_name = channel.get("name")
        for message in channel.get("messages", []):
            text = message.get("text", "").strip()
            activity_type = _chat_activity_type(text)
            if not text or activity_type is None:
                continue
            related = tuple(message.get("related_work_items", []))
            source_id = message.get("id", "chat-message")
            is_blocker = activity_type == "chat_blocker"
            is_decision = activity_type == "chat_decision"
            activities.append(
                Activity(
                    source_system="chat",
                    source_id=source_id,
                    source_url=message.get("url"),
                    title=text,
                    description=text,
                    owner=message.get("author"),
                    team=workspace,
                    project=channel_name,
                    activity_type=activity_type,
                    status="open",
                    timestamp=parse_datetime(message.get("timestamp")),
                    related_work_items=related,
                    blocker_signal=text if is_blocker else None,
                    decision_signal=text if is_decision else None,
                    risk_signal=text if activity_type == "chat_signal" else None,
                    confidence="medium",
                    updated_timestamp=parse_datetime(message.get("timestamp")),
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


def normalize_all(
    jira_data: dict[str, Any],
    github_data: dict[str, Any],
    prior_markdown: str,
    chat_data: dict[str, Any] | None = None,
) -> list[Activity]:
    return [
        *normalize_jira(jira_data),
        *normalize_github(github_data),
        *normalize_prior(prior_markdown),
        *normalize_chat(chat_data or {"channels": []}),
    ]
