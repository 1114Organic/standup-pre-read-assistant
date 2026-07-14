from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, cast


@dataclass(frozen=True)
class Config:
    team_name: str = "Example Platform Team"
    source_mode: str = "sample"
    jira_path: Path = Path("examples/jira-sample.json")
    jira_mcp_path: Path = Path("examples/jira-mcp-sample-response.json")
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
    jira_enabled: bool = True
    jira_mcp_server_name: str | None = None
    jira_jql: str | None = None
    jira_project_keys: tuple[str, ...] = ()
    jira_include_comments: bool = False
    jira_max_results: int = 50
    allow_live_connectors: bool = False


def _optional_path(value: Any) -> Path | None:
    if value in (None, ""):
        return None
    if isinstance(value, Path):
        return value
    if isinstance(value, str):
        return Path(value)
    raise ValueError(f"Expected path value to be a string, got {type(value).__name__}.")


def _string_value(value: Any, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"Expected {field_name} to be a string, got {type(value).__name__}.")


def _bool_value(value: Any, field_name: str) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    raise ValueError(f"Expected {field_name} to be a boolean, got {type(value).__name__}.")


def _int_value(value: Any, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, int):
        return value
    raise ValueError(f"Expected {field_name} to be an integer, got {type(value).__name__}.")


def _string_tuple(value: Any, field_name: str) -> tuple[str, ...] | None:
    if value in (None, ""):
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{field_name} must be a list of non-empty strings when provided.")
    return tuple(value)


def _review_status(value: Any) -> Literal["draft", "approved", "rejected"] | None:
    if value in (None, ""):
        return None
    if value in ("draft", "approved", "rejected"):
        return cast(Literal["draft", "approved", "rejected"], value)
    raise ValueError("review.default_status must be one of: draft, approved, rejected.")


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"", "null", "~"}:
        return None
    if value.startswith("\"") and value.endswith("\""):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    try:
        return int(value)
    except ValueError:
        return value


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by the example team config."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any] | list[Any]]] = [(-1, root)]
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]

    for index, raw_line in enumerate(lines):
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("Config list item appeared outside a list.")
            parent.append(_parse_scalar(line[2:]))
            continue

        if ":" not in line:
            raise ValueError(f"Unsupported config line: {line}")
        if not isinstance(parent, dict):
            raise ValueError("Config mapping entry appeared inside a scalar list.")

        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value:
            parent[key] = _parse_scalar(value)
            continue

        next_container: dict[str, Any] | list[Any] = {}
        if index + 1 < len(lines):
            next_line = lines[index + 1]
            next_indent = len(next_line) - len(next_line.lstrip(" "))
            if next_indent > indent and next_line.strip().startswith("- "):
                next_container = []
        parent[key] = next_container
        stack.append((indent, next_container))
    return root


def load_config_file(path: Path) -> Config:
    """Load supported CLI configuration values from a sanitized YAML file."""
    loaded = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Config file must contain a YAML mapping at the top level.")

    team = loaded.get("team", {})
    sources = loaded.get("sources", {})
    outputs = loaded.get("outputs", {})
    review = loaded.get("review", {})
    security = loaded.get("security", {})
    sections_are_mappings = all(isinstance(section, dict) for section in (team, sources, outputs, review, security))
    if not sections_are_mappings:
        raise ValueError(
            "Config sections team, sources, outputs, review, and security must be YAML mappings when provided."
        )

    jira = sources.get("jira", {})
    github = sources.get("github", {})
    chat = sources.get("chat", {})
    if not isinstance(jira, dict) or not isinstance(github, dict) or not isinstance(chat, dict):
        raise ValueError("Config source sections jira, github, and chat must be YAML mappings when provided.")

    config = Config()
    updates: dict[str, Any] = {}

    team_name = _string_value(team.get("name"), "team.name")
    if team_name is not None:
        updates["team_name"] = team_name

    jira_enabled = _bool_value(jira.get("enabled"), "sources.jira.enabled")
    if jira_enabled is not None:
        updates["jira_enabled"] = jira_enabled

    jira_mode = _string_value(jira.get("mode"), "sources.jira.mode")
    github_mode = _string_value(github.get("mode"), "sources.github.mode")
    if jira_mode is not None:
        if jira_mode not in {"sample", "jira_mcp_sample", "jira_mcp"}:
            raise ValueError("sources.jira.mode must be one of: sample, jira_mcp_sample, jira_mcp.")
        updates["source_mode"] = jira_mode
    elif github_mode == "sample":
        updates["source_mode"] = "sample"

    jira_mcp_server_name = _string_value(jira.get("mcp_server_name"), "sources.jira.mcp_server_name")
    if jira_mcp_server_name is not None:
        updates["jira_mcp_server_name"] = jira_mcp_server_name
    jira_jql = _string_value(jira.get("jql"), "sources.jira.jql")
    if jira_jql is not None:
        updates["jira_jql"] = jira_jql
    jira_project_keys = _string_tuple(jira.get("project_keys"), "sources.jira.project_keys")
    if jira_project_keys is not None:
        updates["jira_project_keys"] = jira_project_keys
    jira_include_comments = _bool_value(jira.get("include_comments"), "sources.jira.include_comments")
    if jira_include_comments is not None:
        updates["jira_include_comments"] = jira_include_comments
    jira_max_results = _int_value(jira.get("max_results"), "sources.jira.max_results")
    if jira_max_results is not None:
        updates["jira_max_results"] = jira_max_results

    allow_live_connectors = _bool_value(security.get("allow_live_connectors"), "security.allow_live_connectors")
    if allow_live_connectors is not None:
        updates["allow_live_connectors"] = allow_live_connectors

    output_path = _optional_path(outputs.get("markdown_path"))
    if output_path is not None:
        updates["output_path"] = output_path
    json_output_path = _optional_path(outputs.get("json_path"))
    if json_output_path is not None:
        updates["json_output_path"] = json_output_path
    approved_output_path = _optional_path(outputs.get("approved_output_path"))
    if approved_output_path is not None:
        updates["approved_output_path"] = approved_output_path

    status = _review_status(review.get("default_status"))
    if status is not None:
        updates["review_status"] = status
    reviewer = _string_value(review.get("reviewer"), "review.reviewer")
    if reviewer is not None:
        updates["reviewer"] = reviewer

    stale_pr_days = github.get("stale_pr_days")
    if stale_pr_days is not None:
        if not isinstance(stale_pr_days, int):
            raise ValueError("sources.github.stale_pr_days must be an integer when provided.")
        updates["stale_pr_days"] = stale_pr_days

    chat_enabled = chat.get("enabled")
    if chat_enabled is False:
        updates["chat_path"] = None

    return replace(config, **updates)
