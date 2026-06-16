# Standup Pre-Read: Example Platform Team

Generated: 2026-06-16

## Executive Summary

The generated pre-read found 4 progress items found, 1 blocker need action, 1 decision need discussion, 2 risk or aging-work items flagged.

## Progress Since Last Standup

- DEMO-101 is done. Documentation updates were completed and accepted by the product owner. Source: DEMO-101, PR #503.
- DEMO-102 moved to review. Implementation completed and moved to review. Waiting on platform reviewer feedback. Related PR review state is changes requested. Source: DEMO-102, PR #501.
- DEMO-103 is blocked. Work is blocked waiting for approval of the service account permission change. Source: DEMO-103.
- DEMO-104 is in progress. Initial fix is in progress. Team needs to decide whether relevance tuning should apply globally or only to workspace search. Source: DEMO-104, PR #502.

## Blockers Needing Action

- DEMO-103 is blocked Waiting on IAM approval. Source: DEMO-103.

## Decisions Needed

- Decide whether search relevance tuning is global or workspace-only. (DEMO-104). Source: DEMO-104.

## Risks and Aging Work

- PR #501 is requested review changes linked to DEMO-102. Source: PR #501.
- PR #502 is open for 6 days since June 10, has failing CI linked to DEMO-104. Source: PR #502.

## Carryover From Yesterday

- DEMO-103: Service account permissions need IAM approval before the data exporter can be tested. Source: DEMO-103.
- DEMO-104: Decide whether platform search relevance tuning should apply globally or only to workspace search. Source: DEMO-104.
- Follow up with IAM approver for DEMO-103. Source: DEMO-103.

## Suggested Standup Agenda

1. Confirm next step: DEMO-103 is blocked Waiting on IAM approval.
2. Make decision: Decide whether search relevance tuning is global or workspace-only. (DEMO-104).
3. Review risk: PR #502 is open for 6 days since June 10, has failing CI linked to DEMO-104.
4. Confirm review path for PR #501: Add usage event publisher.
5. Confirm review path for PR #502: Fix platform search scoring configuration.

## Source References

- DEMO-101: https://jira.example.local/browse/DEMO-101
- DEMO-102: https://jira.example.local/browse/DEMO-102
- DEMO-103: https://jira.example.local/browse/DEMO-103
- DEMO-104: https://jira.example.local/browse/DEMO-104
- PR #501: https://github.com/example/example-platform-service/pull/501
- PR #502: https://github.com/example/example-platform-service/pull/502
- PR #503: https://github.com/example/example-platform-service/pull/503
