from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Literal

from .connectors import SourceHealth
from .models import Activity

ReviewStatus = Literal["draft", "approved", "rejected"]


@dataclass(frozen=True)
class GeneratedBullet:
    text: str
    sources: tuple[Activity, ...]
    priority: int | None = None

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
        if self.priority is not None:
            item["priority"] = self.priority
        pr_metadata = [_pr_metadata(source) for source in self.sources if source.activity_type == "github_pr"]
        pr_metadata = [metadata for metadata in pr_metadata if metadata]
        if pr_metadata:
            item["pr_metadata"] = pr_metadata
        return item


@dataclass(frozen=True)
class PreReadDocument:
    generated_at: str
    team_name: str | None
    source_mode: str
    review_status: ReviewStatus
    reviewed_at: str | None
    reviewer: str | None
    review_notes: str | None
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
    source_health: tuple[SourceHealth, ...]

    def to_json_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "generated_at": self.generated_at,
            "source_mode": self.source_mode,
            "review_status": self.review_status,
            "executive_summary": self.executive_summary,
            "progress": [item.to_json_item() for item in self.progress],
            "blockers": [item.to_json_item() for item in self.blockers],
            "decisions": [item.to_json_item() for item in self.decisions],
            "risks": [item.to_json_item() for item in self.risks],
            "carryover": [item.to_json_item() for item in self.carryover],
            "suggested_agenda": [item.to_json_item() for item in self.suggested_agenda],
            "suggested_questions": [item.to_json_item() for item in self.suggested_questions],
            "source_references": list(self.source_references),
            "source_health": [item.to_json_dict() for item in self.source_health],
        }
        if self.team_name:
            payload["team_name"] = self.team_name
        if self.reviewed_at:
            payload["reviewed_at"] = self.reviewed_at
        if self.reviewer:
            payload["reviewer"] = self.reviewer
        if self.review_notes:
            payload["review_notes"] = self.review_notes
        if self.data_window:
            payload["data_window"] = self.data_window
        return payload


def _activities(activities: list[Activity], activity_type: str) -> list[Activity]:
    return [activity for activity in activities if activity.activity_type == activity_type]


def _activity_priority(activity: Activity, today: date | None = None, stale_pr_days: int = 5) -> int:
    score = 10
    status = activity.status.lower()
    signal_text = " ".join(
        part
        for part in (
            activity.title,
            activity.description,
            activity.blocker_signal or "",
            activity.decision_signal or "",
            activity.risk_signal or "",
            activity.ci_state or "",
            activity.review_state or "",
            activity.merge_state or "",
        )
        if part
    ).lower()

    if (
        activity.blocker_signal
        or activity.activity_type in {"chat_blocker", "prior_blocker"}
        or "block" in status
        or "block" in signal_text
    ):
        score += 90
    if (
        activity.decision_signal
        or activity.activity_type in {"chat_decision", "prior_decision"}
        or "decision" in signal_text
    ):
        score += 75
    if activity.activity_type in {
        "prior_blocker",
        "prior_decision",
        "prior_carryover",
        "chat_follow_up",
        "chat_signal",
    }:
        score += 45
    if activity.ci_state == "failing" or "failing ci" in signal_text:
        score += 80
    if activity.review_state == "changes_requested":
        score += 70
    elif activity.review_state in {"review_required", "review_requested"}:
        score += 25
    if activity.merge_state == "blocked":
        score += 65
    elif activity.merge_state == "waiting_on_decision":
        score += 55
    if activity.risk_signal:
        score += 45
    if activity.activity_type == "github_pr" and status == "open":
        if today and activity.timestamp:
            age_days = (today - activity.timestamp.date()).days
            if age_days >= stale_pr_days:
                score += 60 + min(age_days, 30)
        if today and activity.updated_timestamp:
            idle_days = (today - activity.updated_timestamp.date()).days
            if idle_days >= stale_pr_days:
                score += 35 + min(idle_days, 30)
        if not activity.related_work_items:
            score += 35
    if not activity.owner or not activity.status or status == "unknown":
        score += 35
    if _is_done(activity.status):
        score -= 20
    if status in {"in progress", "review"} and not any(
        (activity.blocker_signal, activity.decision_signal, activity.risk_signal)
    ):
        score -= 5
    return max(score, 0)


