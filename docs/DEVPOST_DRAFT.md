# Devpost Project Story Draft

## What It Does

CaseTrace is a read-only, self-correcting DFIR agent for Windows triage on SIFT. It runs a bounded investigation loop, collects evidence through typed tools, verifies candidate findings, blocks unsupported claims, and writes traceable reports where every finding links back to evidence IDs and raw tool artifacts.

## How It Works

The agent follows explicit phases:

- `intake`
- `plan`
- `collect`
- `synthesize`
- `verify`
- `self_correct`
- `finalize`

Instead of giving the model arbitrary shell access, CaseTrace exposes typed forensic actions such as `timeline_mft`, `prefetch_summary`, `registry_autoruns`, and `scheduled_tasks`. The local development backend uses deterministic fixtures, while the SIFT SSH backend calls a fixed bridge script on a SIFT VM and returns structured JSON.

## How It Was Built

- Python 3 runtime with dataclass schemas for cases, tool results, evidence, findings, verification issues, events, and run summaries.
- Bounded orchestrator with `--max-iterations`.
- Verification layer that blocks unsupported claims and downgrades weakly supported findings.
- JSONL audit logs for execution events and tool calls.
- Markdown and JSON report outputs for human review and machine evaluation.
- UTM bootstrap path for running an x86_64 Ubuntu/SIFT guest on Apple Silicon during development.

## Architectural Guardrails

- The agent has no generic shell tool.
- The remote backend only invokes `scripts/sift_tool_bridge.py` with fixed typed tool names.
- Original evidence paths are treated as read-only inputs.
- Raw outputs are copied into the run folder for auditability.
- The verifier requires final findings to cite evidence IDs.

## Prompt Guardrails

- The reasoning layer is instructed to distinguish confirmed findings, inferences, and items needing review.
- Prompt guardrails are treated as helpful but insufficient.
- Security boundaries are enforced in code through the typed tool surface.

## Challenges

- Running x86_64 SIFT on Apple Silicon is slow.
- The SIFT installer attempted to introduce Ubuntu `noble` package sources into an Ubuntu 22.04 `jammy` guest, so the setup now pins `noble` packages away and patches cached repo states.
- The included fixture case is useful for repeatable development but is not a real disk image, so real SIFT filesystem parsing requires a real Windows case.

## What We Learned

- Auditability matters as much as model reasoning in autonomous IR.
- A bounded loop with explicit verification catches unsupported claims better than a single-pass report.
- A typed MCP/SIFT bridge gives stronger safety than prompt-only restrictions.
- Failure handling is a feature: a useful DFIR agent should say what it could not prove.

## What's Next

- Run the full workflow against a public Windows case with known ground truth.
- Add deeper MFT, registry, and event log parsing.
- Add optional memory cross-checking with Volatility.
- Expand the evaluation harness to score false positives, missed artifacts, and blocked hallucinations.
- Package the SIFT bridge as a cleaner MCP server.
