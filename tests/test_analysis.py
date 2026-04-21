from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import importlib.util
import json
import subprocess
import unittest
from unittest.mock import patch

from findevil import remote as remote_module
from findevil.evaluation import evaluate_request
from findevil.mcp_server import CaseTraceMCPServer
from findevil.orchestrator import AnalysisOrchestrator
from findevil.remote import RemoteSIFTRunner
from findevil.schemas import CaseRequest


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
        self.assertEqual(command[:4], ["ssh", "-p", "22", "sift@dfir.example"])
        self.assertIn("/home/sift/findevil/scripts/sift_tool_bridge.py", command)
        self.assertIn("/cases/case1/image.E01", command)

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

    def test_bridge_parser_extracts_registry_autorun_records(self) -> None:
        sample = """
Software\\Microsoft\\Windows\\CurrentVersion\\Run
Launch String : ThemeUpdater
Value : powershell.exe -ExecutionPolicy Bypass -File C:\\Users\\Analyst\\AppData\\Roaming\\update.ps1
"""
        records = BRIDGE_MODULE.parse_regripper_output(sample, "NTUSER.DAT", "run")
        self.assertEqual(records[0]["entry"], "ThemeUpdater")
        self.assertIn("powershell.exe", records[0]["value"])

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
