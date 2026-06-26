from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .models import Activity


@dataclass(frozen=True)
class GeneratedBullet:
    text: str
    sources: tuple[Activity, ...]

    def render(self) -> str:
        refs = ", ".join(source.source_id for source in self.sources)
        return f"- {self.text} Source: {refs}." if refs else f"- {self.text} Source: supplied data."


def _activities(activities: list[Activity], activity_type: str) -> list[Activity]:
    return [activity for activity in activities if activity.activity_type == activity_type]


def _open_prs(activities: list[Activity]) -> list[Activity]:
    return [activity for activity in _activities(activities, "github_pr") if activity.status.lower() == "open"]


def _linked_prs(issue: Activity, activities: list[Activity]) -> list[Activity]:
    return [pr for pr in _activities(activities, "github_pr") if issue.source_id in pr.related_work_items]


def _first_linked_pr(issue: Activity, activities: list[Activity]) -> Activity | None:
    return next(iter(_linked_prs(issue, activities)), None)


def _is_done(status: str) -> bool:
    return status.lower() in {"done", "closed", "resolved", "complete", "completed"}


def _is_review(status: str) -> bool:
    return "review" in status.lower()


def _needs_review(pr: Activity) -> bool:
    review_state = (pr.review_state or "").lower()
    return pr.status.lower() == "open" and review_state in {"review_required", "changes_requested"}


def _format_date(value: datetime | None) -> str:
    return value.strftime("%B %-d") if value else "an unknown date"


def _issue_summary(issue: Activity, activities: list[Activity]) -> tuple[str, tuple[Activity, ...]]:
    pr = _first_linked_pr(issue, activities)
    linked = (pr,) if pr else tuple()
    if _is_done(issue.status):
        return f"{issue.source_id} is done. {issue.description or issue.title}", (issue, *linked)
    if _is_review(issue.status):
        detail = issue.description or issue.title
        if pr and pr.review_state:
            detail = f"{detail} Related PR review state is {pr.review_state.replace('_', ' ')}."
        return f"{issue.source_id} moved to review. {detail}", (issue, *linked)
    return f"{issue.source_id} is {issue.status.lower()}. {issue.description or issue.title}", (issue, *linked)


def _pr_risk(pr: Activity, today: date, stale_pr_days: int) -> GeneratedBullet | None:
    if pr.status.lower() != "open":
        return None
    age_days = (today - pr.timestamp.date()).days if pr.timestamp else None
    idle_days = (today - pr.updated_timestamp.date()).days if pr.updated_timestamp else None
    reasons: list[str] = []
    if age_days is not None and age_days >= stale_pr_days:
        reasons.append(f"open for {age_days} days since {_format_date(pr.timestamp)}")
    if pr.ci_state == "failing" or pr.risk_signal:
        reasons.append("has failing CI")
    if pr.review_state == "changes_requested":
        reasons.append("requested review changes")
    if idle_days is not None and idle_days >= stale_pr_days:
        reasons.append(f"no updates for {idle_days} days")
    if not reasons:
        return None
    linked = f" linked to {', '.join(pr.related_work_items)}" if pr.related_work_items else " with no linked issue"
    return GeneratedBullet(f"{pr.source_id} is {', '.join(reasons)}{linked}.", (pr,))


def _render_section(bullets: list[GeneratedBullet], empty: str) -> list[str]:
    return [bullet.render() for bullet in bullets] or [f"- {empty}"]


def _references(activities: list[Activity]) -> list[str]:
    seen: dict[str, str] = {}
    for activity in activities:
        if activity.source_url:
            seen[activity.source_id] = activity.source_url
    return [f"- {source_id}: {seen[source_id]}" for source_id in sorted(seen)]


