# CaseTrace Project Progress

Last updated: 2026-04-22

Use this file as the project control board. Change `[ ]` to `[x]` when a task is finished.

## Current Status

- [x] Project direction chosen: read-only self-correcting Windows DFIR agent for SIFT.
- [x] Primary architecture chosen: typed tool backend plus bounded orchestration loop.
- [x] Local sample CaseTrace run works against the fixture case.
- [x] UTM path debugged enough for a local x86_64 Ubuntu VM to boot on this Mac.
- [x] Extra/stale UTM profiles removed; keep only `SIFT Ubuntu 22.04 x86_64`.
- [x] Full SIFT install confirmed complete inside the VM.
- [x] Protocol SIFT install confirmed complete inside the VM.
- [x] Tool wiring: core Windows triage tools now remote-backed through the SIFT bridge; findevil repo deployed to VM.
- [x] Remote SIFT backend tested and working (runs/local-utm-bridge/ and runs/remote-case/ both used sift-ssh backend).
- [x] Realistic Windows demo case created with known artifacts as a controlled artifact tree.
- [ ] End-to-end analysis against real forensic image completed.
- [ ] Accuracy report with real-case evaluation completed.
- [x] Public GitHub repository created: https://github.com/JafarBanar/findevil
- [x] Local UTM bridge self-test passed over SSH on `127.0.0.1:2222`.

## Latest Check Notes

- [x] Demo automation scripts exist for Windows artifact creation and image preparation.
- [x] SIFT bridge now handles partitioned images with `mmls` offset detection and extracts `$MFT` before running `analyzemft`.
- [x] Remote SSH failures now return structured JSON instead of Python tracebacks on timeout.
- [x] Local SIFT SSH self-test succeeds on `127.0.0.1:2222` with a longer timeout for x86 emulation startup.
- [x] Updated bridge code synced into `/home/sift/findevil` on the SIFT VM.
- [x] Remote test suite passes inside the SIFT VM: `python3 -m unittest discover -s tests -v`.
- [x] Checked local UTM, Desktop, Downloads, and Documents for a Windows VM/image; none is currently present.
- [x] Controlled artifact-tree run completed through `sift-ssh`: `runs/realistic-windows-case-script`.
- [x] Controlled artifact-tree validation completed: 10/10 tools succeeded, 8/8 artifact categories produced evidence, 1 unsupported claim blocked.
- [ ] Real Windows demo image still needs to be created or converted from the Windows VM.
- [ ] Real-case accuracy can only be claimed after `runs/realistic-windows-case/` exists and has been manually validated against planted artifacts.

## Next Steps To Finish

- [ ] Create or attach a Windows 10/11 VM or real Windows forensic image.
- [ ] Run `scripts/create_windows_artifacts.ps1` inside the Windows VM as Administrator.
- [ ] Shut down the Windows VM cleanly after artifacts are created.
- [ ] Export or convert the Windows disk to raw/E01 format; for UTM qcow2 use `qemu-img convert -O raw`.
- [ ] Place the image at `cases/realistic-windows-case/disk.img` or `cases/realistic-windows-case/disk.E01`.
- [ ] Run `bash scripts/image_and_analyze.sh realistic-windows-case <target-image-path> <source-image-path> 127.0.0.1 2222 sift /home/sift/findevil`.
- [x] Run `bash cases/realistic-windows-case/run_analysis.sh` for the controlled artifact-tree case.
- [x] Validate `runs/realistic-windows-case-script/report.md`, `findings.json`, `events.jsonl`, and `tool_calls.jsonl`.
- [x] Create validation documentation comparing planted artifact-tree artifacts against detected findings.
- [x] Update `docs/ACCURACY_REPORT.md`, `docs/DATASETS.md`, and `docs/DEVPOST_DRAFT.md` with the artifact-tree results.
- [ ] Record the under-5-minute demo video from the real run.

## Earlier Milestones

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
- [x] Synced CaseTrace source into the SIFT VM at `/home/sift/findevil`.
- [x] Ran a remote-backed sample analysis through the UTM VM bridge.
- [x] Added Markdown architecture diagram.
- [x] Added dataset documentation draft.
- [x] Added accuracy report draft.
- [x] Added Devpost project story draft.
- [x] Confirmed MIT license is present.

## In Progress

- [x] Let the full SIFT installer finish in the UTM guest.
- [x] Verify the SIFT install did not select `noble` packages as installed candidates.
- [x] Confirm SSH remains stable:
  `ssh -i vm_assets/ssh/sift_vm_ed25519 -p 2222 sift@127.0.0.1`
