from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any
import json
import subprocess
import time

from .schemas import CaseRequest


REMOTE_SUPPORTED_TOOLS = {
    "amcache_summary",
    "browser_history",
    "timeline_mft",
    "prefetch_summary",
    "registry_autoruns",
    "scheduled_tasks",
    "user_logons",
    "yara_scan",
}
PLACEHOLDER_HOSTS = {"your-sift-host"}


@dataclass(slots=True)
class RemoteExecutionResult:
    tool_name: str
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    payload: dict[str, Any]


class RemoteSIFTRunner:
    def __init__(self, request: CaseRequest) -> None:
        self.request = request

    def is_enabled(self) -> bool:
        return self.request.tool_backend == "sift-ssh"

    def supports(self, tool_name: str) -> bool:
        return self.is_enabled() and tool_name in REMOTE_SUPPORTED_TOOLS

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.request.remote_host:
            errors.append("Missing --remote-host for sift-ssh backend.")
        elif self.request.remote_host in PLACEHOLDER_HOSTS:
            errors.append("Replace the placeholder remote host with your real SIFT hostname or IP.")
        if not self.request.remote_workdir:
            errors.append("Missing --remote-workdir for sift-ssh backend.")
        return errors

    def run_tool(self, tool_name: str) -> RemoteExecutionResult:
        errors = self.validate()
        if errors:
            joined = " ".join(errors)
            return RemoteExecutionResult(
                tool_name=tool_name,
                command=[],
                exit_code=2,
                stdout="",
                stderr=joined,
                duration_ms=0,
                payload={"tool_name": tool_name, "records": [], "errors": errors},
            )

        command = self._build_command(tool_name)
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.request.remote_timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return self._timeout_result(tool_name, command, start, exc)
        duration_ms = int((time.perf_counter() - start) * 1000)
        payload = self._parse_payload(tool_name, completed.stdout, completed.stderr, completed.returncode, duration_ms)
        return RemoteExecutionResult(
            tool_name=tool_name,
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
            payload=payload,
        )

    def run_self_test(self) -> RemoteExecutionResult:
        errors = self.validate()
        if errors:
            joined = " ".join(errors)
            return RemoteExecutionResult(
                tool_name="self_test",
                command=[],
                exit_code=2,
                stdout="",
                stderr=joined,
                duration_ms=0,
                payload={"tool_name": "self_test", "errors": errors},
            )

        command = self._build_self_test_command()
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.request.remote_timeout_sec,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return self._timeout_result("self_test", command, start, exc)
        duration_ms = int((time.perf_counter() - start) * 1000)
        payload = self._parse_payload("self_test", completed.stdout, completed.stderr, completed.returncode, duration_ms)
        return RemoteExecutionResult(
            tool_name="self_test",
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=duration_ms,
            payload=payload,
        )

    def _timeout_result(
        self,
        tool_name: str,
        command: list[str],
        start: float,
        exc: subprocess.TimeoutExpired,
    ) -> RemoteExecutionResult:
        duration_ms = int((time.perf_counter() - start) * 1000)
        stdout = self._decode_timeout_stream(exc.stdout)
        stderr = self._decode_timeout_stream(exc.stderr)
        message = f"Remote command timed out after {self.request.remote_timeout_sec} seconds."
        return RemoteExecutionResult(
            tool_name=tool_name,
            command=command,
            exit_code=124,
            stdout=stdout,
            stderr=stderr or message,
            duration_ms=duration_ms,
            payload={
                "tool_name": tool_name,
                "records": [],
                "errors": [message],
                "remote_mode": "sift_ssh",
                "duration_ms": duration_ms,
            },
        )

    def _decode_timeout_stream(self, value: str | bytes | None) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return value

    def _build_command(self, tool_name: str) -> list[str]:
        target = self.request.remote_host
        if self.request.remote_user:
            target = f"{self.request.remote_user}@{target}"

        remote_script = str(PurePosixPath(self.request.remote_workdir or ".") / "scripts" / "sift_tool_bridge.py")
        remote_disk = self.request.remote_disk_path or self.request.disk_path
        command = self._base_ssh_command()
        command.extend(
            [
                target,
                self.request.remote_python,
                remote_script,
                "--tool",
                tool_name,
                "--disk",
                remote_disk,
                "--profile",
                self.request.profile,
            ]
        )
        return command

    def _build_self_test_command(self) -> list[str]:
        target = self.request.remote_host
        if self.request.remote_user:
            target = f"{self.request.remote_user}@{target}"
        remote_script = str(PurePosixPath(self.request.remote_workdir or ".") / "scripts" / "sift_tool_bridge.py")
        command = self._base_ssh_command()
        command.extend([target, self.request.remote_python, remote_script, "--self-test"])
        return command

    def _base_ssh_command(self) -> list[str]:
        command = ["ssh", "-p", str(self.request.remote_port), "-o", "BatchMode=yes"]
        if self.request.remote_identity_file:
            command.extend(["-i", self.request.remote_identity_file])
        if self.request.remote_insecure_no_host_key_check:
            command.extend(
                [
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    "UserKnownHostsFile=/dev/null",
                ]
            )
        return command

    def _parse_payload(
        self,
        tool_name: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_ms: int,
    ) -> dict[str, Any]:
        if not stdout.strip():
            return {
                "tool_name": tool_name,
                "records": [],
                "errors": [stderr.strip() or f"Remote command exited with code {exit_code}."],
                "remote_mode": "sift_ssh",
                "duration_ms": duration_ms,
            }
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return {
                "tool_name": tool_name,
                "records": [],
                "errors": [
                    "Remote command did not return JSON.",
                    stderr.strip() or stdout.strip(),
                ],
                "remote_mode": "sift_ssh",
                "duration_ms": duration_ms,
            }
        payload.setdefault("tool_name", tool_name)
        payload.setdefault("records", [])
        payload.setdefault("errors", [])
        payload["remote_mode"] = "sift_ssh"
        payload["duration_ms"] = duration_ms
        if exit_code != 0 and not payload["errors"]:
            payload["errors"] = [stderr.strip() or f"Remote command exited with code {exit_code}."]
        return payload
