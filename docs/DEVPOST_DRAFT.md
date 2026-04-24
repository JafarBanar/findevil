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
- The included fixture case is useful for repeatable development but is not a real disk image, so the final no-Windows path generates a raw NTFS image on SIFT from controlled artifacts.

## What We Learned

- Auditability matters as much as model reasoning in autonomous IR.
- A bounded loop with explicit verification catches unsupported claims better than a single-pass report.
- A typed MCP/SIFT bridge gives stronger safety than prompt-only restrictions.
- Failure handling is a feature: a useful DFIR agent should say what it could not prove.

## What's Next

- Expand collector coverage, then improve the public NIST CFReDS Windows validation result
- Add more Windows artifact parsers behind the same typed tool boundary
- Package the SIFT image-builder workflow into one command
- Improve report visualizations for judges and analysts

## Competition Strategy: No-Windows Image Demo

Because no Windows host is available, the demo uses a generated raw NTFS image with known artifacts:

1. **Create controlled Windows-like attack artifacts:**
   - Browser history: visiting suspicious URLs
   - PowerShell script execution: stored in suspicious location
   - Scheduled task: persistence mechanism
   - Registry autoruns: additional persistence
   - Prefetch, Amcache, Security logon, and downloaded file markers

2. **Build a raw NTFS image on SIFT:**
   - `scripts/create_ntfs_image_from_artifact_tree.sh`
   - 128 MB raw NTFS image at `cases/realistic-windows-image/disk.img`
   - Enumerated by SIFT `fls` and parsed through the same image-backed bridge path

3. **Run CaseTrace analysis:**
   - Use remote SIFT backend with real forensic tools
   - SIFT enumerates a real NTFS filesystem image
   - Real scheduled task and Prefetch footprint extraction
   - Browser history, Amcache, Security.evtx logons, and YARA-style scanning collected through the remote bridge

4. **Validate accuracy:**
   - Every planted artifact category found in the controlled case
   - Zero false positives (controlled environment)
   - Demonstrates self-correction with real data
   - Reproducible: judges can verify every step

**Why This Wins:**
- ✓ Real image-backed analysis (not fixture JSON)
- ✓ Real tool execution (not simulated)
- ✓ Provable accuracy (we control all artifacts)
- ✓ Reproducible (no external dependencies)
- ✓ Demonstrates expertise (shows forensic knowledge)
- ✓ Fast demo (no multi-GB downloads)

See [docs/CREATE_DEMO_CASE.md](./CREATE_DEMO_CASE.md) for step-by-step guide.

## Demo Results

**Current fixture-based demo** (`runs/demo-real-case-run` with fixture backend):
- 4 findings from synthetic test data across 2 iterations
- All 10 forensic tools contributed evidence
- Self-correction blocked 1 unsupported claim
- Demonstrates orchestration and verification working correctly

**Main no-Windows image demo** (`runs/realistic-windows-image` with `sift-ssh` backend):
- 128 MB raw NTFS image created without Windows from the controlled artifact tree
- 10/10 typed tools completed successfully through the remote SIFT bridge
- 8/8 planted artifact categories produced evidence
- 4 findings retained: script execution, web delivery, persistence, and detection hit
- 1 unsupported credential-theft claim blocked by verification
- Scope note: image-backed and reproducible, but not a native Windows OS install

**Controlled artifact-tree smoke demo** (`runs/realistic-windows-case-script` with `sift-ssh` backend):
- 10/10 typed tools completed successfully through the remote SIFT bridge
- 8/8 planted artifact categories produced evidence
- 4 findings retained: script execution, web delivery, persistence, and detection hit
- 1 unsupported credential-theft claim blocked by verification
- Scope note: this is a reproducible Windows-like artifact tree, not a full forensic disk image
