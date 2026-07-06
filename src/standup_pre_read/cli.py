from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from .config import Config
from .connectors import source_connector_for
from .generator import generate_pre_read_document, render_pre_read_markdown
from .normalizer import normalize_all


def build_pre_read(config: Config | None = None) -> str:
    config = config or Config()
    source_data = source_connector_for(config).load()
    activities = normalize_all(
        source_data.jira_data, source_data.github_data, source_data.prior_markdown, source_data.chat_data
    )
    document = generate_pre_read_document(
        activities,
        config.team_name,
        config.stale_pr_days,
        source_mode=config.source_mode,
        review_status=config.review_status,
        reviewer=config.reviewer,
        review_notes=config.review_notes,
    )
    markdown = render_pre_read_markdown(document)
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_path.write_text(markdown, encoding="utf-8")
    if config.review_status == "approved" and config.approved_output_path is not None:
        config.approved_output_path.parent.mkdir(parents=True, exist_ok=True)
        config.approved_output_path.write_text(markdown, encoding="utf-8")
    if config.json_output_path is not None:
        config.json_output_path.parent.mkdir(parents=True, exist_ok=True)
        config.json_output_path.write_text(
            json.dumps(document.to_json_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return markdown


def parse_args(argv: Sequence[str] | None = None) -> Config:
    parser = argparse.ArgumentParser(description="Generate a standup pre-read markdown draft.")
    parser.add_argument(
        "--source-mode",
        default=Config.source_mode,
        help="Source connector mode to use. Currently supported: sample.",
    )
    parser.add_argument(
        "--jira-path",
        type=Path,
        default=Config.jira_path,
        help="Path to the sample Jira JSON file.",
    )
    parser.add_argument(
        "--github-path",
        type=Path,
        default=Config.github_path,
        help="Path to the sample GitHub pull request JSON file.",
    )
    parser.add_argument(
        "--prior-standup-path",
        type=Path,
        default=Config.prior_standup_path,
        help="Path to the prior standup markdown file.",
    )
    parser.add_argument(
        "--chat-path",
        type=Path,
        default=Config.chat_path,
        help="Optional path to a sample chat JSON file.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Config.output_path,
        help="Path where the generated markdown pre-read should be written.",
    )
    parser.add_argument(
        "--json-output-path",
        type=Path,
        default=Config.json_output_path,
        help="Optional path where a structured JSON version of the pre-read should be written.",
    )
    parser.add_argument(
        "--review-status",
        choices=("draft", "approved", "rejected"),
        default=Config.review_status,
        help="Local facilitator review status to attach to the generated pre-read.",
    )
    parser.add_argument(
        "--reviewer",
        default=Config.reviewer,
        help="Optional facilitator name or identifier for reviewed pre-reads.",
    )
    parser.add_argument(
        "--review-notes",
        default=Config.review_notes,
        help="Optional local review notes to include in markdown and JSON output.",
    )
    parser.add_argument(
        "--approved-output-path",
        type=Path,
        default=Config.approved_output_path,
        help="Optional path for an approved markdown copy; written only with --review-status approved.",
    )
    args = parser.parse_args(argv)
    return Config(
        source_mode=args.source_mode,
        jira_path=args.jira_path,
        github_path=args.github_path,
        prior_standup_path=args.prior_standup_path,
        chat_path=args.chat_path,
        output_path=args.output_path,
        json_output_path=args.json_output_path,
        review_status=args.review_status,
        reviewer=args.reviewer,
        review_notes=args.review_notes,
        approved_output_path=args.approved_output_path,
    )


def main(argv: Sequence[str] | None = None) -> None:
    config = parse_args(argv)
    try:
        build_pre_read(config)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(f"Wrote {config.output_path}")
    if config.json_output_path is not None:
        print(f"Wrote {config.json_output_path}")
    if config.review_status == "approved" and config.approved_output_path is not None:
        print(f"Wrote {config.approved_output_path}")


if __name__ == "__main__":
    main()
