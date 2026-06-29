from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .config import Config
from .connectors import source_connector_for
from .generator import generate_pre_read
from .normalizer import normalize_all


def build_pre_read(config: Config | None = None) -> str:
    config = config or Config()
    source_data = source_connector_for(config).load()
    activities = normalize_all(source_data.jira_data, source_data.github_data, source_data.prior_markdown)
    markdown = generate_pre_read(activities, config.team_name, config.stale_pr_days)
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_path.write_text(markdown, encoding="utf-8")
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
        "--output-path",
        type=Path,
        default=Config.output_path,
        help="Path where the generated markdown pre-read should be written.",
    )
    args = parser.parse_args(argv)
    return Config(
        source_mode=args.source_mode,
        jira_path=args.jira_path,
        github_path=args.github_path,
        prior_standup_path=args.prior_standup_path,
        output_path=args.output_path,
    )


def main(argv: Sequence[str] | None = None) -> None:
    config = parse_args(argv)
    try:
        build_pre_read(config)
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(f"Wrote {config.output_path}")


if __name__ == "__main__":
    main()
