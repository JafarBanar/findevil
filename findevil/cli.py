from __future__ import annotations

import argparse
import json

from .evaluation import evaluate_request
from .mcp_server import CaseTraceMCPServer
from .orchestrator import AnalysisOrchestrator
from .remote import RemoteSIFTRunner
from .schemas import CaseRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="findevil", description="CaseTrace DFIR agent.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Run the self-correcting analysis loop.")
    _add_shared_case_arguments(analyze_parser)
    analyze_parser.add_argument("--max-iterations", type=int, default=3)
    analyze_parser.add_argument("--model-backend", default="auto")

    evaluate_parser = subparsers.add_parser("evaluate", help="Compare iteration 1 against the bounded self-correcting run.")
    _add_shared_case_arguments(evaluate_parser)
    evaluate_parser.add_argument("--max-iterations", type=int, default=3)
    evaluate_parser.add_argument("--model-backend", default="auto")

    server_parser = subparsers.add_parser("mcp-server", help="Serve typed tools over MCP stdio.")
    _add_shared_case_arguments(server_parser)

    remote_parser = subparsers.add_parser("check-remote", help="Validate SSH access to a remote SIFT bridge.")
    _add_remote_arguments(remote_parser)

    return parser


def _add_shared_case_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--case", required=True, dest="case_path")
    parser.add_argument("--disk", required=True, dest="disk_path")
    parser.add_argument("--output", required=True, dest="output_path")
    parser.add_argument("--profile", default="windows")
    parser.add_argument("--memory", dest="memory_path")
    parser.add_argument("--case-id", dest="case_id")
    _add_remote_arguments(parser)


def _add_remote_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--tool-backend", choices=["fixture", "sift-ssh"], default="fixture")
    parser.add_argument("--remote-host")
    parser.add_argument("--remote-user")
    parser.add_argument("--remote-port", type=int, default=22)
    parser.add_argument("--remote-workdir")
    parser.add_argument("--remote-disk-path")
    parser.add_argument("--remote-identity-file")
    parser.add_argument("--remote-python", default="python3")
    parser.add_argument("--remote-timeout-sec", type=int, default=120)


def _request_from_args(args: argparse.Namespace) -> CaseRequest:
    return CaseRequest(
        case_path=args.case_path,
        disk_path=args.disk_path,
        output_path=args.output_path,
        profile=args.profile,
        case_id=args.case_id,
        memory_path=args.memory_path,
        max_iterations=getattr(args, "max_iterations", 3),
        model_backend=getattr(args, "model_backend", "auto"),
        tool_backend=args.tool_backend,
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        remote_port=args.remote_port,
        remote_workdir=args.remote_workdir,
        remote_disk_path=args.remote_disk_path,
        remote_identity_file=args.remote_identity_file,
        remote_python=args.remote_python,
        remote_timeout_sec=args.remote_timeout_sec,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check-remote":
        request = CaseRequest(
            case_path=".",
            disk_path=".",
            output_path="runs/remote-check",
            tool_backend=args.tool_backend,
            remote_host=args.remote_host,
            remote_user=args.remote_user,
            remote_port=args.remote_port,
            remote_workdir=args.remote_workdir,
            remote_disk_path=args.remote_disk_path,
            remote_identity_file=args.remote_identity_file,
            remote_python=args.remote_python,
            remote_timeout_sec=args.remote_timeout_sec,
        )
        result = RemoteSIFTRunner(request).run_self_test()
        print(
            json.dumps(
                {
                    "success": result.exit_code == 0 and not result.payload.get("errors"),
                    "command": result.command,
                    "payload": result.payload,
                    "stderr": result.stderr,
                },
                indent=2,
            )
        )
        return 0 if result.exit_code == 0 and not result.payload.get("errors") else 1

    request = _request_from_args(args)

    if args.command == "analyze":
        result = AnalysisOrchestrator().run(request)
        print(
            json.dumps(
                {
                    "case_id": result.summary.case_id,
                    "status": result.summary.status,
                    "iterations": result.summary.iterations,
                    "findings": result.summary.findings_count,
                    "issues": result.summary.issues_count,
                    "output": result.summary.output_path,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "evaluate":
        print(json.dumps(evaluate_request(request), indent=2))
        return 0

    if args.command == "mcp-server":
        CaseTraceMCPServer(request).serve_stdio()
        return 0

    parser.error(f"Unknown command {args.command}")
    return 2
