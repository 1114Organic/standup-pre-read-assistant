from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import Config, SourceMode


@dataclass(frozen=True)
class SourcePayload:
    """Raw source inputs collected for one pre-read generation run."""

    jira: dict[str, Any]
    github: dict[str, Any]
    prior_standup: str


class SourceConnector(Protocol):
    """Collects all raw inputs needed by the normalizer."""

    def collect(self) -> SourcePayload:
        """Return raw Jira, GitHub, and prior-standup source data."""
        ...


@dataclass(frozen=True)
class FileSourceConnector:
    """Source connector backed by configured local sample files."""

    jira_path: Path
    github_path: Path
    prior_standup_path: Path

    @classmethod
    def from_config(cls, config: Config) -> "FileSourceConnector":
        return cls(
            jira_path=config.jira_path,
            github_path=config.github_path,
            prior_standup_path=config.prior_standup_path,
        )

    def collect(self) -> SourcePayload:
        return SourcePayload(
            jira=load_jira_sample(self.jira_path),
            github=load_github_pr_sample(self.github_path),
            prior_standup=load_prior_standup(self.prior_standup_path),
        )


def connector_from_config(config: Config) -> SourceConnector:
    """Build the source connector selected by configuration."""
    if config.source_mode == SourceMode.SAMPLE_FILES:
        return FileSourceConnector.from_config(config)
    raise ValueError(f"Unsupported source mode: {config.source_mode.value}")


def load_jira_sample(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_github_pr_sample(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_prior_standup(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_prior_items(markdown: str) -> list[dict[str, str]]:
    """Extract unresolved/open prior blocker, decision, and carryover bullets."""
    items: list[dict[str, str]] = []
    current_section = ""
    section_map = {
        "Blockers Needing Action": "prior_blocker",
        "Decisions Needed": "prior_decision",
        "Carryover From Yesterday": "prior_carryover",
    }

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            current_section = line.removeprefix("## ").strip()
            continue
        if not line.startswith("- ") or current_section not in section_map:
            continue

        text = line.removeprefix("- ").strip()
        status_match = re.search(r"\bStatus:\s*([A-Za-z -]+)\.?$", text)
        status = status_match.group(1).strip().lower() if status_match else "needs confirmation"
        if status in {"resolved", "closed", "done"}:
            continue
        clean_text = re.sub(r"\s*Status:\s*[A-Za-z -]+\.?$", "", text).strip()
        source_match = re.search(r"\b([A-Z]+-\d+)\b", clean_text)
        items.append(
            {
                "type": section_map[current_section],
                "source_id": source_match.group(1) if source_match else "prior-standup",
                "title": clean_text,
                "status": status,
            }
        )
    return items
