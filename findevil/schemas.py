from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CaseRequest:
    case_path: str
    disk_path: str
    output_path: str
    profile: str = "windows"
    case_id: str | None = None
    memory_path: str | None = None
    max_iterations: int = 3
    model_backend: str = "auto"
    tool_backend: str = "fixture"
    remote_host: str | None = None
    remote_user: str | None = None
    remote_port: int = 22
    remote_workdir: str | None = None
    remote_disk_path: str | None = None
    remote_identity_file: str | None = None
    remote_python: str = "python3"
    remote_timeout_sec: int = 120


@dataclass(slots=True)
class EvidenceRecord:
    id: str
    tool_name: str
    kind: str
    summary: str
    raw_artifact_path: str
    data: dict[str, Any]
    confidence: float = 0.5


@dataclass(slots=True)
class ToolResult:
    tool_name: str
    inputs: dict[str, Any]
    raw_artifact_path: str
    evidence_ids: list[str]
    errors: list[str]
    confidence: float
    data: dict[str, Any]
    started_at: str
    completed_at: str
    duration_ms: int
    success: bool


@dataclass(slots=True)
class Finding:
    id: str
    title: str
    status: str
    severity: str
    summary: str
    evidence_ids: list[str]
    sources: list[str]
    confidence: float
    analyst_notes: str


@dataclass(slots=True)
class VerificationIssue:
    id: str
    issue_type: str
    severity: str
    summary: str
    recommended_action: str
    evidence_ids: list[str] = field(default_factory=list)
    finding_id: str | None = None
    blocked: bool = False


@dataclass(slots=True)
class ExecutionEvent:
    timestamp: str
    phase: str
    iteration: int
    action: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RunSummary:
    case_id: str
    status: str
    iterations: int
    findings_count: int
    confirmed_count: int
    inference_count: int
    issues_count: int
    started_at: str
    completed_at: str
    output_path: str


@dataclass(slots=True)
class ToolExecution:
    result: ToolResult
    evidence: list[EvidenceRecord]


@dataclass(slots=True)
class IterationRecord:
    iteration: int
    tools_run: list[str]
    findings: list[Finding]
    issues: list[VerificationIssue]
    rationale: str


@dataclass(slots=True)
class AnalysisState:
    case_id: str
    evidence: dict[str, EvidenceRecord] = field(default_factory=dict)
    tool_results: dict[str, ToolResult] = field(default_factory=dict)
    tool_iterations: dict[str, int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    issues: list[VerificationIssue] = field(default_factory=list)
    iteration_history: list[IterationRecord] = field(default_factory=list)