def _summary(
    progress: list[GeneratedBullet],
    blockers: list[GeneratedBullet],
    decisions: list[GeneratedBullet],
    risks: list[GeneratedBullet],
) -> str:
    parts: list[str] = []
    if progress:
        parts.append(f"{len(progress)} progress item{'s' if len(progress) != 1 else ''} found")
    if blockers:
        parts.append(f"{len(blockers)} blocker{'s' if len(blockers) != 1 else ''} need action")
    if decisions:
        parts.append(f"{len(decisions)} decision{'s' if len(decisions) != 1 else ''} need discussion")
    if risks:
        parts.append(f"{len(risks)} risk or aging-work item{'s' if len(risks) != 1 else ''} flagged")
    return (
        "No significant updates were found in the supplied sources."
        if not parts
        else "The generated pre-read found " + ", ".join(parts) + "."
    )


def _agenda(
    blockers: list[GeneratedBullet],
    decisions: list[GeneratedBullet],
    risks: list[GeneratedBullet],
    activities: list[Activity],
) -> list[str]:
    items: list[str] = []
    items.extend(f"Confirm next step: {b.text}" for b in blockers)
    items.extend(f"Make decision: {d.text}" for d in decisions)
    items.extend(f"Review risk: {r.text}" for r in risks if "failing CI" in r.text or "open for" in r.text)
    review_prs = [pr for pr in _open_prs(activities) if _needs_review(pr)]
    items.extend(f"Confirm review path for {pr.source_id}: {pr.title}." for pr in review_prs)
    deduped = list(dict.fromkeys(items))[:5]
    return [f"{idx}. {item}" for idx, item in enumerate(deduped, start=1)] or [
        "1. No urgent discussion topics found in the supplied sources."
    ]


def generate_pre_read(activities: list[Activity], team_name: str, stale_pr_days: int, today: date | None = None) -> str:
    today = today or date.today()
    issues = sorted(_activities(activities, "jira_issue"), key=lambda activity: activity.source_id)

    progress: list[GeneratedBullet] = []
    for issue in issues:
        if _is_done(issue.status) or _is_review(issue.status) or issue.status.lower() in {"in progress", "blocked"}:
            text, sources = _issue_summary(issue, activities)
            progress.append(GeneratedBullet(text.strip().rstrip(".") + ".", sources))

    blockers = [
        GeneratedBullet(
            f"{issue.source_id} is blocked {issue.blocker_signal or issue.description or issue.title}", (issue,)
        )
        for issue in issues
        if issue.blocker_signal or issue.status.lower() == "blocked"
    ]
    decisions = [
        GeneratedBullet(f"{issue.decision_signal} ({issue.source_id}).", (issue,))
        for issue in issues
        if issue.decision_signal
    ]
    risks = [
        risk
        for pr in sorted(_open_prs(activities), key=lambda activity: activity.source_id)
        if (risk := _pr_risk(pr, today, stale_pr_days))
    ]

    carryover = [
        GeneratedBullet(activity.title, (activity,))
        for activity in activities
        if activity.activity_type in {"prior_blocker", "prior_decision", "prior_carryover"}
    ]

    lines = [
        f"# Standup Pre-Read: {team_name}",
        "",
        f"Generated: {today.isoformat()}",
        "",
        "## Executive Summary",
        "",
        _summary(progress, blockers, decisions, risks),
        "",
        "## Progress Since Last Standup",
        "",
        *_render_section(progress, "No confirmed progress found in the supplied sources."),
        "",
        "## Blockers Needing Action",
        "",
        *_render_section(blockers, "No active blockers found in the supplied sources."),
        "",
        "## Decisions Needed",
        "",
        *_render_section(decisions, "No open decisions found in the supplied sources."),
        "",
        "## Risks and Aging Work",
        "",
        *_render_section(risks, "No stale or risky pull requests found in the supplied sources."),
        "",
        "## Carryover From Yesterday",
        "",
        *_render_section(carryover, "No unresolved carryover found in the supplied prior standup."),
        "",
        "## Suggested Standup Agenda",
        "",
        *_agenda(blockers, decisions, risks, activities),
        "",
        "## Source References",
        "",
        *_references(activities),
        "",
    ]
    return "\n".join(lines)
