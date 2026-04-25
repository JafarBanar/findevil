from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import re


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_slug(value: str) -> str:
    lowered = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "item"


def stable_id(prefix: str, payload: str) -> str:
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    return f"{safe_slug(prefix)}-{digest}"


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def default_token_usage(
    *,
    source: str = "local_reasoning_backend",
    notes: str = "No external model tokens were consumed; reasoning used the local deterministic backend.",
) -> dict[str, Any]:
    return {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "tracked": True,
        "source": source,
        "notes": notes,
    }


def merge_token_usage(usages: Iterable[dict[str, Any] | None]) -> dict[str, Any]:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    tracked = True
    sources: list[str] = []
    notes: list[str] = []

    for usage in usages:
        if not usage:
            continue
        prompt_tokens += int(usage.get("prompt_tokens", 0))
        completion_tokens += int(usage.get("completion_tokens", 0))
        total_tokens += int(usage.get("total_tokens", 0))
        tracked = tracked and bool(usage.get("tracked", False))
        source = str(usage.get("source", "")).strip()
        if source and source not in sources:
            sources.append(source)
        note = str(usage.get("notes", "")).strip()
        if note and note not in notes:
            notes.append(note)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "tracked": tracked,
        "source": ", ".join(sources) if sources else "unknown",
        "notes": " ".join(notes).strip(),
    }


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [to_jsonable(item) for item in value]
    return value
