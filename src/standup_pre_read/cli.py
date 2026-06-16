from __future__ import annotations

from .collectors import load_github_pr_sample, load_jira_sample, load_prior_standup
from .config import Config
from .generator import generate_pre_read
from .normalizer import normalize_all


def build_pre_read(config: Config = Config()) -> str:
    jira_data = load_jira_sample(config.jira_path)
    github_data = load_github_pr_sample(config.github_path)
    prior_markdown = load_prior_standup(config.prior_standup_path)
    activities = normalize_all(jira_data, github_data, prior_markdown)
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
