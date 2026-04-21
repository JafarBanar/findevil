from __future__ import annotations

from pathlib import PureWindowsPath
from typing import Iterable

from .schemas import AnalysisState, CaseRequest, EvidenceRecord, Finding, VerificationIssue
from .utils import safe_slug


ALL_CORE_TOOLS = [
    "case_info",
    "mount_image_readonly",
    "user_logons",
    "browser_history",
    "prefetch_summary",
    "amcache_summary",
    "timeline_mft",
    "registry_autoruns",
    "scheduled_tasks",
    "yara_scan",
]

BASELINE_TOOLS = [
    "case_info",
    "mount_image_readonly",
    "user_logons",
    "browser_history",
    "prefetch_summary",
]

SUSPICIOUS_EXECUTABLES = {
    "powershell.exe",
    "pwsh.exe",
    "cmd.exe",
    "wscript.exe",
    "cscript.exe",
    "mshta.exe",
    "rundll32.exe",
    "regsvr32.exe",
}

SUSPICIOUS_PATH_MARKERS = ("\\appdata\\", "\\temp\\", "\\downloads\\", "\\programdata\\")
SUSPICIOUS_URL_MARKERS = ("invoice", "update", "login", "verify", "cdn-", ".zip", ".js", ".hta", ".ps1")


def _tool_evidence(state: AnalysisState, tool_name: str) -> list[EvidenceRecord]:
    return [item for item in state.evidence.values() if item.tool_name == tool_name]


def _unique_sources(evidence_ids: Iterable[str], state: AnalysisState) -> list[str]:
    sources = {state.evidence[evidence_id].tool_name for evidence_id in evidence_ids if evidence_id in state.evidence}
    return sorted(sources)


def _windows_name(path: str | None) -> str:
    if not path:
        return ""
    return PureWindowsPath(path).name.lower()


def _is_suspicious_path(value: str | None) -> bool:
    return bool(value) and any(marker in value.lower() for marker in SUSPICIOUS_PATH_MARKERS)


def _is_suspicious_url(url: str | None) -> bool:
    return bool(url) and any(marker in url.lower() for marker in SUSPICIOUS_URL_MARKERS)


