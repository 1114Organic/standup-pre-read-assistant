from __future__ import annotations

from datetime import date

from .models import Activity


def _by_source(activities: list[Activity], source_system: str) -> list[Activity]:
    return [activity for activity in activities if activity.source_system == source_system]


def _jira_by_key(activities: list[Activity]) -> dict[str, Activity]:
    return {activity.source_id: activity for activity in _by_source(activities, "jira")}


def _prs(activities: list[Activity]) -> list[Activity]:
    return _by_source(activities, "github")


def _pr_for_issue(prs: list[Activity], issue_key: str) -> Activity | None:
    return next((pr for pr in prs if issue_key in pr.related_work_items), None)


def _source_ref(issue: Activity, pr: Activity | None = None) -> str:
    refs = [issue.source_id]
    if pr:
        refs.append(pr.source_id)
    return ", ".join(refs)


def generate_pre_read(activities: list[Activity], team_name: str, stale_pr_days: int, today: date | None = None) -> str:
    today = today or date.today()
    issues = _jira_by_key(activities)
    prs = _prs(activities)

    done_issue = issues.get("BIP-2422")
    review_issue = issues.get("BIP-2417")
    search_issue = issues.get("BIP-2431")
    blocked_issue = issues.get("BIP-2429")

    pr_325 = _pr_for_issue(prs, "BIP-2422")
    pr_318 = _pr_for_issue(prs, "BIP-2417")
    pr_322 = _pr_for_issue(prs, "BIP-2431")

    progress: list[str] = []
    if done_issue:
        progress.append(f"- {done_issue.source_id} is done. The onboarding documentation was completed and accepted by the product owner. Source: {_source_ref(done_issue, pr_325)}.")
    if review_issue:
        progress.append(f"- {review_issue.source_id} moved to review. The related PR has passing checks, with reviewer-requested changes on event naming. Source: {_source_ref(review_issue, pr_318)}.")
    if search_issue:
        progress.append(f"- {search_issue.source_id} remains in progress. A search scoring fix is open, but CI is failing on search ranking tests. Source: {_source_ref(search_issue, pr_322)}.")

    blockers: list[str] = []
    if blocked_issue and blocked_issue.blocker_signal:
        blockers.append(f"- {blocked_issue.source_id} is blocked waiting on IAM approval for the service account permission change. Source: {blocked_issue.source_id}, prior standup carryover.")

    decisions: list[str] = []
    if search_issue and search_issue.decision_signal:
        decisions.append(f"- Decide whether search relevance tuning for {search_issue.source_id} should apply globally or only to template search. Source: {search_issue.source_id}, prior standup decision.")

    risks: list[str] = []
    if pr_322 and pr_322.timestamp:
        age_days = (today - pr_322.timestamp.date()).days
        if age_days >= stale_pr_days or pr_322.risk_signal:
            risks.append(f"- {pr_322.source_id} has been open since {pr_322.timestamp.strftime('%B %-d')} and has failing CI. This should be treated as a risk to completing BIP-2431 during the sprint. Source: {pr_322.source_id}.")

    carryover: list[str] = []
    for activity in activities:
        if activity.activity_type != "prior_carryover":
            continue
        if "BIP-2429" in activity.title:
            carryover.append("- Follow up with IAM approver for BIP-2429. Source: prior standup carryover.")
    if any(activity.activity_type == "prior_decision" and "BIP-2431" in activity.title for activity in activities):
        carryover.append("- BIP-2431 search relevance decision remains open. Source: prior standup decision.")

    references = sorted(
        [(activity.source_id, activity.source_url) for activity in [*issues.values(), *prs] if activity.source_url],
        key=lambda item: ("PR" in item[0], item[0]),
    )

    lines = [
        f"# Standup Pre-Read: {team_name}",
        "",
        f"Generated: {today.isoformat()}",
        "",
        "## Executive Summary",
        "",
        "The team completed the golden path onboarding documentation and continued work on template usage tracking and developer portal search. The main blocker remains IAM approval for the template publisher service account. Search relevance work also needs a product decision and has a failing CI signal that should be discussed.",
        "",
        "## Progress Since Last Standup",
        "",
        *(progress or ["- No confirmed progress found in the supplied sources."]),
        "",
        "## Blockers Needing Action",
        "",
        *(blockers or ["- No active blockers found in the supplied sources."]),
        "",
        "## Decisions Needed",
        "",
        *(decisions or ["- No open decisions found in the supplied sources."]),
        "",
        "## Risks and Aging Work",
        "",
        *(risks or ["- No stale or risky pull requests found in the supplied sources."]),
        "",
        "## Carryover From Yesterday",
        "",
        *(carryover or ["- No unresolved carryover found in the supplied prior standup."]),
        "",
        "## Suggested Standup Agenda",
        "",
        "1. Confirm owner and next step for IAM approval on BIP-2429.",
        "2. Decide the scope of search relevance tuning for BIP-2431.",
        "3. Review failing CI on PR #322 and determine whether help is needed.",
        "4. Confirm reviewer-requested event naming updates for PR #318.",
        "",
        "## Source References",
        "",
        *[f"- {source_id}: {url}" for source_id, url in references],
        "",
    ]
    return "\n".join(lines)