def _bullet_priority(bullet: GeneratedBullet, today: date | None = None, stale_pr_days: int = 5) -> int:
    if bullet.priority is not None:
        return bullet.priority
    if not bullet.sources:
        return 0
    score = max(_activity_priority(source, today, stale_pr_days) for source in bullet.sources)
    text = bullet.text.lower()
    if "failing ci" in text:
        score += 20
    if "open for" in text or "no updates" in text:
        score += 15
    return score


def _with_priorities(
    bullets: tuple[GeneratedBullet, ...], today: date | None = None, stale_pr_days: int = 5
) -> tuple[GeneratedBullet, ...]:
    return tuple(
        bullet
        if bullet.priority is not None
        else GeneratedBullet(bullet.text, bullet.sources, _bullet_priority(bullet, today, stale_pr_days))
        for bullet in bullets
    )


def _prioritize(
    bullets: tuple[GeneratedBullet, ...], today: date | None = None, stale_pr_days: int = 5
) -> tuple[GeneratedBullet, ...]:
    prioritized = _with_priorities(bullets, today, stale_pr_days)
    return tuple(
        bullet
        for _, bullet in sorted(
            enumerate(prioritized),
            key=lambda item: (-(item[1].priority or 0), item[0]),
        )
    )


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
    return pr.status.lower() == "open" and review_state in {"review_required", "review_requested", "changes_requested"}


def _pr_metadata(pr: Activity) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for key, value in (
        ("review_state", pr.review_state),
        ("ci_state", pr.ci_state),
        ("merge_state", pr.merge_state),
        ("stale_days", pr.stale_days),
        ("draft", pr.draft),
        ("owner", pr.owner),
    ):
        if value is not None:
            metadata[key] = value
    if pr.stale_days is not None:
        metadata["age_days"] = pr.stale_days
    if pr.timestamp:
        metadata["created_at"] = pr.timestamp.isoformat()
    if pr.updated_timestamp:
        metadata["updated_at"] = pr.updated_timestamp.isoformat()
    if pr.related_work_items:
        metadata["linked_issues"] = list(pr.related_work_items)
    if pr.reviewers:
        metadata["reviewers"] = list(pr.reviewers)
    if pr.approvals:
        metadata["approvals"] = list(pr.approvals)
    if pr.requested_changes:
        metadata["requested_changes"] = list(pr.requested_changes)
    return metadata


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
    if pr.ci_state == "failing":
        reasons.append("has failing CI")
    if pr.review_state == "changes_requested":
        reasons.append("requested review changes")
    if pr.merge_state == "blocked":
        reasons.append("blocked from merging")
    if idle_days is not None and idle_days >= stale_pr_days:
        reasons.append(f"no updates for {idle_days} days")
    if not reasons:
        return None
    linked = f" linked to {', '.join(pr.related_work_items)}" if pr.related_work_items else " with no linked issue"
    return GeneratedBullet(f"{pr.source_id} is {', '.join(reasons)}{linked}.", (pr,))


def _pr_progress(pr: Activity) -> GeneratedBullet | None:
    if pr.status.lower() != "merged":
        return None
    linked = f" linked to {', '.join(pr.related_work_items)}" if pr.related_work_items else " with no linked issue"
    approval = " after approval" if pr.review_state == "approved" or pr.approvals else ""
    return GeneratedBullet(f"{pr.source_id} merged{approval}: {pr.title}{linked}.", (pr,))


def _render_section(bullets: tuple[GeneratedBullet, ...], empty: str) -> list[str]:
    return [bullet.render() for bullet in bullets] or [f"- {empty}"]


def _source_reference(sources: tuple[Activity, ...]) -> str:
    refs = ", ".join(source.source_id for source in sources if source.source_id)
    return refs or "supplied data"


def _question(
    text: str,
    sources: tuple[Activity, ...],
    priority: int | None = None,
    today: date | None = None,
    stale_pr_days: int = 5,
) -> GeneratedBullet:
    return GeneratedBullet(
        f"{text.rstrip('.?')}?",
        sources,
        priority
        if priority is not None
        else max((_activity_priority(source, today, stale_pr_days) for source in sources), default=0),
    )


