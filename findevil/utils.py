from __future__ import annotations

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

