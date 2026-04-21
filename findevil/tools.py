from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import json
import time

from .remote import RemoteSIFTRunner
from .case_data import CaseDataset
from .schemas import AnalysisState, CaseRequest, EvidenceRecord, ToolExecution, ToolResult
from .store import RunArtifactStore
from .utils import now_utc_iso, stable_id


DEFAULT_KIND_BY_TOOL = {
    "case_info": "case_context",
    "mount_image_readonly": "case_access",
    "timeline_mft": "timeline_event",
    "prefetch_summary": "process_execution",
    "amcache_summary": "program_execution",
    "registry_autoruns": "persistence",
    "scheduled_tasks": "persistence",
    "user_logons": "logon",
    "browser_history": "browser_activity",
    "yara_scan": "detection",
    "vol_process_tree": "memory_process",
    "vol_netscan": "network",
}


@dataclass(slots=True)
class ToolContext:
    request: CaseRequest
    dataset: CaseDataset
    store: RunArtifactStore
    state: AnalysisState
    iteration: int


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[ToolContext, dict[str, Any]], ToolExecution]


def _summary_for_record(tool_name: str, record: dict[str, Any]) -> str:
    if tool_name == "prefetch_summary":
        executable = record.get("executable", "unknown executable")
        return f"{executable} executed {record.get('run_count', '?')} times."
    if tool_name == "amcache_summary":
        return f"Amcache recorded {record.get('program_name', record.get('path', 'unknown program'))}."
    if tool_name == "registry_autoruns":
        return f"Autorun entry {record.get('entry', 'unknown entry')} launches {record.get('value', 'unknown value')}."
    if tool_name == "scheduled_tasks":
        return f"Scheduled task {record.get('task_name', 'unknown task')} runs {record.get('command', 'unknown command')}."
    if tool_name == "browser_history":
        return f"Visited {record.get('url', 'unknown URL')}."
    if tool_name == "timeline_mft":
        return f"{record.get('action', 'timeline event')} for {record.get('path', 'unknown path')}."
    if tool_name == "user_logons":
        return f"User {record.get('user', 'unknown user')} logged on via {record.get('logon_type', 'unknown logon type')}."
    if tool_name == "yara_scan":
        return f"YARA rule {record.get('rule', 'unknown rule')} matched {record.get('file_path', 'unknown file')}."
    if tool_name == "case_info":
        return f"Loaded case metadata for {record.get('case_id', 'unknown case')}."
    if tool_name == "mount_image_readonly":
        return f"Case source prepared in {record.get('access_mode', 'unknown')} mode."
    return json.dumps(record, sort_keys=True)


def _build_evidence_records(
    tool_name: str,
    records: list[dict[str, Any]],
    raw_artifact_path: str,
) -> list[EvidenceRecord]:
    evidence: list[EvidenceRecord] = []
    default_kind = DEFAULT_KIND_BY_TOOL[tool_name]
    for index, record in enumerate(records, start=1):
        serialized = json.dumps(record, sort_keys=True)
        evidence_id = record.get("evidence_id") or stable_id(f"{tool_name}-{index}", serialized)
        evidence.append(
            EvidenceRecord(
                id=evidence_id,
                tool_name=tool_name,
                kind=str(record.get("kind", default_kind)),
                summary=_summary_for_record(tool_name, record),
                raw_artifact_path=raw_artifact_path,
                data=record,
                confidence=float(record.get("confidence", 0.6)),
            )
        )
    return evidence


def _finish_tool_result(
    tool_name: str,
    started_at: str,
    start_time: float,
    inputs: dict[str, Any],
    raw_payload: dict[str, Any],
    evidence: list[EvidenceRecord],
    errors: list[str],
    confidence: float,
    store: RunArtifactStore,
    raw_artifact_path: str | None = None,
) -> ToolExecution:
    artifact_path = raw_artifact_path or store.write_raw_json(tool_name, raw_payload)
    copied_evidence = [
        EvidenceRecord(
            id=item.id,
            tool_name=item.tool_name,
            kind=item.kind,
            summary=item.summary,
            raw_artifact_path=artifact_path,
            data=item.data,
            confidence=item.confidence,
        )
        for item in evidence
    ]
    completed_at = now_utc_iso()
    duration_ms = int((time.perf_counter() - start_time) * 1000)
    result = ToolResult(
        tool_name=tool_name,
        inputs=inputs,
        raw_artifact_path=artifact_path,
        evidence_ids=[item.id for item in copied_evidence],
        errors=errors,
        confidence=confidence,
        data={
            "record_count": len(copied_evidence),
            "records": [item.data for item in copied_evidence],
        },
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        success=not errors,
    )
    return ToolExecution(result=result, evidence=copied_evidence)


