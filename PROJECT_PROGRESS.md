# CaseTrace Project Progress

Last updated: 2026-04-21

Use this file as the project control board. Change `[ ]` to `[x]` when a task is finished.

## Current Status

- [x] Project direction chosen: read-only self-correcting Windows DFIR agent for SIFT.
- [x] Primary architecture chosen: typed tool backend plus bounded orchestration loop.
- [x] Local sample CaseTrace run works against the fixture case.
- [x] UTM path debugged enough for a local x86_64 Ubuntu VM to boot on this Mac.
- [x] Extra/stale UTM profiles removed; keep only `SIFT Ubuntu 22.04 x86_64`.
- [ ] Full SIFT install confirmed complete inside the VM.
- [ ] Protocol SIFT install confirmed complete inside the VM.
- [ ] Real Windows case data selected and documented.
- [ ] End-to-end real case run completed with evidence-linked findings.
- [ ] Demo, README, accuracy report, architecture diagram, and Devpost write-up completed.
- [x] Public GitHub repository created: https://github.com/JafarBanar/findevil

## Done

- [x] Defined the hackathon submission plan and scoring strategy.
- [x] Scoped v1 to Windows disk triage first.
- [x] Made memory analysis optional instead of blocking the main workflow.
- [x] Implemented core CaseTrace CLI shape:
  `python -m findevil analyze --case ... --disk ... --profile windows --max-iterations 3 --output ...`
- [x] Implemented structured run outputs:
  `report.md`, `findings.json`, `events.jsonl`, `tool_calls.jsonl`, and `run_metadata.json`.
- [x] Implemented evidence-linked findings for the sample case.
- [x] Implemented bounded iteration behavior.
- [x] Implemented unsupported-claim verification behavior in the sample workflow.
- [x] Added test coverage for the local sample workflow.
- [x] Confirmed local tests pass: `python3 -m unittest discover -s tests -v`.
- [x] Created UTM bootstrap scripts for an Ubuntu 22.04 x86_64 guest.
- [x] Added cloud-init assets for the VM.
- [x] Added deterministic SSH setup for the guest user.
- [x] Fixed UTM app reload issue so edited VM config is actually used.
- [x] Switched VM networking to localhost SSH forwarding on `127.0.0.1:2222`.
- [x] Added hardened SIFT guest installer wrapper.
- [x] Added apt safeguards to block accidental Ubuntu `noble` package selection on Jammy.
- [x] Verified the earlier package contamination root cause.
- [x] Initialized local Git repository on `main`.
- [x] Pushed initial project commit to GitHub.

## In Progress

- [ ] Let the full SIFT installer finish in the UTM guest.
- [ ] Verify the SIFT install did not select `noble` packages as installed candidates.
- [ ] Confirm SSH remains stable:
  `ssh -i vm_assets/ssh/sift_vm_ed25519 -p 2222 sift@127.0.0.1`
- [ ] Confirm the guest has enough disk after install:
  `df -h /`
- [ ] Confirm the VM still boots cleanly after shutdown/restart.

## VM And SIFT Tasks

- [ ] Check whether `cast install teamdfir/sift` completed successfully.
- [ ] If the final guard fails only because pinned `noble` entries are visible at priority `-10`, adjust the guard to allow pinned-but-not-selected `noble` entries.
- [ ] Run SIFT tool verification:
  `mmls`, `fls`, `bulk_extractor`, `xmount`, `tcpflow`, `analyzemft`, `evtx_dump.py`.
- [ ] Install Protocol SIFT in the VM:
  `curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash`
- [ ] Verify Protocol SIFT starts or exposes its expected MCP/tooling path.
- [ ] Document the VM setup in one judge-friendly command path.

## CaseTrace Product Tasks

- [x] Add or verify `--remote-port 2222` support for the SSH SIFT backend.
- [ ] Copy or sync the repo into the VM at `/home/sift/findevil`.
- [ ] Run the bridge self-test against the VM.
- [ ] Wire at least two fixture tools to real SIFT commands.
- [ ] Prioritize these first real tools:
  `timeline_mft`, `registry_autoruns`, `scheduled_tasks`, `user_logons`.
- [ ] Save raw command output for every real SIFT-backed tool call.
- [ ] Ensure every real tool returns structured JSON only.
- [ ] Ensure every real tool result includes:
  `tool_name`, `inputs`, `raw_artifact_path`, `evidence_ids`, `errors`, and `confidence`.
- [ ] Make tool failures degrade cleanly instead of crashing the run.
- [ ] Add tests for real-tool failure behavior using mocked SSH/SIFT output.

## Real Case Tasks

- [ ] Choose one Windows disk image case for the main demo.
- [ ] Record dataset source, license/permission, hash, size, and expected artifacts.
- [ ] Put case data under a local path such as `/cases/case1`.
- [ ] Run CaseTrace on the real case.
- [ ] Review `report.md` manually for false positives and unsupported claims.
- [ ] Update verifier rules based on the first real run.
- [ ] Re-run until the final report is evidence-linked and defensible.
- [ ] Preserve the complete run folder for Devpost judging.

## Self-Correction And Evaluation Tasks

- [ ] Create a test case where one expected artifact is missing.
- [ ] Confirm the agent triggers self-correction only for valid reasons.
- [ ] Create an unsupported-claim test case.
- [ ] Confirm unsupported claims are removed or downgraded to `inference`.
- [ ] Create a tool-failure test case.
- [ ] Confirm the agent retries, falls back, or exits gracefully.
- [ ] Compare iteration 1 against final output.
- [ ] Count unsupported claims before and after self-correction.
- [ ] Save this comparison in the accuracy report.

## Submission Documents

- [ ] Finish README quickstart for local runs.
- [ ] Finish SIFT VM setup instructions.
- [ ] Add architecture diagram.
- [ ] Add dataset documentation.
- [ ] Add accuracy report.
- [ ] Add evidence integrity section.
- [ ] Add blocked hallucinations section.
- [ ] Add known limitations section.
- [ ] Add Devpost project story:
  What it does, how it was built, challenges, what was learned, and what is next.
- [ ] Add open-source license confirmation.
- [x] Initialize Git repo if needed.
- [x] Push public GitHub repository.

## Demo Video Checklist

- [ ] Start with the problem: AI attackers move faster than human IR.
- [ ] Show architecture diagram.
- [ ] Show the agent running from terminal.
- [ ] Show at least one typed tool call.
- [ ] Show raw artifact path and evidence ID.
- [ ] Show a self-correction sequence.
- [ ] Show final `report.md`.
- [ ] Show `findings.json` and `tool_calls.jsonl` traceability.
- [ ] Keep video under 5 minutes.

## Winning Focus

- [ ] Do not broaden into many shallow artifact types.
- [ ] Make the Windows disk workflow excellent.
- [ ] Make evidence traceability obvious.
- [ ] Make read-only architectural guardrails obvious.
- [ ] Show at least one blocked hallucination.
- [ ] Show one clean end-to-end real case.
- [ ] Keep judge setup simple and reproducible.