- [x] Confirm the guest has enough disk after install:
  `df -h /`
- [x] Confirm the VM still boots cleanly after shutdown/restart.

## VM And SIFT Tasks

- [x] Check whether `cast install teamdfir/sift` completed successfully.
- [x] If the final guard fails only because pinned `noble` entries are visible at priority `-10`, adjust the guard to allow pinned-but-not-selected `noble` entries.
- [x] Run SIFT tool verification:
  `mmls`, `fls`, `bulk_extractor`, `xmount`, `tcpflow`, `analyzemft`, `evtx_dump.py`.
  Present: mmls, fls, imount, analyzemft, xmount, tcpflow, evtx_dump.py. Missing: bulk_extractor.
- [x] Install Protocol SIFT in the VM:
  `curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash`
- [x] Verify Protocol SIFT starts or exposes its expected MCP/tooling path.
  Claude Code v2.1.116 at ~/.local/bin/claude; skills and case templates installed.
- [x] Document the VM setup in one judge-friendly command path.

## CaseTrace Product Tasks

- [x] Add or verify `--remote-port 2222` support for the SSH SIFT backend.
- [x] Copy or sync the repo into the VM at `/home/sift/findevil`.
- [x] Run the bridge self-test against the VM.
- [x] Wire fixture tools to real SIFT/forensic collection paths:
  - timeline_mft: Uses `mmls`/`fls`/`icat` plus `analyzemft` on extracted `$MFT`.
  - registry_autoruns: Uses `regripper` on extracted registry hives.
  - scheduled_tasks: Parses task XML from extracted task files.
  - browser_history: Parses Chromium/Firefox SQLite history databases.
  - amcache_summary: Uses Regripper Amcache parsing where available.
  - user_logons: Parses Security.evtx through `evtx_dump.py` when present.
  - yara_scan: Scans suspicious files through a deterministic detection path.
- [x] Prioritize these first real tools:
  `timeline_mft`, `registry_autoruns`, `scheduled_tasks`, `user_logons`.
- [x] Save raw command output for every real SIFT-backed tool call.
- [x] Ensure every real tool returns structured JSON only.
- [x] Ensure every real tool result includes:
  `tool_name`, `inputs`, `raw_artifact_path`, `evidence_ids`, `errors`, and `confidence`.
- [x] Make tool failures degrade cleanly instead of crashing the run.
- [x] Add tests for real-tool failure behavior using mocked SSH/SIFT output.

## Real Case Tasks

- [ ] Choose one Windows disk image case for the main demo.
- [ ] Record dataset source, license/permission, hash, size, and expected artifacts.
- [x] Put controlled artifact-tree case data under `cases/realistic-windows-case`.
- [ ] Run CaseTrace on the real case.
- [x] Review artifact-tree `report.md` manually for false positives and unsupported claims.
- [ ] Update verifier rules based on the first real run.
- [x] Re-run controlled artifact-tree case until the final report is evidence-linked and defensible.
- [x] Preserve the complete controlled artifact-tree run folder locally for Devpost judging.

## Self-Correction And Evaluation Tasks

- [x] Create a test case where one expected artifact is missing.
- [x] Confirm the agent triggers self-correction only for valid reasons.
- [x] Create an unsupported-claim test case.
- [x] Confirm unsupported claims are removed or downgraded to `inference`.
- [x] Create a tool-failure test case.
- [x] Confirm the agent retries, falls back, or exits gracefully.
- [x] Compare iteration 1 against final output.
- [x] Count unsupported claims before and after self-correction.
- [x] Save this comparison in the accuracy report.

## Submission Documents

- [x] Finish README quickstart for local runs.
- [x] Finish SIFT VM setup instructions.
- [x] Add architecture diagram.
- [x] Add dataset documentation.
- [x] Add accuracy report.
- [x] Add evidence integrity section.
- [x] Add blocked hallucinations section.
- [x] Add known limitations section.
- [x] Add Devpost project story:
  What it does, how it was built, challenges, what was learned, and what is next.
- [x] Add open-source license confirmation.
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

- [x] Do not broaden into many shallow artifact types.
- [ ] Make the Windows disk workflow excellent.
- [x] Make evidence traceability obvious.
- [x] Make read-only architectural guardrails obvious.
- [x] Show at least one blocked hallucination.
- [ ] Show one clean end-to-end real case.
- [x] Keep judge setup simple and reproducible.
