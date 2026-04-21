from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from .schemas import ExecutionEvent
from .utils import ensure_parent, now_utc_iso, to_jsonable


class RunArtifactStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.raw_dir = self.root / "raw"
        self._counters: dict[str, int] = {}

    def prepare(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, relative_path: str) -> Path:
        return self.root / relative_path

    def write_json(self, relative_path: str, payload: Any) -> str:
        path = self.path_for(relative_path)
        ensure_parent(path)
        path.write_text(
            json.dumps(to_jsonable(payload), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return str(path)

    def write_text(self, relative_path: str, text: str) -> str:
        path = self.path_for(relative_path)
        ensure_parent(path)
        path.write_text(text, encoding="utf-8")
        return str(path)

    def append_jsonl(self, relative_path: str, payload: Any) -> str:
        path = self.path_for(relative_path)
        ensure_parent(path)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(to_jsonable(payload), sort_keys=True))
            handle.write("\n")
        return str(path)

    def append_event(self, event: ExecutionEvent) -> None:
        self.append_jsonl("events.jsonl", event)

    def append_tool_call(self, payload: Any) -> None:
        self.append_jsonl("tool_calls.jsonl", payload)

    def write_raw_json(self, tool_name: str, payload: Any) -> str:
        counter = self._counters.get(tool_name, 0) + 1
        self._counters[tool_name] = counter
        stamp = now_utc_iso().replace(":", "-")
        relative_path = f"raw/{tool_name}/{counter:02d}-{stamp}.json"
        return self.write_json(relative_path, payload)
