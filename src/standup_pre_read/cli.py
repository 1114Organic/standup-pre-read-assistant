from __future__ import annotations

from .collectors import SourceConnector, connector_from_config
from .config import Config
from .generator import generate_pre_read
from .normalizer import normalize_all


def build_pre_read(config: Config = Config(), connector: SourceConnector | None = None) -> str:
    source_connector = connector or connector_from_config(config)
    sources = source_connector.collect()
    activities = normalize_all(sources.jira, sources.github, sources.prior_standup)
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
