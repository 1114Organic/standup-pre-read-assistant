from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .collectors import (
    load_chat_sample,
    load_github_pr_sample,
    load_jira_mcp_sample,
    load_jira_sample,
    load_prior_standup,
)
from .config import Config


@dataclass(frozen=True)
class SourceData:
    jira_data: dict[str, Any]
    github_data: dict[str, Any]
    prior_markdown: str
    chat_data: dict[str, Any]


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
            chat_data=load_chat_sample(self.config.chat_path),
        )


@dataclass(frozen=True)
class JiraMcpSampleSourceConnector:
    config: Config

    def load(self) -> SourceData:
        return SourceData(
            jira_data=load_jira_mcp_sample(self.config.jira_mcp_path),
            github_data=load_github_pr_sample(self.config.github_path),
            prior_markdown=load_prior_standup(self.config.prior_standup_path),
            chat_data=load_chat_sample(self.config.chat_path),
        )


def source_connector_for(config: Config) -> SourceConnector:
    if config.source_mode == "sample":
        return SampleSourceConnector(config)
    if config.source_mode == "jira_mcp_sample":
        return JiraMcpSampleSourceConnector(config)
    supported = "sample, jira_mcp_sample"
    raise ValueError(f"Unsupported source_mode '{config.source_mode}'. Supported modes: {supported}.")
