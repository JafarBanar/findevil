#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile


SUPPORTED_TOOLS = {
    "amcache_summary",
    "browser_history",
    "timeline_mft",
    "prefetch_summary",
    "registry_autoruns",
    "scheduled_tasks",
    "user_logons",
    "yara_scan",
}
SUSPICIOUS_SUFFIXES = (".ps1", ".js", ".hta", ".vbs", ".zip")
SUSPICIOUS_MARKERS = ("appdata", "downloads", "temp", "programdata")
SUSPICIOUS_NAME_MARKERS = ("payload", "update", "invoice", "autorun", "theme", "runme", "dropper")
SUSPICIOUS_URL_MARKERS = ("invoice", "update", "login", "verify", "cdn-", ".zip", ".js", ".hta", ".ps1", "payload", "c2")
MAX_SCAN_BYTES = 2 * 1024 * 1024


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


def detect_filesystem_offset(image_path: Path) -> str | None:
    completed = run_command(["mmls", str(image_path)])
    if completed.returncode != 0:
        return None
    candidates: list[tuple[int, int, int, str]] = []
    for line in completed.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5 or not parts[0].endswith(":"):
            continue
        if re.fullmatch(r"\d+", parts[1]):
            start = parts[1]
            length_text = parts[3] if len(parts) >= 4 and re.fullmatch(r"\d+", parts[3]) else "0"
            description = " ".join(parts[4:])
        elif len(parts) >= 6 and re.fullmatch(r"\d+", parts[2]):
            start = parts[2]
            length_text = parts[4] if re.fullmatch(r"\d+", parts[4]) else "0"
            description = " ".join(parts[5:])
        else:
            continue
        lowered = description.lower()
        if "unallocated" in lowered or "metadata" in lowered:
            continue
        if "ntfs" in lowered or "basic data" in lowered or "windows" in lowered:
            score = 0
            if "windows" in lowered:
                score += 4
            if "basic data" in lowered:
                score += 2
            if "ntfs" in lowered:
                score += 1
            try:
                length = int(length_text)
                start_sector = int(start)
            except ValueError:
                continue
            candidates.append((score, length, start_sector, start))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return candidates[-1][3]
    return None


def enumerate_fls(image_path: Path) -> tuple[list[dict[str, str | None]], str]:
    offset = detect_filesystem_offset(image_path)
    command = ["fls", "-r", "-p"]
    source_mode = "image_fls"
    if offset:
        command.extend(["-o", offset])
        source_mode = "image_fls_offset"
    command.append(str(image_path))
    completed = run_command(command)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "fls failed")
    entries: list[dict[str, str | None]] = []
    for line in completed.stdout.splitlines():
        entry = parse_fls_line(line.strip())
        if entry is not None:
            entry["offset"] = offset
            entries.append(entry)
    return entries, source_mode


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


def timeline_from_entries(disk_path: Path, entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    """Extract timeline from entries, preferring real analyzemft output when available."""
    records: list[dict[str, Any]] = []
    
    # First, try to find and analyze MFT files using real analyzemft command
    for entry in entries:
        path_text = entry_path(entry)
        lowered = path_text.lower()
        if "$mft" in lowered or path_text.endswith("$MFT"):
            with tempfile.TemporaryDirectory() as temp_dir:
                mft_path = Path(temp_dir) / "$MFT"
                local_path = entry.get("local_path")
                if local_path and Path(local_path).exists():
                    mft_path = Path(local_path)
                else:
                    mft_path.write_bytes(read_entry_bytes(disk_path, entry))
                real_records = timeline_from_analyzemft(mft_path)
                if real_records:
                    records.extend(real_records)
                    return records  # Return real analyzemft results if available
    
    # Fallback: extract suspicious file timeline from entries
    for entry in entries:
        path_text = entry_path(entry)
        if not is_suspicious_path(path_text):
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
    command = ["icat"]
    offset = entry.get("offset")
    if offset:
        command.extend(["-o", offset])
    command.extend([str(disk_path), address])
    completed = run_command_bytes(command)
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(stderr or f"icat failed for {entry_path(entry)}")
    return completed.stdout


def copy_entry_to_temp(disk_path: Path, entry: dict[str, str | None], temp_root: Path, suffix: str = "") -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(entry_path(entry)).name or "artifact")
    if suffix and not safe_name.lower().endswith(suffix.lower()):
        safe_name = f"{safe_name}{suffix}"
    target = temp_root / safe_name
    target.write_bytes(read_entry_bytes(disk_path, entry))
    return target


