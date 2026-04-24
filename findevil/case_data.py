from __future__ import annotations

from pathlib import Path
from typing import Any

from .schemas import CaseRequest
from .utils import load_json, safe_slug


class CaseDataset:
    def __init__(self, request: CaseRequest) -> None:
        self.request = request
        self.case_path = Path(request.case_path)
        self.disk_path = Path(request.disk_path)
        self.manifest_path = self.case_path / "manifest.json"
        self.manifest = load_json(self.manifest_path) if self.manifest_path.exists() else {}

    def resolved_case_id(self) -> str:
        return self.request.case_id or self.manifest.get("case_id") or safe_slug(self.case_path.name)

    def expected_artifacts(self) -> set[str]:
        artifacts = self.manifest.get("expected_artifacts", [])
        return {str(item) for item in artifacts}

    def artifact_path(self, tool_name: str) -> Path | None:
        candidates = [
            self.case_path / "artifacts" / f"{tool_name}.json",
            self.case_path / f"{tool_name}.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def load_records(self, tool_name: str) -> list[dict[str, Any]]:
        path = self.artifact_path(tool_name)
        if path is None:
            raise FileNotFoundError(f"No fixture artifact found for tool '{tool_name}'.")
        payload = load_json(path)
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict) and isinstance(payload.get("records"), list):
            return [item for item in payload["records"] if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
        raise ValueError(f"Unsupported payload shape for '{tool_name}'.")

    def disk_access_mode(self) -> str:
        if self.disk_path.is_dir():
            return "mounted_directory"
        if self.disk_path.exists() and self.disk_path.suffix.lower() in {".e01", ".ex01", ".dd", ".raw", ".img"}:
            return "read_only_image"
        if self.disk_path.exists():
            return "existing_path"
        if self.request.tool_backend == "sift-ssh" and self.request.remote_disk_path:
            remote_suffix = Path(self.request.remote_disk_path).suffix.lower()
            if remote_suffix in {".e01", ".ex01", ".dd", ".raw", ".img"}:
                return "remote_read_only_image"
            return "remote_existing_path"
        return "fixture_only"

    def case_metadata(self) -> dict[str, Any]:
        return {
            "case_id": self.resolved_case_id(),
            "profile": self.request.profile,
            "case_path": str(self.case_path),
            "disk_path": str(self.disk_path),
            "memory_path": self.request.memory_path,
            "target_host": self.manifest.get("target_host"),
            "analyst": self.manifest.get("analyst"),
            "expected_artifacts": sorted(self.expected_artifacts()),
            "notes": self.manifest.get("notes", ""),
        }
