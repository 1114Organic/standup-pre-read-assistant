# Standup Pre-Read: Tenant Success ART

Generated: 2026-06-16

## Executive Summary

The team completed the golden path onboarding documentation and continued work on template usage tracking and developer portal search. The main blocker remains IAM approval for the template publisher service account. Search relevance work also needs a product decision and has a failing CI signal that should be discussed.

## Progress Since Last Standup

- BIP-2422 is done. The onboarding documentation was completed and accepted by the product owner. Source: BIP-2422, PR #325.
- BIP-2417 moved to review. The related PR has passing checks, with reviewer-requested changes on event naming. Source: BIP-2417, PR #318.
- BIP-2431 remains in progress. A search scoring fix is open, but CI is failing on search ranking tests. Source: BIP-2431, PR #322.

## Blockers Needing Action

- BIP-2429 is blocked waiting on IAM approval for the service account permission change. Source: BIP-2429, prior standup carryover.

## Decisions Needed

- Decide whether search relevance tuning for BIP-2431 should apply globally or only to template search. Source: BIP-2431, prior standup decision.

## Risks and Aging Work

- PR #322 has been open since June 10 and has failing CI. This should be treated as a risk to completing BIP-2431 during the sprint. Source: PR #322.

## Carryover From Yesterday

- Follow up with IAM approver for BIP-2429. Source: prior standup carryover.
- BIP-2431 search relevance decision remains open. Source: prior standup decision.

## Suggested Standup Agenda

1. Confirm owner and next step for IAM approval on BIP-2429.
2. Decide the scope of search relevance tuning for BIP-2431.
3. Review failing CI on PR #322 and determine whether help is needed.
4. Confirm reviewer-requested event naming updates for PR #318.

## Source References

- BIP-2417: https://jira.example.local/browse/BIP-2417
- BIP-2422: https://jira.example.local/browse/BIP-2422
- BIP-2429: https://jira.example.local/browse/BIP-2429
- BIP-2431: https://jira.example.local/browse/BIP-2431
- PR #318: https://github.com/example/tenant-success-portal/pull/318
- PR #322: https://github.com/example/tenant-success-portal/pull/322
- PR #325: https://github.com/example/tenant-success-portal/pull/325