class LocalReasoningBackend:
    name = "local"

    def plan_collection(
        self,
        request: CaseRequest,
        state: AnalysisState,
        iteration: int,
    ) -> tuple[list[str], str]:
        if iteration == 1:
            tools = [tool for tool in BASELINE_TOOLS if tool not in state.tool_results]
            return tools, "Baseline triage starts with user activity, browser evidence, and execution traces."

        remaining = [tool for tool in ALL_CORE_TOOLS if tool not in state.tool_results]
        if not remaining:
            return [], "No additional typed tools remain."

        selected: list[str] = []
        for issue in state.issues:
            if issue.issue_type in {"missing_corroboration", "unsupported_claim"}:
                for tool in ("amcache_summary", "timeline_mft", "yara_scan", "registry_autoruns", "scheduled_tasks"):
                    if tool in remaining and tool not in selected:
                        selected.append(tool)
            if issue.issue_type == "tool_failure":
                tool_name = issue.recommended_action.replace("retry:", "", 1)
                if tool_name in remaining and tool_name not in selected:
                    selected.append(tool_name)

        if not selected:
            selected = remaining

        return selected, "Self-correction expands collection to corroborate or recover unsupported claims."

    def synthesize_findings(self, state: AnalysisState, iteration: int) -> list[Finding]:
        findings: list[Finding] = []
        findings.extend(self._execution_findings(state, iteration))
        findings.extend(self._delivery_findings(state, iteration))
        findings.extend(self._persistence_findings(state, iteration))
        findings.extend(self._detection_findings(state, iteration))
        findings.extend(self._speculative_findings(state, iteration))
        return findings

    def _execution_findings(self, state: AnalysisState, iteration: int) -> list[Finding]:
        evidence = []
        labels: list[str] = []
        for item in _tool_evidence(state, "prefetch_summary") + _tool_evidence(state, "amcache_summary"):
            executable = str(item.data.get("executable", item.data.get("program_name", ""))).lower()
            path = str(item.data.get("path", item.data.get("command_line", "")))
            if executable in SUSPICIOUS_EXECUTABLES or _is_suspicious_path(path) or "bypass" in path.lower():
                evidence.append(item.id)
                labels.append(item.summary)

        if not evidence:
            return []

        title = "Suspicious script execution observed on the endpoint"
        return [
            Finding(
                id=safe_slug(title),
                title=title,
                status="needs_review",
                severity="high",
                summary="Execution telemetry suggests a script or living-off-the-land binary ran from a suspicious location.",
                evidence_ids=sorted(set(evidence)),
                sources=_unique_sources(evidence, state),
                confidence=min(0.55 + (0.1 * len(set(evidence))), 0.9),
                analyst_notes=f"Iteration {iteration}: {labels[0]}",
            )
        ]

    def _delivery_findings(self, state: AnalysisState, iteration: int) -> list[Finding]:
        browser_hits = [
            item
            for item in _tool_evidence(state, "browser_history")
            if _is_suspicious_url(str(item.data.get("url"))) or _is_suspicious_path(str(item.data.get("downloaded_path")))
        ]
        if not browser_hits:
            return []

        evidence = [item.id for item in browser_hits]
        correlated_name = ""
        for browser_hit in browser_hits:
            downloaded_path = str(browser_hit.data.get("downloaded_path", ""))
            candidate_name = _windows_name(downloaded_path)
            if not candidate_name:
                continue
            for item in _tool_evidence(state, "timeline_mft") + _tool_evidence(state, "yara_scan"):
                values = " ".join(str(value) for value in item.data.values()).lower()
                if candidate_name and candidate_name in values:
                    evidence.append(item.id)
                    correlated_name = candidate_name

        summary = "Browser activity suggests a suspicious payload delivery path."
        if correlated_name:
            summary = f"Browser activity and on-disk artifacts both reference {correlated_name}, suggesting payload delivery."

        title = "Likely web delivery of a suspicious payload"
        return [
            Finding(
                id=safe_slug(title),
                title=title,
                status="needs_review",
                severity="medium",
                summary=summary,
                evidence_ids=sorted(set(evidence)),
                sources=_unique_sources(evidence, state),
                confidence=0.5 if len(set(evidence)) == len(browser_hits) else 0.8,
                analyst_notes=f"Iteration {iteration}: {browser_hits[0].summary}",
            )
        ]

    def _persistence_findings(self, state: AnalysisState, iteration: int) -> list[Finding]:
        evidence = []
        notes: list[str] = []
        for item in _tool_evidence(state, "registry_autoruns") + _tool_evidence(state, "scheduled_tasks"):
            value_blob = " ".join(str(value) for value in item.data.values())
            if _is_suspicious_path(value_blob) or "hidden" in value_blob.lower():
                evidence.append(item.id)
                notes.append(item.summary)

        if not evidence:
            return []

        title = "Persistence mechanism likely established on the host"
        return [
            Finding(
                id=safe_slug(title),
                title=title,
                status="needs_review",
                severity="high",
                summary="Persistence-related telemetry points to a suspicious autorun or scheduled task.",
                evidence_ids=sorted(set(evidence)),
                sources=_unique_sources(evidence, state),
                confidence=min(0.65 + (0.1 * len(set(evidence))), 0.95),
                analyst_notes=f"Iteration {iteration}: {notes[0]}",
            )
        ]

    def _detection_findings(self, state: AnalysisState, iteration: int) -> list[Finding]:
        hits = _tool_evidence(state, "yara_scan")
        if not hits:
            return []

        title = "Known suspicious artifact matched detection rules"
        return [
            Finding(
                id=safe_slug(title),
                title=title,
                status="needs_review",
                severity="high",
                summary="At least one artifact matched a detection signature during scanning.",
                evidence_ids=[item.id for item in hits],
                sources=_unique_sources([item.id for item in hits], state),
                confidence=0.9,
                analyst_notes=f"Iteration {iteration}: {hits[0].summary}",
            )
        ]

    def _speculative_findings(self, state: AnalysisState, iteration: int) -> list[Finding]:
        browser_hits = [
            item
            for item in _tool_evidence(state, "browser_history")
            if _is_suspicious_url(str(item.data.get("url")))
        ]
        if not browser_hits:
            return []

        title = "Credential theft likely followed the suspicious browser session"
        return [
            Finding(
                id=safe_slug(title),
                title=title,
                status="needs_review",
                severity="medium",
                summary="The browsing pattern resembles phishing delivery, but the claim must be blocked unless stronger evidence appears.",
                evidence_ids=[browser_hits[0].id],
                sources=_unique_sources([browser_hits[0].id], state),
                confidence=0.35,
                analyst_notes=f"Iteration {iteration}: speculative hypothesis generated for verifier testing.",
            )
        ]


def select_backend(model_backend: str) -> LocalReasoningBackend:
    return LocalReasoningBackend()
