from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SourceMode(StrEnum):
    SAMPLE_FILES = "sample_files"


@dataclass(frozen=True)
class Config:
    team_name: str = "Example Platform Team"
    jira_path: Path = Path("examples/jira-sample.json")
    github_path: Path = Path("examples/github-pr-sample.json")
    prior_standup_path: Path = Path("examples/prior-standup.md")
    source_mode: SourceMode = SourceMode.SAMPLE_FILES
    output_path: Path = Path("output/standup-pre-read.md")
    stale_pr_days: int = 5
