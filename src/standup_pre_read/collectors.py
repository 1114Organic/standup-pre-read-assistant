from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast


def load_jira_sample(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def load_github_pr_sample(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def load_jira_mcp_sample(path: Path) -> dict[str, Any]:
    """Load a local Jira MCP-style tool response and adapt it to sample issue data.

    This is intentionally file-only: it does not create an MCP client, open a
    network connection, or require credentials. The fixture may expose issue
    records either as top-level ``issues`` data or inside MCP ``content`` text
    payloads containing JSON.
    """
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    return jira_mcp_response_to_jira_sample(payload)


def jira_mcp_response_to_jira_sample(payload: dict[str, Any]) -> dict[str, Any]:
    issues = _extract_mcp_issues(payload)
    return {
        "team": payload.get("team") or payload.get("metadata", {}).get("team"),
        "issues": [_mcp_issue_to_sample_issue(issue) for issue in issues],
    }


def _extract_mcp_issues(payload: dict[str, Any]) -> list[dict[str, Any]]:
    direct = payload.get("issues")
    if isinstance(direct, list):
        return [issue for issue in direct if isinstance(issue, dict)]

    tool_result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    content = tool_result.get("content", []) if isinstance(tool_result, dict) else []
    for item in content:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("json"), dict) and isinstance(item["json"].get("issues"), list):
            return [issue for issue in item["json"]["issues"] if isinstance(issue, dict)]
        text = item.get("text")
        if not isinstance(text, str):
            continue
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict) and isinstance(decoded.get("issues"), list):
            return [issue for issue in decoded["issues"] if isinstance(issue, dict)]
    return []


def _field_value(fields: dict[str, Any], key: str) -> Any:
    value = fields.get(key)
    if isinstance(value, dict):
        return value.get("displayName") or value.get("name") or value.get("value")
    return value


def _mcp_issue_to_sample_issue(issue: dict[str, Any]) -> dict[str, Any]:
    raw_fields = issue.get("fields")
    fields: dict[str, Any] = cast(dict[str, Any], raw_fields) if isinstance(raw_fields, dict) else {}
    status = _field_value(fields, "status") or issue.get("status") or "Unknown"
    assignee = _field_value(fields, "assignee") or issue.get("assignee")
    blocked_reason = issue.get("blocked_reason") or fields.get("blocked_reason")
    decision_needed = issue.get("decision_needed") or fields.get("decision_needed")
    key = str(issue.get("key") or issue.get("id") or "MCP-UNKNOWN")
    return {
        "key": key,
        "title": issue.get("title") or fields.get("summary") or key,
        "status": status,
        "assignee": assignee,
        "updated": issue.get("updated") or fields.get("updated"),
        "sprint": issue.get("sprint") or _field_value(fields, "project"),
        "url": issue.get("url") or issue.get("self"),
        "summary": issue.get("summary") or fields.get("description") or fields.get("summary") or "",
        "blocker": bool(issue.get("blocker") or blocked_reason or str(status).lower() == "blocked"),
        "blocked_reason": blocked_reason,
        "decision_needed": decision_needed,
    }


def load_prior_standup(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_chat_sample(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"channels": []}
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


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
