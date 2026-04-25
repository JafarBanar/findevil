from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any
import json
import sys

from .case_data import CaseDataset
from .schemas import AnalysisState, CaseRequest
from .store import RunArtifactStore
from .tools import ToolContext, ToolRegistry
from .utils import now_utc_iso, to_jsonable


class CaseTraceMCPServer:
    def __init__(self, request: CaseRequest, registry: ToolRegistry | None = None) -> None:
        self.request = request
        self.registry = registry or ToolRegistry()
        self.store = RunArtifactStore(request.output_path)
        self.store.prepare()
        self.dataset = CaseDataset(request)
        self.state = AnalysisState(case_id=self.dataset.resolved_case_id())
        self.call_count = 0

    def handle_request(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params", {})

        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-03-26",
                    "serverInfo": {"name": "casetrace-mcp", "version": "0.1.0"},
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }
        if method == "tools/list":
            tools = [
                {
                    "name": spec.name,
                    "description": spec.description,
                    "inputSchema": spec.input_schema,
                }
                for spec in self.registry.specs()
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            if tool_name not in self.registry.names():
                return self._error(request_id, -32602, f"Unknown tool '{tool_name}'.")

            self.call_count += 1
            execution = self.registry.execute(
                tool_name,
                ToolContext(
                    request=self.request,
                    dataset=self.dataset,
                    store=self.store,
                    state=self.state,
                    iteration=self.call_count,
                ),
                arguments,
            )
            self.state.tool_results[tool_name] = execution.result
            for item in execution.evidence:
                self.state.evidence[item.id] = item
            self.store.append_tool_call(
                {
                    "timestamp": now_utc_iso(),
                    "iteration": self.call_count,
                    "tool_name": tool_name,
                    "inputs": execution.result.inputs,
                    "success": execution.result.success,
                    "errors": execution.result.errors,
                    "evidence_ids": execution.result.evidence_ids,
                    "token_usage": execution.result.token_usage,
                }
            )
            structured = {
                "tool_name": tool_name,
                "result": to_jsonable(execution.result),
                "evidence": to_jsonable(execution.evidence),
            }
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(structured, indent=2)}],
                    "structuredContent": structured,
                    "isError": bool(execution.result.errors),
                },
            }
        return self._error(request_id, -32601, f"Method '{method}' not found.")

    def serve_stdio(self) -> None:
        while True:
            message = self._read_message()
            if message is None:
                break
            response = self.handle_request(message)
            if response is not None:
                self._write_message(response)

    def _read_message(self) -> dict[str, Any] | None:
        headers: dict[str, str] = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            if line in {b"\r\n", b"\n"}:
                break
            decoded = line.decode("utf-8").strip()
            if ":" in decoded:
                key, value = decoded.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        content_length = int(headers.get("content-length", "0"))
        if content_length <= 0:
            return None
        payload = sys.stdin.buffer.read(content_length)
        return json.loads(payload.decode("utf-8"))

    def _write_message(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8"))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }
