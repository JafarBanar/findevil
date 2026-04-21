from __future__ import annotations

from collections import Counter

from .schemas import AnalysisState, CaseRequest, Finding, RunSummary, VerificationIssue


def render_report(
    request: CaseRequest,
    summary: RunSummary,
    state: AnalysisState,
    findings: list[Finding],
    issues: list[VerificationIssue],
) -> str:
    lines = [
        "# CaseTrace Report",
        "",
        "## Case",
        f"- Case ID: `{summary.case_id}`",
        f"- Profile: `{request.profile}`",
        f"- Disk: `{request.disk_path}`",
        f"- Memory: `{request.memory_path or 'not provided'}`",
        f"- Iterations: `{summary.iterations}`",
        f"- Output: `{summary.output_path}`",
        "",
        "## Findings",
    ]

    if not findings:
        lines.append("- No findings were retained after verification.")
    else:
        for finding in findings:
            evidence_list = ", ".join(f"`{item}`" for item in finding.evidence_ids)
            source_list = ", ".join(finding.sources)
            lines.extend(
                [
                    f"### {finding.title}",
                    f"- Status: `{finding.status}`",
                    f"- Severity: `{finding.severity}`",
                    f"- Confidence: `{finding.confidence:.2f}`",
                    f"- Sources: {source_list}",
                    f"- Evidence: {evidence_list}",
                    f"- Summary: {finding.summary}",
                    f"- Notes: {finding.analyst_notes}",
                    "",
                ]
            )

    lines.extend(["## Verification", ""])
    if not issues:
        lines.append("- No verification issues remained at the end of the run.")
    else:
        for issue in issues:
            evidence_list = ", ".join(f"`{item}`" for item in issue.evidence_ids) or "none"
            lines.append(
                f"- `{issue.severity}` {issue.issue_type}: {issue.summary} Evidence: {evidence_list}. Action: {issue.recommended_action}."
            )

    lines.extend(["", "## Tool Coverage", ""])
    counts = Counter(result.tool_name for result in state.tool_results.values())
    if not counts:
        lines.append("- No tools were executed.")
    else:
        for tool_name in sorted(counts):
            result = state.tool_results[tool_name]
            lines.append(
                f"- `{tool_name}`: success={str(result.success).lower()} evidence={len(result.evidence_ids)} errors={len(result.errors)}"
            )

    lines.extend(["", "## Iterations", ""])
    for record in state.iteration_history:
        lines.append(
            f"- Iteration {record.iteration}: tools={', '.join(record.tools_run)} findings={len(record.findings)} issues={len(record.issues)}"
        )
    return "\n".join(lines) + "\n"

