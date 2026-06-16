from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ActivityType = Literal["jira_issue", "github_pr", "prior_blocker", "prior_decision", "prior_carryover"]


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
