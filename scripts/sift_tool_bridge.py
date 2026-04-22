#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile


SUPPORTED_TOOLS = {
    "timeline_mft",
    "prefetch_summary",
    "registry_autoruns",
    "scheduled_tasks",
}
SUSPICIOUS_SUFFIXES = (".ps1", ".js", ".hta", ".vbs", ".exe", ".zip")
SUSPICIOUS_MARKERS = ("appdata", "downloads", "temp", "programdata")


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)


def run_command_bytes(command: list[str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, capture_output=True, text=False, check=False)


def timeline_from_analyzemft(mft_path: Path) -> list[dict[str, Any]]:
    """Extract timeline from MFT using real analyzemft command."""
    records: list[dict[str, Any]] = []
    completed = run_command(["analyzemft", "-f", str(mft_path), "-o", "json"])
    if completed.returncode != 0 or not completed.stdout.strip():
        return records
    try:
        data = json.loads(completed.stdout)
        entries = data if isinstance(data, list) else data.get("records", [])
        for entry in entries[:500]:
            records.append(
                {
                    "action": entry.get("action", "unknown"),
                    "path": entry.get("filename", "unknown"),
                    "timestamp": entry.get("modify_time", None),
                    "kind": "timeline_event",
                    "confidence": 0.85,
                }
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return records


def enumerate_directory(root: Path) -> list[dict[str, str | None]]:
    command = ["find", str(root), "-type", "f"]
    completed = run_command(command)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "find failed")
    entries: list[dict[str, str | None]] = []
    for line in completed.stdout.splitlines():
        absolute_path = line.strip()
        if not absolute_path:
            continue
        relative = Path(absolute_path).resolve().relative_to(root.resolve()).as_posix()
        entries.append({"path": relative, "address": None, "local_path": absolute_path})
    return entries


def parse_fls_line(line: str) -> dict[str, str | None] | None:
    if ":" not in line:
        return None
    prefix, path = line.split(":", 1)
    path = path.strip()
    if not path:
        return None
    address = prefix.split()[-1].strip()
    return {"path": path, "address": address, "local_path": None}


def enumerate_fls(image_path: Path) -> list[dict[str, str | None]]:
    command = ["fls", "-r", "-p", str(image_path)]
    completed = run_command(command)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "fls failed")
    entries: list[dict[str, str | None]] = []
    for line in completed.stdout.splitlines():
        entry = parse_fls_line(line.strip())
        if entry is not None:
            entries.append(entry)
    return entries


def to_windowsish(path_text: str) -> str:
    path = path_text.replace("\\", "/").lstrip("./")
    if not path.startswith("/"):
        path = f"/{path}"
    windows_path = path.replace("/", "\\")
    return f"C:{windows_path}"


def entry_path(entry: dict[str, str | None]) -> str:
    return str(entry["path"])


