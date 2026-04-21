from __future__ import annotations

from typing import Iterable

from .schemas import AnalysisState, Finding, VerificationIssue
from .utils import stable_id


def _score_finding(finding: Finding, state: AnalysisState) -> tuple[int, set[str]]:
    kinds = {
        state.evidence[evidence_id].kind
        for evidence_id in finding.evidence_ids
        if evidence_id in state.evidence
    }
    score = 0
    if "detection" in kinds:
        score += 2
    if "persistence" in kinds:
        score += 2
    if "process_execution" in kinds or "program_execution" in kinds:
        score += 1
    if "timeline_event" in kinds:
        score += 1
    if "browser_activity" in kinds:
        score += 1
    tool_names = {
        state.evidence[evidence_id].tool_name
        for evidence_id in finding.evidence_ids
        if evidence_id in state.evidence
    }
    if len(tool_names) > 1:
        score += 1
    return score, kinds


def _make_issue(
    finding: Finding | None,
    issue_type: str,
    severity: str,
    summary: str,
    recommended_action: str,
    evidence_ids: Iterable[str],
    blocked: bool = False,
) -> VerificationIssue:
    payload = f"{finding.id if finding else 'global'}:{issue_type}:{summary}"
    return VerificationIssue(
        id=stable_id("verification", payload),
        finding_id=finding.id if finding else None,
        issue_type=issue_type,
        severity=severity,
        summary=summary,
        recommended_action=recommended_action,
        evidence_ids=list(evidence_ids),
        blocked=blocked,
    )


def verify_findings(
    findings: list[Finding],
    state: AnalysisState,
) -> tuple[list[Finding], list[VerificationIssue]]:
    verified: list[Finding] = []
    issues: list[VerificationIssue] = []

    for finding in findings:
        present_ids = [evidence_id for evidence_id in finding.evidence_ids if evidence_id in state.evidence]
        if not present_ids:
            issues.append(
                _make_issue(
                    finding,
                    issue_type="unsupported_claim",
                    severity="high",
                    summary=f"Removed unsupported finding '{finding.title}' because it had no backing evidence.",
                    recommended_action="gather corroborating evidence",
                    evidence_ids=[],
                    blocked=True,
                )
            )
            continue

        finding.evidence_ids = present_ids
        score, kinds = _score_finding(finding, state)

        if "credential theft" in finding.title.lower():
            issues.append(
                _make_issue(
                    finding,
                    issue_type="unsupported_claim",
                    severity="high",
                    summary=f"Blocked speculative finding '{finding.title}' because no credential-access evidence exists.",
                    recommended_action="gather corroborating evidence",
                    evidence_ids=present_ids,
                    blocked=True,
                )
            )
            continue

        if "delivery" in finding.title.lower() and not ({"timeline_event", "detection"} & kinds):
            issues.append(
                _make_issue(
                    finding,
                    issue_type="missing_corroboration",
                    severity="medium",
                    summary=f"Delivery finding '{finding.title}' lacks on-disk corroboration.",
                    recommended_action="gather corroborating evidence",
                    evidence_ids=present_ids,
                )
            )

        if "execution" in finding.title.lower() and not ({"process_execution", "program_execution"} & kinds):
            issues.append(
                _make_issue(
                    finding,
                    issue_type="unsupported_claim",
                    severity="high",
                    summary=f"Removed unsupported execution finding '{finding.title}'.",
                    recommended_action="gather corroborating evidence",
                    evidence_ids=present_ids,
                    blocked=True,
                )
            )
            continue

        if score >= 3:
            finding.status = "confirmed"
            finding.confidence = max(finding.confidence, 0.85)
        elif score >= 2:
            finding.status = "inference"
            finding.confidence = min(finding.confidence, 0.74)
        else:
            finding.status = "needs_review"
            finding.confidence = min(finding.confidence, 0.5)

        verified.append(finding)

    return verified, issues