def _load_fixture_tool(tool_name: str, context: ToolContext, inputs: dict[str, Any]) -> ToolExecution:
    started_at = now_utc_iso()
    start_time = time.perf_counter()
    errors: list[str] = []
    try:
        records = context.dataset.load_records(tool_name)
    except FileNotFoundError as exc:
        records = []
        errors.append(str(exc))
    except ValueError as exc:
        records = []
        errors.append(str(exc))

    raw_payload = {
        "tool_name": tool_name,
        "inputs": inputs,
        "mode": "fixture_artifact",
        "records": records,
        "errors": errors,
    }
    raw_artifact_path = context.store.write_raw_json(tool_name, raw_payload)
    evidence = _build_evidence_records(tool_name, records, raw_artifact_path)
    return _finish_tool_result(
        tool_name=tool_name,
        started_at=started_at,
        start_time=start_time,
        inputs=inputs,
        raw_payload=raw_payload,
        evidence=evidence,
        errors=errors,
        confidence=0.85 if records else 0.3,
        store=context.store,
        raw_artifact_path=raw_artifact_path,
    )


def _load_remote_tool(tool_name: str, context: ToolContext, inputs: dict[str, Any]) -> ToolExecution:
    started_at = now_utc_iso()
    start_time = time.perf_counter()
    runner = RemoteSIFTRunner(context.request)
    remote = runner.run_tool(tool_name)
    errors = list(remote.payload.get("errors", []))
    records = [
        item
        for item in remote.payload.get("records", [])
        if isinstance(item, dict)
    ]
    raw_payload = {
        "tool_name": tool_name,
        "inputs": inputs,
        "mode": "sift_ssh",
        "ssh_command": remote.command,
        "exit_code": remote.exit_code,
        "stdout": remote.stdout,
        "stderr": remote.stderr,
        "records": records,
        "errors": errors,
    }
    raw_artifact_path = context.store.write_raw_json(tool_name, raw_payload)
    evidence = _build_evidence_records(tool_name, records, raw_artifact_path)
    confidence = 0.9 if records and not errors else 0.35
    return _finish_tool_result(
        tool_name=tool_name,
        started_at=started_at,
        start_time=start_time,
        inputs=inputs,
        raw_payload=raw_payload,
        evidence=evidence,
        errors=errors,
        confidence=confidence,
        store=context.store,
        raw_artifact_path=raw_artifact_path,
    )


def _load_tool(tool_name: str, context: ToolContext, inputs: dict[str, Any]) -> ToolExecution:
    runner = RemoteSIFTRunner(context.request)
    if runner.supports(tool_name):
        return _load_remote_tool(tool_name, context, inputs)
    return _load_fixture_tool(tool_name, context, inputs)


def case_info_tool(context: ToolContext, inputs: dict[str, Any]) -> ToolExecution:
    started_at = now_utc_iso()
    start_time = time.perf_counter()
    metadata = context.dataset.case_metadata()
    raw_payload = {
        "tool_name": "case_info",
        "inputs": inputs,
        "metadata": metadata,
    }
    raw_artifact_path = context.store.write_raw_json("case_info", raw_payload)
    evidence = _build_evidence_records("case_info", [metadata], raw_artifact_path)
    return _finish_tool_result(
        tool_name="case_info",
        started_at=started_at,
        start_time=start_time,
        inputs=inputs,
        raw_payload=raw_payload,
        evidence=evidence,
        errors=[],
        confidence=0.95,
        store=context.store,
        raw_artifact_path=raw_artifact_path,
    )


