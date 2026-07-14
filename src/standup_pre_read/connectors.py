from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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


class ConnectorContractError(ValueError):
    """Raised when a connector returns a payload that cannot be normalized safely."""


class JiraMcpRuntimeUnavailableError(RuntimeError):
    """Raised when real Jira MCP mode is selected without an approved runtime adapter."""


class SourceConnector(Protocol):
    def load(self) -> SourceData:
        """Load source data without normalizing or generating output."""


@dataclass(frozen=True)
class SampleSourceConnector:
    config: Config

    def load(self) -> SourceData:
        source_data = SourceData(
            jira_data=load_jira_sample(self.config.jira_path),
            github_data=load_github_pr_sample(self.config.github_path),
            prior_markdown=load_prior_standup(self.config.prior_standup_path),
            chat_data=load_chat_sample(self.config.chat_path),
        )
        validate_source_data(source_data)
        return source_data


@dataclass(frozen=True)
class JiraMcpSampleSourceConnector:
    config: Config

    def load(self) -> SourceData:
        source_data = SourceData(
            jira_data=load_jira_mcp_sample(self.config.jira_mcp_path),
            github_data=load_github_pr_sample(self.config.github_path),
            prior_markdown=load_prior_standup(self.config.prior_standup_path),
            chat_data=load_chat_sample(self.config.chat_path),
        )
        validate_source_data(source_data)
        return source_data


@dataclass(frozen=True)
class JiraMcpConnector:
    """Boundary for a future approved real Jira MCP client.

    Contract: execute a read-only Jira search against ``config.jira_mcp_server_name``
    using either ``config.jira_jql`` or ``config.jira_project_keys``, honor
    ``config.jira_include_comments`` and ``config.jira_max_results``, adapt the
    MCP tool result into the local Jira issue shape, and return a validated
    ``SourceData`` with local GitHub/prior/chat inputs. Credentials must come
    from the approved MCP runtime, never from repository code or config files.
    """

    config: Config

    def load(self) -> SourceData:
        if not self.config.allow_live_connectors:
            raise JiraMcpRuntimeUnavailableError(
                "jira_mcp source mode is disabled by default: security.allow_live_connectors "
                "is false. Real Jira MCP execution requires an approved work environment, "
                "an externally configured MCP server, and credentials supplied outside this "
                "repository. No credentials, network calls, or Jira requests were attempted."
            )
        if not self.config.jira_enabled:
            raise JiraMcpRuntimeUnavailableError(
                "jira_mcp source mode is disabled by config: sources.jira.enabled is false."
            )
        raise JiraMcpRuntimeUnavailableError(
            "jira_mcp source mode requires an approved MCP runtime and configured "
            "sources.jira.mcp_server_name. This repository provides only the safe "
            "adapter boundary; use jira_mcp_sample for local tests. No credentials, "
            "network calls, or Jira requests were attempted."
        )


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_timestamp(value: Any, path: str, errors: list[str]) -> None:
    if value in (None, ""):
        return
    if not isinstance(value, str):
        errors.append(f"{path} must be an ISO-8601 timestamp string when provided")
        return
    normalized = value.removesuffix("Z") + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        errors.append(f"{path} must be a valid ISO-8601 timestamp")


def validate_source_data(source_data: SourceData) -> None:
    """Validate the lightweight connector contract before normalization.

    The contract intentionally checks only the envelope and fields that the
    current normalizers require. It is meant to catch malformed connector output
    early without turning local sample adapters into a full schema framework.
    """
    errors: list[str] = []
    jira_data: Any = source_data.jira_data
    github_data: Any = source_data.github_data
    prior_markdown: Any = source_data.prior_markdown
    chat_data: Any = source_data.chat_data

    if not isinstance(jira_data, dict):
        errors.append("jira_data must be a dictionary")
    else:
        issues = jira_data.get("issues")
        if not isinstance(issues, list) or not issues:
            errors.append("jira_data.issues must be a non-empty list")
        else:
            for index, issue in enumerate(issues):
                path = f"jira_data.issues[{index}]"
                if not isinstance(issue, dict):
                    errors.append(f"{path} must be a dictionary")
                    continue
                for field in ("key", "status"):
                    if not _is_non_empty_string(issue.get(field)):
                        errors.append(f"{path}.{field} is required and must be a non-empty string")
                _validate_timestamp(issue.get("updated"), f"{path}.updated", errors)

    if not isinstance(github_data, dict):
        errors.append("github_data must be a dictionary")
    else:
        repositories = github_data.get("repositories")
        if not isinstance(repositories, list):
            errors.append("github_data.repositories must be a list")
        else:
            for repo_index, repo in enumerate(repositories):
                repo_path = f"github_data.repositories[{repo_index}]"
                if not isinstance(repo, dict):
                    errors.append(f"{repo_path} must be a dictionary")
                    continue
                if not _is_non_empty_string(repo.get("name")):
                    errors.append(f"{repo_path}.name is required and must be a non-empty string")
                pull_requests = repo.get("pull_requests")
                if not isinstance(pull_requests, list):
                    errors.append(f"{repo_path}.pull_requests must be a list")
                    continue
                for pr_index, pr in enumerate(pull_requests):
                    pr_path = f"{repo_path}.pull_requests[{pr_index}]"
                    if not isinstance(pr, dict):
                        errors.append(f"{pr_path} must be a dictionary")
                        continue
                    if pr.get("number") in (None, ""):
                        errors.append(f"{pr_path}.number is required")
                    for field in ("title", "state"):
                        if not _is_non_empty_string(pr.get(field)):
                            errors.append(f"{pr_path}.{field} is required and must be a non-empty string")
                    _validate_timestamp(pr.get("created"), f"{pr_path}.created", errors)
                    _validate_timestamp(pr.get("updated"), f"{pr_path}.updated", errors)

    if not isinstance(prior_markdown, str):
        errors.append("prior_markdown must be a string")

    if not isinstance(chat_data, dict):
        errors.append("chat_data must be a dictionary")
    else:
        channels = chat_data.get("channels")
        if not isinstance(channels, list):
            errors.append("chat_data.channels must be a list")
        else:
            for channel_index, channel in enumerate(channels):
                channel_path = f"chat_data.channels[{channel_index}]"
                if not isinstance(channel, dict):
                    errors.append(f"{channel_path} must be a dictionary")
                    continue
                messages = channel.get("messages", [])
                if not isinstance(messages, list):
                    errors.append(f"{channel_path}.messages must be a list when provided")
                    continue
                for message_index, message in enumerate(messages):
                    message_path = f"{channel_path}.messages[{message_index}]"
                    if not isinstance(message, dict):
                        errors.append(f"{message_path} must be a dictionary")
                        continue
                    if not _is_non_empty_string(message.get("id")):
                        errors.append(f"{message_path}.id is required and must be a non-empty string")
                    if not _is_non_empty_string(message.get("text")):
                        errors.append(f"{message_path}.text is required and must be a non-empty string")
                    _validate_timestamp(message.get("timestamp"), f"{message_path}.timestamp", errors)

    if errors:
        joined = "; ".join(errors)
        raise ConnectorContractError(f"Connector payload failed validation: {joined}")


def source_connector_for(config: Config) -> SourceConnector:
    if config.source_mode == "sample":
        return SampleSourceConnector(config)
    if config.source_mode == "jira_mcp_sample":
        return JiraMcpSampleSourceConnector(config)
    if config.source_mode == "jira_mcp":
        return JiraMcpConnector(config)
    supported = "sample, jira_mcp_sample, jira_mcp"
    raise ValueError(f"Unsupported source_mode '{config.source_mode}'. Supported modes: {supported}.")
