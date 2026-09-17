from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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


_EXPORT_HEADER = re.compile(r"^STANDUP EXPORT - (?P<date>.+)$")
_CHANNEL_HEADER = re.compile(r"^CHANNEL:\s*#?(?P<channel>\S.*?)\s*$")
_MESSAGE_HEADER = re.compile(r"^\[(?P<time>\d{1,2}:\d{2}\s*(?:AM|PM))\]\s+(?P<author>.+):\s*$", re.IGNORECASE)
_JIRA_REFERENCE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
_PR_REFERENCE = re.compile(
    r"(?:github\.com/[^/\s]+/[^/\s]+/pull/|\bPR\s*#|\bpull request\s*#)(\d+)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class LocalChatFileCollector:
    """Read Slackbot standup exports from one explicitly configured local path."""

    path: Path
    timezone: str = "Etc/UTC"
    lookback_hours: int = 24
    now: datetime | None = None

    def _select_file(self) -> Path:
        if self.path.is_file():
            if self.path.suffix.lower() != ".txt":
                raise ValueError(f"Local chat export must be a .txt file: {self.path}")
            candidates = [self.path]
        elif self.path.is_dir():
            candidates = [item for item in self.path.iterdir() if item.is_file() and item.suffix.lower() == ".txt"]
        else:
            raise FileNotFoundError(f"Local chat export path does not exist: {self.path}")

        valid: list[tuple[datetime, Path]] = []
        for candidate in candidates:
            first_line = candidate.read_text(encoding="utf-8").splitlines()[:1]
            if not first_line:
                continue
            match = _EXPORT_HEADER.fullmatch(first_line[0].strip())
            if match:
                try:
                    export_date = datetime.strptime(match.group("date"), "%A, %B %d, %Y")
                except ValueError:
                    continue
                valid.append((export_date, candidate))
        if not valid:
            raise ValueError(f"No matching Slackbot standup export .txt files found in {self.path}")
        return max(valid, key=lambda item: (item[0], item[1].name))[1]

    def collect(self) -> dict[str, Any]:
        try:
            zone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown local chat timezone: {self.timezone}") from exc
        selected = self._select_file()
        lines = selected.read_text(encoding="utf-8").splitlines()
        header = _EXPORT_HEADER.fullmatch(lines[0].strip())
        if header is None:
            raise ValueError("Local chat export is missing its STANDUP EXPORT header.")
        export_date = datetime.strptime(header.group("date"), "%A, %B %d, %Y").date()
        cutoff_now = self.now
        if cutoff_now is not None and cutoff_now.tzinfo is None:
            cutoff_now = cutoff_now.replace(tzinfo=zone)

        channels: list[dict[str, Any]] = []
        current_channel: dict[str, Any] | None = None
        current_message: dict[str, Any] | None = None
        thread_parent_id: str | None = None

        def finish_message() -> None:
            nonlocal current_message
            if current_message is None or current_channel is None:
                return
            current_message["text"] = "\n".join(current_message.pop("_lines")).strip()
            content = "\x1f".join(
                (
                    current_channel["name"],
                    current_message["timestamp"],
                    current_message["author"],
                    current_message["text"],
                )
            )
            current_message["id"] = f"local-chat-{sha256(content.encode()).hexdigest()[:16]}"
            if current_message.pop("_thread", False) and thread_parent_id is not None:
                current_message["thread_parent_id"] = thread_parent_id
            related = sorted(set(_JIRA_REFERENCE.findall(current_message["text"])))
            related.extend(f"PR #{number}" for number in _PR_REFERENCE.findall(current_message["text"]))
            current_message["related_work_items"] = list(dict.fromkeys(related))
            timestamp = datetime.fromisoformat(current_message["timestamp"])
            if cutoff_now is None or timestamp >= cutoff_now.astimezone(zone) - timedelta(hours=self.lookback_hours):
                current_channel["messages"].append(current_message)
            current_message = None

        in_thread = False
        for raw_line in lines[1:]:
            channel_match = _CHANNEL_HEADER.fullmatch(raw_line.strip())
            if channel_match:
                finish_message()
                current_channel = {"name": channel_match.group("channel"), "messages": []}
                channels.append(current_channel)
                thread_parent_id = None
                in_thread = False
                continue
            if raw_line.strip() == "Thread replies:":
                finish_message()
                if current_channel and current_channel["messages"]:
                    thread_parent_id = current_channel["messages"][-1]["id"]
                in_thread = True
                continue
            message_match = _MESSAGE_HEADER.fullmatch(raw_line.strip())
            if message_match:
                finish_message()
                if current_channel is None:
                    raise ValueError("Local chat message appeared before a CHANNEL header.")
                parsed_time = datetime.strptime(message_match.group("time").upper(), "%I:%M %p").time()
                timestamp = datetime.combine(export_date, time(parsed_time.hour, parsed_time.minute), zone)
                current_message = {
                    "author": message_match.group("author").strip(),
                    "timestamp": timestamp.isoformat(),
                    "_lines": [],
                    "_thread": in_thread,
                }
                continue
            if current_message is not None:
                current_message["_lines"].append(raw_line)
            elif raw_line.strip():
                raise ValueError(f"Unrecognized local chat export line: {raw_line}")
        finish_message()
        if cutoff_now is None:
            timestamps = [
                datetime.fromisoformat(message["timestamp"])
                for channel in channels
                for message in channel["messages"]
            ]
            if timestamps:
                newest = max(timestamps)
                threshold = newest - timedelta(hours=self.lookback_hours)
                for channel in channels:
                    channel["messages"] = [
                        message
                        for message in channel["messages"]
                        if datetime.fromisoformat(message["timestamp"]) >= threshold
                    ]
        channels = [channel for channel in channels if channel["messages"]]
        return {"workspace": "Local Chat Export", "source_file": str(selected), "channels": channels}


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
