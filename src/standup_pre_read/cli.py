from __future__ import annotations

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


def main() -> None:
    config = Config()
    build_pre_read(config)
    print(f"Wrote {config.output_path}")


if __name__ == "__main__":
    main()
