from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ActivityType = Literal[
    "jira_issue",
    "github_pr",
    "prior_blocker",
    "prior_decision",
    "prior_carryover",
    "chat_blocker",
    "chat_decision",
    "chat_follow_up",
    "chat_signal",
]


@dataclass(frozen=True)
class Activity:
    source_system: str
    source_id: str
    source_url: str | None
    title: str
    description: str
    owner: str | None
    team: str | None
    project: str | None
    activity_type: ActivityType
    status: str
    timestamp: datetime | None
    related_work_items: tuple[str, ...] = field(default_factory=tuple)
    blocker_signal: str | None = None
    decision_signal: str | None = None
    risk_signal: str | None = None
    confidence: str = "high"
    updated_timestamp: datetime | None = None
    ci_state: str | None = None
    review_state: str | None = None
    merge_state: str | None = None
    stale_days: int | None = None
    reviewers: tuple[str, ...] = field(default_factory=tuple)
    approvals: tuple[str, ...] = field(default_factory=tuple)
    requested_changes: tuple[str, ...] = field(default_factory=tuple)
    draft: bool | None = None