def _standup_questions(
    blockers: tuple[GeneratedBullet, ...],
    decisions: tuple[GeneratedBullet, ...],
    risks: tuple[GeneratedBullet, ...],
    carryover: tuple[GeneratedBullet, ...],
    activities: list[Activity],
    today: date,
    stale_pr_days: int,
) -> tuple[GeneratedBullet, ...]:
    questions: list[GeneratedBullet] = []
    for blocker in blockers:
        source = blocker.sources[0] if blocker.sources else None
        subject = source.source_id if source else "this blocker"
        detail = source.blocker_signal or source.description or source.title if source else blocker.text
        questions.append(
            _question(f"What action is needed today to unblock {subject}: {detail}", blocker.sources, blocker.priority)
        )
    for risk in risks:
        source = risk.sources[0] if risk.sources else None
        subject = source.source_id if source else "this risky pull request"
        questions.append(
            _question(f"What is the next step to reduce risk on {subject}: {risk.text}", risk.sources, risk.priority)
        )
    for pr in _open_prs(activities):
        if pr.review_state in {"review_required", "review_requested"}:
            questions.append(
                _question(
                    f"Who can review {pr.source_id}: {pr.title}",
                    (pr,),
                    _activity_priority(pr, today, stale_pr_days),
                )
            )
        if not pr.related_work_items:
            questions.append(
                _question(
                    f"Should {pr.source_id} be linked to an issue before standup follow-up: {pr.title}",
                    (pr,),
                    _activity_priority(pr, today, stale_pr_days),
                )
            )
    for decision in decisions:
        source = decision.sources[0] if decision.sources else None
        subject = source.source_id if source else "this decision"
        detail = source.decision_signal if source and source.decision_signal else decision.text
        questions.append(
            _question(
                f"Who can make or facilitate the decision for {subject}: {detail}", decision.sources, decision.priority
            )
        )
    for activity in activities:
        if activity.activity_type == "chat_signal":
            questions.append(
                _question(
                    f"Who can clarify ownership or next steps from chat: {activity.description}",
                    (activity,),
                    _activity_priority(activity, today, stale_pr_days),
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
                _question(
                    f"Who owns {activity.source_id} and what is its current status; missing {', '.join(missing)}",
                    (activity,),
                    _activity_priority(activity, today, stale_pr_days),
                )
            )
    for item in carryover:
        source = item.sources[0] if item.sources else None
        subject = source.source_id if source and source.source_id != "prior-standup" else "prior standup carryover"
        questions.append(
            _question(
                f"Should we keep carrying over {subject}, and what changed since the last standup: {item.text}",
                item.sources,
                item.priority,
            )
        )
    deduped: list[GeneratedBullet] = []
    seen: set[str] = set()
    for question in questions:
        key = question.text.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(question)
    return _prioritize(tuple(deduped), today, stale_pr_days)[:20]


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
    items.extend(GeneratedBullet(f"Confirm next step: {b.text}", b.sources, b.priority) for b in blockers)
    items.extend(GeneratedBullet(f"Make decision: {d.text}", d.sources, d.priority) for d in decisions)
    items.extend(
        GeneratedBullet(f"Review risk: {r.text}", r.sources, r.priority)
        for r in risks
        if "failing CI" in r.text or "open for" in r.text or "blocked from merging" in r.text
    )
    review_prs = [pr for pr in _open_prs(activities) if _needs_review(pr)]
    items.extend(
        GeneratedBullet(
            f"Confirm review path for {pr.source_id}: {pr.title}.",
            (pr,),
            _activity_priority(pr),
        )
        for pr in review_prs
    )
    items = list(_prioritize(tuple(items)))
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
    review_status: ReviewStatus = "draft",
    reviewer: str | None = None,
    review_notes: str | None = None,
    source_health: tuple[SourceHealth, ...] = (),
) -> PreReadDocument:
    today = today or date.today()
    if review_status not in {"draft", "approved", "rejected"}:
        raise ValueError(f"Unsupported review_status {review_status!r}")
    issues = sorted(_activities(activities, "jira_issue"), key=lambda activity: activity.source_id)
    progress = _with_priorities(
        (
            *tuple(
                GeneratedBullet(text.strip().rstrip(".") + ".", sources)
                for issue in issues
                if _is_done(issue.status)
                or _is_review(issue.status)
                or issue.status.lower() in {"in progress", "blocked"}
                for text, sources in [_issue_summary(issue, activities)]
            ),
            *tuple(
                bullet
                for pr in sorted(_activities(activities, "github_pr"), key=lambda activity: activity.source_id)
                if (bullet := _pr_progress(pr))
            ),
        ),
        today,
        stale_pr_days,
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
    blockers = _prioritize((*issue_blockers, *chat_blockers), today, stale_pr_days)
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
    pr_decisions = tuple(
        GeneratedBullet(f"{pr.decision_signal} ({pr.source_id}).", (pr,))
        for pr in _open_prs(activities)
        if pr.decision_signal or pr.merge_state == "waiting_on_decision"
    )
    decisions = _prioritize((*issue_decisions, *chat_decisions, *pr_decisions), today, stale_pr_days)
    risks = _prioritize(
        tuple(
            risk
            for pr in sorted(_open_prs(activities), key=lambda activity: activity.source_id)
            if (risk := _pr_risk(pr, today, stale_pr_days))
        ),
        today,
        stale_pr_days,
    )
    carryover = _prioritize(
        tuple(
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
        ),
        today,
        stale_pr_days,
    )
    summary = _summary(progress, blockers, decisions, risks)
    return PreReadDocument(
        generated_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC).isoformat(),
        team_name=team_name,
        source_mode=source_mode,
        review_status=review_status,
        reviewed_at=(datetime.now(UTC).isoformat() if review_status in {"approved", "rejected"} else None),
        reviewer=reviewer,
        review_notes=review_notes,
        data_window=_data_window(activities),
        executive_summary=summary,
        progress=progress,
        blockers=blockers,
        decisions=decisions,
        risks=risks,
        carryover=carryover,
        suggested_agenda=_agenda(blockers, decisions, risks, activities),
        suggested_questions=_standup_questions(blockers, decisions, risks, carryover, activities, today, stale_pr_days),
        source_references=_references(activities),
        source_health=source_health,
    )