def is_suspicious_path(path_text: str | None) -> bool:
    if not path_text:
        return False
    lowered = path_text.lower()
    if any(marker in lowered for marker in SUSPICIOUS_MARKERS):
        return True
    if lowered.endswith(SUSPICIOUS_SUFFIXES):
        return True
    if lowered.endswith(".exe") and any(marker in lowered for marker in SUSPICIOUS_NAME_MARKERS):
        return True
    return False


def is_suspicious_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return any(marker in lowered for marker in SUSPICIOUS_URL_MARKERS)


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


def table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {str(row[0]).lower() for row in rows}


def parse_chromium_history(history_db: Path, source_path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    connection = sqlite3.connect(f"file:{history_db}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        tables = table_names(connection)
        if "urls" not in tables:
            return records
        for row in connection.execute(
            "SELECT url, title, visit_count, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 500"
        ):
            url = str(row["url"] or "")
            if not is_suspicious_url(url):
                continue
            records.append(
                {
                    "browser": "Chromium",
                    "url": url,
                    "title": row["title"],
                    "visit_count": row["visit_count"],
                    "last_visit_time": row["last_visit_time"],
                    "source_path": to_windowsish(source_path),
                    "kind": "browser_activity",
                    "confidence": 0.78,
                }
            )
        if "downloads" in tables:
            for row in connection.execute("SELECT target_path, tab_url, start_time FROM downloads LIMIT 500"):
                target_path = str(row["target_path"] or "")
                tab_url = str(row["tab_url"] or "")
                if not is_suspicious_path(target_path) and not is_suspicious_url(tab_url):
                    continue
                records.append(
                    {
                        "browser": "Chromium",
                        "url": tab_url,
                        "downloaded_path": target_path,
                        "timestamp": row["start_time"],
                        "source_path": to_windowsish(source_path),
                        "kind": "browser_activity",
                        "confidence": 0.82,
                    }
                )
    except sqlite3.DatabaseError:
        return records
    finally:
        connection.close()
    return records


def parse_firefox_history(history_db: Path, source_path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    connection = sqlite3.connect(f"file:{history_db}?mode=ro", uri=True)
    try:
        connection.row_factory = sqlite3.Row
        tables = table_names(connection)
        if "moz_places" not in tables:
            return records
        for row in connection.execute(
            "SELECT url, title, visit_count, last_visit_date FROM moz_places ORDER BY last_visit_date DESC LIMIT 500"
        ):
            url = str(row["url"] or "")
            if not is_suspicious_url(url):
                continue
            records.append(
                {
                    "browser": "Firefox",
                    "url": url,
                    "title": row["title"],
                    "visit_count": row["visit_count"],
                    "last_visit_time": row["last_visit_date"],
                    "source_path": to_windowsish(source_path),
                    "kind": "browser_activity",
                    "confidence": 0.78,
                }
            )
    except sqlite3.DatabaseError:
        return records
    finally:
        connection.close()
    return records


def browser_history_from_entries(disk_path: Path, entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for entry in entries:
            path_text = entry_path(entry)
            lowered = path_text.lower()
            is_chromium = lowered.endswith("/history") and (
                "chrome/user data" in lowered or "edge/user data" in lowered or "chromium/user data" in lowered
            )
            is_firefox = lowered.endswith("/places.sqlite")
            if not is_chromium and not is_firefox:
                continue
            temp_db = copy_entry_to_temp(disk_path, entry, temp_root, ".sqlite")
            if is_chromium:
                records.extend(parse_chromium_history(temp_db, path_text))
            else:
                records.extend(parse_firefox_history(temp_db, path_text))
    return records[:300]


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


def parse_registry_export(text: str, source_path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";") or line.startswith("Windows Registry Editor"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_key = line.strip("[]")
            continue
        if not current_key or "\\currentversion\\run" not in current_key.lower():
            continue
        match = re.match(r'^"([^"]+)"=(?:"(.*)"|hex:.*)$', line)
        if not match:
            continue
        entry, value = match.groups()
        records.append(
            {
                "entry": entry,
                "value": value.replace("\\\\", "\\") if value else "",
                "reg_path": current_key,
                "source_hive": source_path,
                "plugin": "reg_export",
                "kind": "persistence",
                "confidence": 0.72,
            }
        )
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
    for entry in entries:
        path_text = entry_path(entry)
        lowered = path_text.lower()
        if not (lowered.endswith(".reg") or "autorun" in lowered):
            continue
        try:
            text = read_entry_bytes(disk_path, entry).decode("utf-16", errors="ignore")
            if "\\currentversion\\run" not in text.lower():
                text = read_entry_bytes(disk_path, entry).decode("utf-8", errors="ignore")
        except Exception:
            continue
        records.extend(parse_registry_export(text, path_text))
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


def parse_amcache_output(text: str, source_hive: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {"source_hive": source_hive}

    def flush() -> None:
        nonlocal current
        path = str(current.get("path", ""))
        program_name = str(current.get("program_name", ""))
        if path or program_name:
            blob = f"{path} {program_name}".lower()
            if any(marker in blob for marker in ("powershell", ".ps1", "appdata", "temp", "downloads")):
                current.setdefault("kind", "program_execution")
                current.setdefault("confidence", 0.76)
                records.append(current)
        current = {"source_hive": source_hive}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue
        pair_match = re.match(
            r"^(File(?:\s+Name)?|Name|Program(?:\s+Name)?|Path|File(?:\s+)?Path|SHA1|SHA-1|Last(?:\s+)?Modified|LastWrite)\s*:\s*(.*)$",
            line,
            re.IGNORECASE,
        )
        if not pair_match:
            continue
        key, value = pair_match.groups()
        normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        if normalized in {"file", "file_name", "name", "program", "program_name"} and "program_name" not in current:
            current["program_name"] = value
        elif normalized in {"path", "file_path", "filepath"}:
            current["path"] = value
        elif normalized in {"sha1", "sha_1"}:
            current["sha1"] = value
        elif normalized.startswith("last"):
            current["last_modified"] = value
    flush()
    return records


def amcache_from_entries(disk_path: Path, entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for entry in entries:
            path_text = entry_path(entry)
            lowered = path_text.lower()
            if lowered.endswith("windows/appcompat/programs/amcache.hve"):
                temp_hive = copy_entry_to_temp(disk_path, entry, temp_root, ".hve")
                completed = run_regripper(temp_hive, "amcache")
                if completed.returncode != 0:
                    continue
                records.extend(parse_amcache_output(completed.stdout, path_text))
            elif "amcache" in lowered and lowered.endswith((".txt", ".log", ".csv")):
                try:
                    text = read_entry_bytes(disk_path, entry).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                records.extend(parse_amcache_output(text, path_text))
    return records[:300]


def _event_data(root: ET.Element) -> dict[str, str]:
    data: dict[str, str] = {}
    for element in root.iter():
        if strip_namespace(element.tag) != "Data":
            continue
        name = element.attrib.get("Name")
        if name and element.text:
            data[name] = element.text.strip()
    return data


def parse_security_events_xml(text: str, source_path: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for event_text in re.findall(r"<Event\b.*?</Event>", text, flags=re.DOTALL):
        try:
            root = ET.fromstring(event_text)
        except ET.ParseError:
            continue
        event_id = _first_text(root, "EventID")
        if event_id not in {"4624", "4625"}:
            continue
        data = _event_data(root)
        user = data.get("TargetUserName") or data.get("SubjectUserName") or "unknown"
        if user.endswith("$"):
            continue
        records.append(
            {
                "event_id": event_id,
                "user": user,
                "logon_type": data.get("LogonType"),
                "source_ip": data.get("IpAddress"),
                "source_path": to_windowsish(source_path),
                "kind": "logon",
                "confidence": 0.72 if event_id == "4624" else 0.62,
            }
        )
    return records[:300]


def user_logons_from_entries(disk_path: Path, entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    evtx_dump = shutil.which("evtx_dump.py")
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        for entry in entries:
            path_text = entry_path(entry)
            lowered = path_text.lower()
            if lowered.endswith(("security.xml", "security.evtx.xml")):
                try:
                    text = read_entry_bytes(disk_path, entry).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                records.extend(parse_security_events_xml(text, path_text))
                continue
            if not evtx_dump or not lowered.endswith("windows/system32/winevt/logs/security.evtx"):
                continue
            temp_evtx = copy_entry_to_temp(disk_path, entry, temp_root, ".evtx")
            completed = run_command([evtx_dump, str(temp_evtx)])
            if completed.returncode != 0:
                continue
            records.extend(parse_security_events_xml(completed.stdout, path_text))
    return records[:300]


def yara_scan_from_entries(disk_path: Path, entries: list[dict[str, str | None]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    candidates = [entry for entry in entries if is_suspicious_path(entry_path(entry))][:300]
    for entry in candidates:
        path_text = entry_path(entry)
        try:
            content = read_entry_bytes(disk_path, entry)
        except Exception:
            continue
        if len(content) > MAX_SCAN_BYTES:
            continue
        lowered = content.lower()
        if b"powershell" not in lowered and b"http://" not in lowered and b"https://" not in lowered and b"set-executionpolicy" not in lowered:
            continue
        records.append(
            {
                "rule": "Inline_Suspicious_Windows_Artifact",
                "file_path": to_windowsish(path_text),
                "tags": ["powershell", "downloader"],
                "kind": "detection",
                "confidence": 0.74,
            }
        )
    return records[:300]


def collect_entries(disk_path: Path) -> tuple[list[dict[str, str | None]], str]:
    if disk_path.is_dir():
        return enumerate_directory(disk_path), "mounted_directory"
    return enumerate_fls(disk_path)


def self_test_payload() -> dict[str, Any]:
    return {
        "tool_name": "self_test",
        "supported_tools": sorted(SUPPORTED_TOOLS),
        "available_commands": {
            "find": shutil.which("find"),
            "mmls": shutil.which("mmls"),
            "fls": shutil.which("fls"),
            "icat": shutil.which("icat"),
            "analyzemft": shutil.which("analyzemft"),
            "evtx_dump.py": shutil.which("evtx_dump.py"),
            "rip.pl": shutil.which("rip.pl"),
            "yara": shutil.which("yara"),
        },
        "python_modules": {
            "sqlite3": True,
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
            payload["records"] = timeline_from_entries(disk_path, entries)
        elif args.tool == "prefetch_summary":
            payload["records"] = prefetch_from_entries(entries)
        elif args.tool == "browser_history":
            payload["records"] = browser_history_from_entries(disk_path, entries)
        elif args.tool == "amcache_summary":
            payload["records"] = amcache_from_entries(disk_path, entries)
        elif args.tool == "scheduled_tasks":
            payload["records"] = scheduled_tasks_from_entries(disk_path, entries)
        elif args.tool == "registry_autoruns":
            payload["records"] = registry_autoruns_from_entries(disk_path, entries)
        elif args.tool == "user_logons":
            payload["records"] = user_logons_from_entries(disk_path, entries)
        else:
            payload["records"] = yara_scan_from_entries(disk_path, entries)
    except Exception as exc:
        payload["errors"] = [str(exc)]

    sys.stdout.write(json.dumps(payload))
    return 0 if not payload["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
