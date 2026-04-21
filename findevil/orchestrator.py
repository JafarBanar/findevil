from __future__ import annotations

from dataclasses import dataclass

from .case_data import CaseDataset
from .reasoning import ALL_CORE_TOOLS, select_backend
from .reporting import render_report
from .schemas import (
    AnalysisState,
    CaseRequest,
    ExecutionEvent,
    IterationRecord,
    RunSummary,
    VerificationIssue,
)
from .store import RunArtifactStore
from .tools import ToolContext, ToolRegistry
from .utils import now_utc_iso, stable_id, to_jsonable
from .verification import verify_findings


@dataclass(slots=True)
class AnalysisResult:
    summary: RunSummary
    state: AnalysisState


class AnalysisOrchestrator:
    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or ToolRegistry()

    def run(self, request: CaseRequest) -> AnalysisResult:
        started_at = now_utc_iso()
        store = RunArtifactStore(request.output_path)
        store.prepare()
        dataset = CaseDataset(request)
        state = AnalysisState(case_id=dataset.resolved_case_id())
        backend = select_backend(request.model_backend)

        self._log_event(
            store,
            phase="intake",
            iteration=0,
            action="start",
            message="Starting analysis run.",
            data={"case_id": state.case_id, "backend": backend.name},
        )

        iterations_used = 0
        for iteration in range(1, request.max_iterations + 1):
            iterations_used = iteration
            plan_tools, rationale = backend.plan_collection(request, state, iteration)
            self._log_event(
                store,
                phase="plan",
                iteration=iteration,
                action="plan_collection",
                message=rationale,
                data={"tools": plan_tools},
            )
            if not plan_tools:
                break

            for tool_name in plan_tools:
                execution = self.registry.execute(
                    tool_name,
                    ToolContext(
                        request=request,
                        dataset=dataset,
                        store=store,
                        state=state,
                        iteration=iteration,
                    ),
                )
                state.tool_results[tool_name] = execution.result
                state.tool_iterations[tool_name] = iteration
                for item in execution.evidence:
                    state.evidence[item.id] = item

                store.append_tool_call(
                    {
                        "timestamp": now_utc_iso(),
                        "iteration": iteration,
                        "tool_name": tool_name,
                        "inputs": execution.result.inputs,
                        "success": execution.result.success,
                        "errors": execution.result.errors,
                        "evidence_ids": execution.result.evidence_ids,
                        "raw_artifact_path": execution.result.raw_artifact_path,
                    }
                )
                self._log_event(
                    store,
                    phase="collect",
                    iteration=iteration,
                    action="tool_executed",
                    message=f"Executed {tool_name}.",
                    data={
                        "success": execution.result.success,
                        "evidence_count": len(execution.result.evidence_ids),
                        "errors": execution.result.errors,
                    },
                )

            candidate_findings = backend.synthesize_findings(state, iteration)
            verified_findings, verification_issues = verify_findings(candidate_findings, state)
            tool_failure_issues = self._tool_failure_issues(plan_tools, state)
            state.findings = verified_findings
            state.issues = verification_issues + tool_failure_issues
            state.iteration_history.append(
                IterationRecord(
                    iteration=iteration,
                    tools_run=plan_tools,
                    findings=list(verified_findings),
                    issues=list(state.issues),
                    rationale=rationale,
                )
            )
            self._log_event(
                store,
                phase="verify",
                iteration=iteration,
                action="verification_complete",
                message="Verification completed for synthesized findings.",
                data={
                    "findings_count": len(verified_findings),
                    "issues_count": len(state.issues),
                },
            )

            if not self._should_self_correct(iteration, request.max_iterations, state):
                break

            followup = [tool for tool in ALL_CORE_TOOLS if tool not in state.tool_results]
            self._log_event(
                store,
                phase="self_correct",
                iteration=iteration,
                action="queue_followup",
                message="Verification requested additional corroboration.",
                data={"remaining_tools": followup},
            )

        completed_at = now_utc_iso()
        summary = RunSummary(
            case_id=state.case_id,
            status="completed",
            iterations=iterations_used,
            findings_count=len(state.findings),
            confirmed_count=sum(1 for item in state.findings if item.status == "confirmed"),
            inference_count=sum(1 for item in state.findings if item.status == "inference"),
            issues_count=len(state.issues),
            started_at=started_at,
            completed_at=completed_at,
            output_path=request.output_path,
        )
        self._log_event(
            store,
            phase="finalize",
            iteration=iterations_used,
            action="write_outputs",
            message="Persisting final run artifacts.",
            data=to_jsonable(summary),
        )
        self._write_outputs(store, request, state, summary)
        return AnalysisResult(summary=summary, state=state)

    def _should_self_correct(self, iteration: int, max_iterations: int, state: AnalysisState) -> bool:
        if iteration >= max_iterations or not state.issues:
            return False
        remaining_tools = [tool for tool in ALL_CORE_TOOLS if tool not in state.tool_results]
        if remaining_tools:
            return True
        return any(issue.issue_type == "tool_failure" and not issue.blocked for issue in state.issues)

    def _tool_failure_issues(self, tools_run: list[str], state: AnalysisState) -> list[VerificationIssue]:
        issues: list[VerificationIssue] = []
        for tool_name in tools_run:
            result = state.tool_results[tool_name]
            if not result.errors:
                continue
            issues.append(
                VerificationIssue(
                    id=stable_id("tool-failure", f"{tool_name}:{','.join(result.errors)}"),
                    finding_id=None,
                    issue_type="tool_failure",
                    severity="medium",
                    summary=f"Tool {tool_name} did not return fixture data and needs fallback handling.",
                    recommended_action=f"retry:{tool_name}",
                    evidence_ids=[],
                    blocked=False,
                )
            )
        return issues

    def _write_outputs(
        self,
        store: RunArtifactStore,
        request: CaseRequest,
        state: AnalysisState,
        summary: RunSummary,
    ) -> None:
        store.write_json("findings.json", state.findings)
        store.write_json(
            "run_metadata.json",
            {
                "request": request,
                "summary": summary,
                "issues": state.issues,
                "iteration_history": state.iteration_history,
                "tool_results": list(state.tool_results.values()),
            },
        )
        store.write_text("report.md", render_report(request, summary, state, state.findings, state.issues))

    def _log_event(
        self,
        store: RunArtifactStore,
        phase: str,
        iteration: int,
        action: str,
        message: str,
        data: dict[str, object],
    ) -> None:
        store.append_event(
            ExecutionEvent(
                timestamp=now_utc_iso(),
                phase=phase,
                iteration=iteration,
                action=action,
                message=message,
                data=data,
            )
        )

