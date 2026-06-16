from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


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
