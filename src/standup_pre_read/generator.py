from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from .models import Activity


@dataclass(frozen=True)
class GeneratedBullet:
    text: str
    sources: tuple[Activity, ...]

    @property
    def source_refs(self) -> tuple[str, ...]:
        return tuple(source.source_id for source in self.sources if source.source_id)

    @property
    def related_work_items(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item for source in self.sources for item in source.related_work_items if item))

    @property
    def confidence(self) -> str | None:
        confidences = tuple(dict.fromkeys(source.confidence for source in self.sources if source.confidence))
        if len(confidences) == 1:
            return confidences[0]
        if confidences:
            return "mixed"
        return None

    def render(self) -> str:
        refs = ", ".join(self.source_refs)
        return f"- {self.text} Source: {refs}." if refs else f"- {self.text} Source: supplied data."

    def to_json_item(self) -> dict[str, Any]:
        item: dict[str, Any] = {"text": self.text, "source_refs": list(self.source_refs)}
        if self.confidence is not None:
            item["confidence"] = self.confidence
        if self.related_work_items:
            item["related_work_items"] = list(self.related_work_items)
        return item


@dataclass(frozen=True)
class PreReadDocument:
    generated_at: str
    team_name: str | None
    source_mode: str
    data_window: dict[str, str] | None
    executive_summary: str
    progress: tuple[GeneratedBullet, ...]
    blockers: tuple[GeneratedBullet, ...]
    decisions: tuple[GeneratedBullet, ...]
    risks: tuple[GeneratedBullet, ...]
    carryover: tuple[GeneratedBullet, ...]
    suggested_agenda: tuple[GeneratedBullet, ...]
    suggested_questions: tuple[GeneratedBullet, ...]
    source_references: tuple[dict[str, str], ...]

    def to_json_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "generated_at": self.generated_at,
            "source_mode": self.source_mode,
            "executive_summary": self.executive_summary,
            "progress": [item.to_json_item() for item in self.progress],
            "blockers": [item.to_json_item() for item in self.blockers],
            "decisions": [item.to_json_item() for item in self.decisions],
            "risks": [item.to_json_item() for item in self.risks],
            "carryover": [item.to_json_item() for item in self.carryover],
            "suggested_agenda": [item.to_json_item() for item in self.suggested_agenda],
            "suggested_questions": [item.to_json_item() for item in self.suggested_questions],
            "source_references": list(self.source_references),
        }
        if self.team_name:
            payload["team_name"] = self.team_name
        if self.data_window:
            payload["data_window"] = self.data_window
        return payload


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


def _render_section(bullets: tuple[GeneratedBullet, ...], empty: str) -> list[str]:
    return [bullet.render() for bullet in bullets] or [f"- {empty}"]


def _source_reference(sources: tuple[Activity, ...]) -> str:
    refs = ", ".join(source.source_id for source in sources if source.source_id)
    return refs or "supplied data"


def _question(text: str, sources: tuple[Activity, ...]) -> GeneratedBullet:
    return GeneratedBullet(f"{text.rstrip('.?')}?", sources)