def mount_image_readonly_tool(context: ToolContext, inputs: dict[str, Any]) -> ToolExecution:
    started_at = now_utc_iso()
    start_time = time.perf_counter()
    access_mode = context.dataset.disk_access_mode()
    mount_record = {
        "access_mode": access_mode,
        "disk_path": context.request.disk_path,
        "mount_path": context.request.case_path if access_mode == "fixture_only" else context.request.disk_path,
        "tool_backend": context.request.tool_backend,
        "remote_host": context.request.remote_host,
        "remote_disk_path": context.request.remote_disk_path,
        "read_only_guardrails": [
            "No write-capable shell execution is exposed.",
            "Tools only read fixture artifacts or case metadata.",
            "All tool output is copied into run-local artifacts for auditability.",
        ],
        "kind": "case_access",
    }
    raw_payload = {
        "tool_name": "mount_image_readonly",
        "inputs": inputs,
        "record": mount_record,
    }
    raw_artifact_path = context.store.write_raw_json("mount_image_readonly", raw_payload)
    evidence = _build_evidence_records("mount_image_readonly", [mount_record], raw_artifact_path)
    return _finish_tool_result(
        tool_name="mount_image_readonly",
        started_at=started_at,
        start_time=start_time,
        inputs=inputs,
        raw_payload=raw_payload,
        evidence=evidence,
        errors=[],
        confidence=0.95,
        store=context.store,
        raw_artifact_path=raw_artifact_path,
    )


class ToolRegistry:
    def __init__(self) -> None:
        self._specs = self._build_specs()

    def _build_specs(self) -> dict[str, ToolSpec]:
        return {
            "case_info": ToolSpec(
                name="case_info",
                description="Load case metadata and target host context.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=case_info_tool,
            ),
            "mount_image_readonly": ToolSpec(
                name="mount_image_readonly",
                description="Prepare read-only case access and record guardrails.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=mount_image_readonly_tool,
            ),
            "timeline_mft": ToolSpec(
                name="timeline_mft",
                description="Load MFT-style timeline records.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_tool("timeline_mft", context, inputs),
            ),
            "prefetch_summary": ToolSpec(
                name="prefetch_summary",
                description="Load execution evidence from Prefetch summaries.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_tool("prefetch_summary", context, inputs),
            ),
            "amcache_summary": ToolSpec(
                name="amcache_summary",
                description="Load installed and executed program evidence from Amcache.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_fixture_tool("amcache_summary", context, inputs),
            ),
            "registry_autoruns": ToolSpec(
                name="registry_autoruns",
                description="Load autorun persistence entries from the registry.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_tool("registry_autoruns", context, inputs),
            ),
            "scheduled_tasks": ToolSpec(
                name="scheduled_tasks",
                description="Load suspicious scheduled task executions.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_tool("scheduled_tasks", context, inputs),
            ),
            "user_logons": ToolSpec(
                name="user_logons",
                description="Load user logon history for the endpoint.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_fixture_tool("user_logons", context, inputs),
            ),
            "browser_history": ToolSpec(
                name="browser_history",
                description="Load browser history and download activity.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_fixture_tool("browser_history", context, inputs),
            ),
            "yara_scan": ToolSpec(
                name="yara_scan",
                description="Load YARA scan hits or detection matches.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_fixture_tool("yara_scan", context, inputs),
            ),
            "vol_process_tree": ToolSpec(
                name="vol_process_tree",
                description="Optional phase-2 memory process tree evidence.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_fixture_tool("vol_process_tree", context, inputs),
            ),
            "vol_netscan": ToolSpec(
                name="vol_netscan",
                description="Optional phase-2 memory network evidence.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
                handler=lambda context, inputs: _load_fixture_tool("vol_netscan", context, inputs),
            ),
        }

    def names(self) -> list[str]:
        return list(self._specs)

    def specs(self) -> list[ToolSpec]:
        return list(self._specs.values())

    def get(self, name: str) -> ToolSpec:
        return self._specs[name]

    def execute(self, name: str, context: ToolContext, inputs: dict[str, Any] | None = None) -> ToolExecution:
        if name not in self._specs:
            raise KeyError(f"Unknown tool '{name}'.")
        return self._specs[name].handler(context, inputs or {})
