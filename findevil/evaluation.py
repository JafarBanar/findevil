from __future__ import annotations

from dataclasses import replace

from .orchestrator import AnalysisOrchestrator
from .schemas import CaseRequest
from .store import RunArtifactStore
from .utils import to_jsonable


def evaluate_request(request: CaseRequest) -> dict[str, object]:
    baseline_request = replace(
        request,
        max_iterations=1,
        output_path=f"{request.output_path.rstrip('/')}/iteration-1",
    )
    final_request = replace(
        request,
        output_path=f"{request.output_path.rstrip('/')}/final",
    )

    orchestrator = AnalysisOrchestrator()
    baseline = orchestrator.run(baseline_request)
    final = orchestrator.run(final_request)

    baseline_blocked = sum(
        1
        for issue in baseline.state.issues
        if issue.issue_type == "unsupported_claim" and issue.blocked
    )
    final_blocked = sum(
        1
        for issue in final.state.issues
        if issue.issue_type == "unsupported_claim" and issue.blocked
    )

    summary = {
        "case_id": final.summary.case_id,
        "baseline": to_jsonable(baseline.summary),
        "final": to_jsonable(final.summary),
        "delta": {
            "findings": final.summary.findings_count - baseline.summary.findings_count,
            "confirmed": final.summary.confirmed_count - baseline.summary.confirmed_count,
            "issues": final.summary.issues_count - baseline.summary.issues_count,
            "blocked_unsupported_claims": final_blocked - baseline_blocked,
        },
    }

    store = RunArtifactStore(request.output_path)
    store.prepare()
    store.write_json("evaluation.json", summary)
    return summary