def _standup_questions(
    blockers: tuple[GeneratedBullet, ...],
    decisions: tuple[GeneratedBullet, ...],
    risks: tuple[GeneratedBullet, ...],
    carryover: tuple[GeneratedBullet, ...],
    activities: list[Activity],
) -> tuple[GeneratedBullet, ...]:
    questions: list[tuple[str, tuple[Activity, ...]]] = []
    for blocker in blockers:
        source = blocker.sources[0] if blocker.sources else None
        subject = source.source_id if source else "this blocker"
        detail = source.blocker_signal or source.description or source.title if source else blocker.text
        questions.append((f"What action is needed today to unblock {subject}: {detail}", blocker.sources))
    for risk in risks:
        source = risk.sources[0] if risk.sources else None
        subject = source.source_id if source else "this risky pull request"
        questions.append((f"What is the next step to reduce risk on {subject}: {risk.text}", risk.sources))
    for decision in decisions:
        source = decision.sources[0] if decision.sources else None
        subject = source.source_id if source else "this decision"
        detail = source.decision_signal if source and source.decision_signal else decision.text
        questions.append((f"Who can make or facilitate the decision for {subject}: {detail}", decision.sources))
    for activity in activities:
        if activity.activity_type == "chat_signal":
            questions.append(
                (
                    f"Who can clarify ownership or next steps from chat: {activity.description}",
                    (activity,),
                )
            )
            continue
        if activity.activity_type not in {"jira_issue", "github_pr"}:
            continue
        missing: list[str] = []
        if not activity.owner:
            missing.append("owner")
        if not activity.status or activity.status.lower() == "unknown":
            missing.append("status")
        if missing:
            questions.append(
                (
                    f"Who owns {activity.source_id} and what is its current status; missing {', '.join(missing)}",
                    (activity,),
                )
            )
    for item in carryover:
        source = item.sources[0] if item.sources else None
        subject = source.source_id if source and source.source_id != "prior-standup" else "prior standup carryover"
        questions.append(
            (
                f"Should we keep carrying over {subject}, and what changed since the last standup: {item.text}",
                item.sources,
            )
        )
    deduped: list[GeneratedBullet] = []
    seen: set[str] = set()
    for text, sources in questions:
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(_question(text, sources))
        if len(deduped) == 9:
            break
    return tuple(deduped)


def _references(activities: list[Activity]) -> tuple[dict[str, str], ...]:
    seen: dict[str, dict[str, str]] = {}
    for activity in activities:
        if activity.source_url:
            seen[activity.source_id] = {
                "source_ref": activity.source_id,
                "url": activity.source_url,
                "source_system": activity.source_system,
            }
    return tuple(seen[source_id] for source_id in sorted(seen))


def _summary(
    progress: tuple[GeneratedBullet, ...],
    blockers: tuple[GeneratedBullet, ...],
    decisions: tuple[GeneratedBullet, ...],
    risks: tuple[GeneratedBullet, ...],
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
    if not parts:
        return "No significant updates were found in the supplied sources."
    return "The generated pre-read found " + ", ".join(parts) + "."


def _agenda(
    blockers: tuple[GeneratedBullet, ...],
    decisions: tuple[GeneratedBullet, ...],
    risks: tuple[GeneratedBullet, ...],
    activities: list[Activity],
) -> tuple[GeneratedBullet, ...]:
    items: list[GeneratedBullet] = []
    items.extend(GeneratedBullet(f"Confirm next step: {b.text}", b.sources) for b in blockers)
    items.extend(GeneratedBullet(f"Make decision: {d.text}", d.sources) for d in decisions)
    items.extend(
        GeneratedBullet(f"Review risk: {r.text}", r.sources)
        for r in risks
        if "failing CI" in r.text or "open for" in r.text
    )
    review_prs = [pr for pr in _open_prs(activities) if _needs_review(pr)]
    items.extend(GeneratedBullet(f"Confirm review path for {pr.source_id}: {pr.title}.", (pr,)) for pr in review_prs)
    deduped: list[GeneratedBullet] = []
    seen: set[str] = set()
    for item in items:
        if item.text in seen:
            continue
        seen.add(item.text)
        deduped.append(item)
        if len(deduped) == 5:
            break
    return tuple(deduped)


def _data_window(activities: list[Activity]) -> dict[str, str] | None:
    timestamps = [ts for activity in activities for ts in (activity.timestamp, activity.updated_timestamp) if ts]
    if not timestamps:
        return None
    return {"start": min(timestamps).date().isoformat(), "end": max(timestamps).date().isoformat()}


def generate_pre_read_document(
    activities: list[Activity],
    team_name: str | None,
    stale_pr_days: int,
    today: date | None = None,
    source_mode: str = "sample",
) -> PreReadDocument:
    today = today or date.today()
    issues = sorted(_activities(activities, "jira_issue"), key=lambda activity: activity.source_id)
    progress = tuple(
        GeneratedBullet(text.strip().rstrip(".") + ".", sources)
        for issue in issues
        if _is_done(issue.status) or _is_review(issue.status) or issue.status.lower() in {"in progress", "blocked"}
        for text, sources in [_issue_summary(issue, activities)]
    )
    issue_blockers = tuple(
        GeneratedBullet(
            f"{issue.source_id} is blocked {issue.blocker_signal or issue.description or issue.title}",
            (issue,),
        )
        for issue in issues
        if issue.blocker_signal or issue.status.lower() == "blocked"
    )
    chat_blockers = tuple(
        GeneratedBullet(f"Chat blocker: {activity.description}", (activity,))
        for activity in activities
        if activity.activity_type == "chat_blocker"
    )
    blockers = (*issue_blockers, *chat_blockers)
    issue_decisions = tuple(
        GeneratedBullet(f"{issue.decision_signal} ({issue.source_id}).", (issue,))
        for issue in issues
        if issue.decision_signal
    )
    chat_decisions = tuple(
        GeneratedBullet(f"Chat decision requested: {activity.description}", (activity,))
        for activity in activities
        if activity.activity_type == "chat_decision"
    )
    decisions = (*issue_decisions, *chat_decisions)
    risks = tuple(
        risk
        for pr in sorted(_open_prs(activities), key=lambda activity: activity.source_id)
        if (risk := _pr_risk(pr, today, stale_pr_days))
    )
    carryover = tuple(
        GeneratedBullet(activity.title, (activity,))
        for activity in activities
        if activity.activity_type
        in {
            "prior_blocker",
            "prior_decision",
            "prior_carryover",
            "chat_follow_up",
            "chat_signal",
        }
    )
    summary = _summary(progress, blockers, decisions, risks)
    return PreReadDocument(
        generated_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC).isoformat(),
        team_name=team_name,
        source_mode=source_mode,
        data_window=_data_window(activities),
        executive_summary=summary,
        progress=progress,
        blockers=blockers,
        decisions=decisions,
        risks=risks,
        carryover=carryover,
        suggested_agenda=_agenda(blockers, decisions, risks, activities),
        suggested_questions=_standup_questions(blockers, decisions, risks, carryover, activities),
        source_references=_references(activities),
    )