def render_pre_read_markdown(document: PreReadDocument) -> str:
    generated_date = document.generated_at[:10]
    agenda_lines = [f"{idx}. {item.text}" for idx, item in enumerate(document.suggested_agenda, start=1)] or [
        "1. No urgent discussion topics found in the supplied sources."
    ]
    question_lines = [item.render() for item in document.suggested_questions] or [
        "- No high-value standup questions found in the supplied sources."
    ]
    review_lines = [
        "## Review Metadata",
        "",
        f"- Status: {document.review_status}",
    ]
    if document.reviewed_at:
        review_lines.append(f"- Reviewed at: {document.reviewed_at}")
    if document.reviewer:
        review_lines.append(f"- Reviewer: {document.reviewer}")
    if document.review_notes:
        review_lines.append(f"- Notes: {document.review_notes}")
    lines = [
        f"# Standup Pre-Read: {document.team_name or 'Team'}",
        "",
        f"Generated: {generated_date}",
        "",
        *review_lines,
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
        "## Source Health",
        "",
        *_render_source_health(document.source_health),
        "",
        "## Source References",
        "",
        *[f"- {reference['source_ref']}: {reference['url']}" for reference in document.source_references],
        "",
    ]
    return "\n".join(lines)


def _render_source_health(source_health: tuple[SourceHealth, ...]) -> list[str]:
    if not source_health:
        return ["- No source health metadata was supplied."]
    lines = []
    for item in source_health:
        requirement = "required" if item.required else "optional"
        lines.append(f"- {item.name}: {item.status} ({requirement}) - {item.message}")
    return lines


def generate_pre_read(activities: list[Activity], team_name: str, stale_pr_days: int, today: date | None = None) -> str:
    return render_pre_read_markdown(generate_pre_read_document(activities, team_name, stale_pr_days, today))