def prefetch_from_entries(entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entry in entries:
        path_text = entry_path(entry)
        lowered = path_text.lower()
        if not lowered.endswith(".pf") or "prefetch" not in lowered:
            continue
        executable = Path(path_text).name.split("-", 1)[0].lower()
        records.append(
            {
                "executable": executable,
                "path": to_windowsish(path_text),
                "run_count": None,
                "kind": "process_execution",
                "confidence": 0.68,
            }
        )
    return records


def timeline_from_entries(entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    """Extract timeline from entries, preferring real analyzemft output when available."""
    records: list[dict[str, Any]] = []
    
    # First, try to find and analyze MFT files using real analyzemft command
    for entry in entries:
        path_text = entry_path(entry)
        lowered = path_text.lower()
        if "$mft" in lowered or path_text.endswith("$MFT"):
            local_path = entry.get("local_path")
            if local_path and Path(local_path).exists():
                real_records = timeline_from_analyzemft(Path(local_path))
                if real_records:
                    records.extend(real_records)
                    return records  # Return real analyzemft results if available
    
    # Fallback: extract suspicious file timeline from entries
    for entry in entries:
        path_text = entry_path(entry)
        lowered = path_text.lower()
        if not lowered.endswith(SUSPICIOUS_SUFFIXES) and not any(marker in lowered for marker in SUSPICIOUS_MARKERS):
            continue
        records.append(
            {
                "action": "observed",
                "path": to_windowsish(path_text),
                "kind": "timeline_event",
                "confidence": 0.62,
            }
        )
    return records[:200]


def read_entry_bytes(disk_path: Path, entry: dict[str, str | None]) -> bytes:
    local_path = entry.get("local_path")
    if local_path:
        return Path(local_path).read_bytes()
    address = entry.get("address")
    if not address:
        raise RuntimeError(f"No address available for image entry {entry_path(entry)}.")
    completed = run_command_bytes(["icat", str(disk_path), address])
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(stderr or f"icat failed for {entry_path(entry)}")
    return completed.stdout


def strip_namespace(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_text(root: ET.Element, name: str) -> str | None:
    for element in root.iter():
        if strip_namespace(element.tag) == name and element.text:
            return element.text.strip()
    return None


def _trigger_names(root: ET.Element) -> list[str]:
    triggers: list[str] = []
    inside_triggers = False
    for element in root.iter():
        local_name = strip_namespace(element.tag)
        if local_name == "Triggers":
            inside_triggers = True
            continue
        if inside_triggers and local_name in {"CalendarTrigger", "LogonTrigger", "BootTrigger", "TimeTrigger"}:
            triggers.append(local_name)
    return triggers


def parse_task_xml(task_bytes: bytes, fallback_path: str) -> dict[str, Any] | None:
    try:
        root = ET.fromstring(task_bytes)
    except ET.ParseError:
        return None
    command = _first_text(root, "Command")
    if not command:
        return None
    task_name = _first_text(root, "URI") or Path(fallback_path).name
    arguments = _first_text(root, "Arguments")
    triggers = _trigger_names(root)
    record = {
        "task_name": task_name.strip("\\"),
        "command": command,
        "trigger": ",".join(triggers) if triggers else None,
        "kind": "persistence",
        "confidence": 0.76,
    }
    if arguments:
        record["arguments"] = arguments
    return record


def scheduled_tasks_from_entries(disk_path: Path, entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for entry in entries:
        path_text = entry_path(entry)
        lowered = path_text.lower()
        if "windows/system32/tasks/" not in lowered:
            continue
        task_bytes = read_entry_bytes(disk_path, entry)
        parsed = parse_task_xml(task_bytes, path_text)
        if parsed is not None:
            records.append(parsed)
    return records


def run_regripper(hive_path: Path, plugin: str) -> subprocess.CompletedProcess[str]:
    return run_command(["rip.pl", "-r", str(hive_path), "-p", plugin])


def parse_regripper_output(text: str, source_hive: str, plugin: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {"source_hive": source_hive, "plugin": plugin}
    current_reg_path: str | None = None

    def flush() -> None:
        nonlocal current
        if current.get("entry") and current.get("value"):
            current.setdefault("kind", "persistence")
            current.setdefault("confidence", 0.79)
            records.append(current)
        current = {"source_hive": source_hive, "plugin": plugin}
        if current_reg_path:
            current["reg_path"] = current_reg_path

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        if "\\currentversion\\run" in line.lower():
            current_reg_path = line
            current["reg_path"] = line
            continue

        pair_match = re.match(r"^(Launch String|Value|Data|Reg Path|Key name|LastWrite Time|LastWrite)\s*:\s*(.*)$", line)
        if pair_match:
            key, value = pair_match.groups()
            if key == "Launch String":
                if current.get("entry") and current.get("value"):
                    flush()
                current["entry"] = value
            elif key in {"Value", "Data"}:
                current["value"] = value
            elif key == "Reg Path":
                current_reg_path = value
                current["reg_path"] = value
            elif key == "Key name" and "entry" not in current:
                current["entry"] = value
            elif key.startswith("LastWrite"):
                current["last_write"] = value
            continue

        arrow_match = re.match(r"^(.+?)\s+->\s+(.+)$", line)
        if arrow_match:
            if current.get("entry") and current.get("value"):
                flush()
            current["entry"] = arrow_match.group(1).strip()
            current["value"] = arrow_match.group(2).strip()
            continue

    flush()
    return records


def collect_registry_hives(disk_path: Path, entries: list[dict[str, str | None]]) -> list[tuple[dict[str, str | None], str]]:
    collected: list[tuple[dict[str, str | None], str]] = []
    for entry in entries:
        path_text = entry_path(entry)
        lowered = path_text.lower()
        if lowered.endswith("windows/system32/config/software"):
            collected.append((entry, "machine"))
        elif lowered.endswith("ntuser.dat"):
            collected.append((entry, "user"))
    return collected


def registry_autoruns_from_entries(disk_path: Path, entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    hive_entries = collect_registry_hives(disk_path, entries)
    if not hive_entries:
        return []
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for index, (entry, _) in enumerate(hive_entries, start=1):
            hive_name = Path(entry_path(entry)).name or f"hive-{index}"
            temp_hive = temp_root / f"{index:02d}-{hive_name}"
            temp_hive.write_bytes(read_entry_bytes(disk_path, entry))
            for plugin in ("run", "runonce"):
                completed = run_regripper(temp_hive, plugin)
                if completed.returncode != 0:
                    continue
                parsed = parse_regripper_output(completed.stdout, entry_path(entry), plugin)
                records.extend(parsed)
    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for record in records:
        key = (
            str(record.get("entry", "")),
            str(record.get("value", "")),
            str(record.get("reg_path", "")),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def collect_entries(disk_path: Path) -> tuple[list[dict[str, str | None]], str]:
    if disk_path.is_dir():
        return enumerate_directory(disk_path), "mounted_directory"
    return enumerate_fls(disk_path), "image_fls"


def self_test_payload() -> dict[str, Any]:
    return {
        "tool_name": "self_test",
        "supported_tools": sorted(SUPPORTED_TOOLS),
        "available_commands": {
            "find": shutil.which("find"),
            "fls": shutil.which("fls"),
            "icat": shutil.which("icat"),
            "rip.pl": shutil.which("rip.pl"),
        },
        "errors": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remote bridge for CaseTrace typed SIFT exports.")
    parser.add_argument("--tool", choices=sorted(SUPPORTED_TOOLS))
    parser.add_argument("--disk")
    parser.add_argument("--profile", default="windows")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        payload = self_test_payload()
        sys.stdout.write(json.dumps(payload))
        return 0

    if not args.tool or not args.disk:
        parser.error("--tool and --disk are required unless --self-test is used.")

    disk_path = Path(args.disk)
    payload: dict[str, Any] = {
        "tool_name": args.tool,
        "records": [],
        "errors": [],
        "profile": args.profile,
    }

    try:
        entries, source_mode = collect_entries(disk_path)
        payload["source_mode"] = source_mode
        if args.tool == "timeline_mft":
            payload["records"] = timeline_from_entries(entries)
        elif args.tool == "prefetch_summary":
            payload["records"] = prefetch_from_entries(entries)
        elif args.tool == "scheduled_tasks":
            payload["records"] = scheduled_tasks_from_entries(disk_path, entries)
        else:
            payload["records"] = registry_autoruns_from_entries(disk_path, entries)
    except Exception as exc:
        payload["errors"] = [str(exc)]

    sys.stdout.write(json.dumps(payload))
    return 0 if not payload["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
