from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Config:
    team_name: str = "Example Platform Team"
    source_mode: str = "sample"
    jira_path: Path = Path("examples/jira-sample.json")
    github_path: Path = Path("examples/github-pr-sample.json")
    prior_standup_path: Path = Path("examples/prior-standup.md")
    chat_path: Path | None = None
    output_path: Path = Path("output/standup-pre-read.md")
    json_output_path: Path | None = None
    review_status: Literal["draft", "approved", "rejected"] = "draft"
    reviewer: str | None = None
    review_notes: str | None = None
    approved_output_path: Path | None = None
    stale_pr_days: int = 5