def render_pre_read_markdown(document: PreReadDocument) -> str:
    generated_date = document.generated_at[:10]
    agenda_lines = [f"{idx}. {item.text}" for idx, item in enumerate(document.suggested_agenda, start=1)] or [
        "1. No urgent discussion topics found in the supplied sources."
    ]
    question_lines = [item.render() for item in document.suggested_questions] or [
        "- No high-value standup questions found in the supplied sources."
    ]
    lines = [
        f"# Standup Pre-Read: {document.team_name or 'Team'}",
        "",
        f"Generated: {generated_date}",
        "",
        "## Executive Summary",
        "",
        document.executive_summary,
        "",
        "## Progress Since Last Standup",
        "",
        *_render_section(document.progress, "No confirmed progress found in the supplied sources."),
        "",
        "## Blockers Needing Action",
        "",
        *_render_section(document.blockers, "No active blockers found in the supplied sources."),
        "",
        "## Decisions Needed",
        "",
        *_render_section(document.decisions, "No open decisions found in the supplied sources."),
        "",
        "## Risks and Aging Work",
        "",
        *_render_section(document.risks, "No stale or risky pull requests found in the supplied sources."),
        "",
        "## Carryover From Yesterday",
        "",
        *_render_section(document.carryover, "No unresolved carryover found in the supplied prior standup."),
        "",
        "## Suggested Standup Agenda",
        "",
        *agenda_lines,
        "",
        "## Suggested Standup Questions",
        "",
        *question_lines,
        "",
        "## Source References",
        "",
        *[f"- {reference['source_ref']}: {reference['url']}" for reference in document.source_references],
        "",
    ]
    return "\n".join(lines)


def generate_pre_read(activities: list[Activity], team_name: str, stale_pr_days: int, today: date | None = None) -> str:
    return render_pre_read_markdown(generate_pre_read_document(activities, team_name, stale_pr_days, today))
