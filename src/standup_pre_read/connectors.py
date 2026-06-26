from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .collectors import load_github_pr_sample, load_jira_sample, load_prior_standup
from .config import Config


@dataclass(frozen=True)
class SourceData:
    jira_data: dict[str, Any]
    github_data: dict[str, Any]
    prior_markdown: str


class SourceConnector(Protocol):
    def load(self) -> SourceData:
        """Load source data without normalizing or generating output."""


@dataclass(frozen=True)
class SampleSourceConnector:
    config: Config

    def load(self) -> SourceData:
        return SourceData(
            jira_data=load_jira_sample(self.config.jira_path),
            github_data=load_github_pr_sample(self.config.github_path),
            prior_markdown=load_prior_standup(self.config.prior_standup_path),
        )


def source_connector_for(config: Config) -> SourceConnector:
    if config.source_mode == "sample":
        return SampleSourceConnector(config)
    supported = "sample"
    raise ValueError(f"Unsupported source_mode '{config.source_mode}'. Supported modes: {supported}.")
