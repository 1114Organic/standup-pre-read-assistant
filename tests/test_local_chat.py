from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from standup_pre_read.cli import parse_args
from standup_pre_read.collectors import LocalChatFileCollector
from standup_pre_read.config import load_config_file

EXPORT = """STANDUP EXPORT - Thursday, September 03, 2026
CHANNEL: #alpha
[7:43 AM] Person (they/them):
Blocked on APP-12 in PR #45.
More context on another line.
Thread replies:
[8:01 AM] Another Person:
Follow up: reviewing https://github.com/acme/app/pull/46
CHANNEL: #beta
[9:05 PM] Third Person:
Decision needed: should we ship APP-13?
"""


def write_export(path: Path, text: str = EXPORT) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_collector_parses_multiple_channels_and_multiline_messages(tmp_path: Path) -> None:
    result = LocalChatFileCollector(write_export(tmp_path / "export.txt"), lookback_hours=48).collect()
    assert [channel["name"] for channel in result["channels"]] == ["alpha", "beta"]
    assert result["channels"][0]["messages"][0]["text"].endswith("More context on another line.")


def test_collector_preserves_parenthetical_author_text(tmp_path: Path) -> None:
    result = LocalChatFileCollector(write_export(tmp_path / "export.txt"), lookback_hours=48).collect()
    assert result["channels"][0]["messages"][0]["author"] == "Person (they/them)"


def test_collector_assigns_thread_parent(tmp_path: Path) -> None:
    result = LocalChatFileCollector(write_export(tmp_path / "export.txt"), lookback_hours=48).collect()
    parent, reply = result["channels"][0]["messages"]
    assert reply["thread_parent_id"] == parent["id"]


def test_collector_extracts_jira_and_pull_request_references(tmp_path: Path) -> None:
    result = LocalChatFileCollector(write_export(tmp_path / "export.txt"), lookback_hours=48).collect()
    parent, reply = result["channels"][0]["messages"]
    assert parent["related_work_items"] == ["APP-12", "PR #45"]
    assert reply["related_work_items"] == ["PR #46"]


def test_collector_ids_are_deterministic_across_paths(tmp_path: Path) -> None:
    first = LocalChatFileCollector(write_export(tmp_path / "one.txt"), lookback_hours=48).collect()
    second = LocalChatFileCollector(write_export(tmp_path / "two.txt"), lookback_hours=48).collect()
    assert first["channels"][0]["messages"][0]["id"] == second["channels"][0]["messages"][0]["id"]


def test_collector_uses_configured_timezone(tmp_path: Path) -> None:
    result = LocalChatFileCollector(
        write_export(tmp_path / "export.txt"), timezone="America/New_York", lookback_hours=48
    ).collect()
    assert result["channels"][0]["messages"][0]["timestamp"].endswith("-04:00")


def test_collector_selects_latest_valid_export_in_directory(tmp_path: Path) -> None:
    write_export(tmp_path / "new.txt")
    write_export(tmp_path / "old.txt", EXPORT.replace("September 03", "September 02").replace("Thursday", "Wednesday"))
    (tmp_path / "notes.txt").write_text("not an export", encoding="utf-8")
    assert LocalChatFileCollector(tmp_path, lookback_hours=48).collect()["source_file"].endswith("new.txt")


def test_collector_excludes_messages_outside_lookback(tmp_path: Path) -> None:
    result = LocalChatFileCollector(
        write_export(tmp_path / "export.txt"),
        lookback_hours=1,
        now=datetime(2026, 9, 3, 9, 0, tzinfo=ZoneInfo("Etc/UTC")),
    ).collect()
    assert [channel["name"] for channel in result["channels"]] == ["alpha", "beta"]
    assert len(result["channels"][0]["messages"]) == 1


def test_collector_rejects_non_export_text_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No matching Slackbot"):
        LocalChatFileCollector(write_export(tmp_path / "bad.txt", "hello\n")).collect()


def test_local_chat_config_and_validation_flag() -> None:
    config = load_config_file(Path("config/local-chat-demo.yaml"))
    assert config.chat_path == Path("examples/local-chat-export.txt")
    assert parse_args(["--config", "config/local-chat-demo.yaml", "--validate-chat"]).validate_chat is True
