from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    team_name: str = "Example Platform Team"
    jira_path: Path = Path("examples/jira-sample.json")
    github_path: Path = Path("examples/github-pr-sample.json")
    prior_standup_path: Path = Path("examples/prior-standup.md")
    output_path: Path = Path("output/standup-pre-read.md")
    stale_pr_days: int = 5
