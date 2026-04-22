# Accuracy Report

This report is a living assessment of CaseTrace accuracy. The final Devpost submission should update this with the real demo case results.

## Current Evaluation Summary

| Run | Dataset | Backend | Result |
| --- | --- | --- | --- |
| `runs/windows-persistence-case` | fixture case | fixture | Completed; evidence-linked findings generated. |
| `runs/windows-persistence-eval` | fixture case | fixture | Completed; iteration comparison available in `evaluation.json`. |
| `runs/local-utm-bridge` | fixture case | remote SIFT VM (sift-ssh) | Completed; remote backend works, fails gracefully on fixture image ("Cannot determine file system type"). |
| `runs/demo-real-case-run` | fixture case | fixture | Completed; 4 findings from fixture data across 2 iterations; **NOT a real case analysis**. |
| `runs/remote-case` | fixture case | remote SIFT VM (sift-ssh) | Completed; remote backend execution confirmed. |
| `runs/realistic-windows-case-script` | controlled artifact tree | remote SIFT VM (sift-ssh) | Completed; 10/10 tools succeeded, 4 findings retained, 1 unsupported claim blocked. |

## Confirmed Strengths

- Findings cite `evidence_ids` instead of standing alone as free text.
- Tool execution is recorded in `tool_calls.jsonl`.
- Reasoning and phase transitions are recorded in `events.jsonl`.
- Unsupported credential-theft speculation is blocked when no supporting evidence exists.
- Tool failures are represented as verification issues instead of crashing the run.
- The SSH SIFT backend does not expose arbitrary shell execution to the agent.
- Remote SIFT backend (SSH over 127.0.0.1:2222) executes successfully and returns structured JSON.
- Real SIFT/forensic parsers are callable from the remote bridge, including analyzemft, Regripper-backed hives, scheduled task XML, browser SQLite history, Security.evtx logons, and YARA-style suspicious file scanning.
- Tool coverage across 2 iterations spans 10 different forensic tools.

## Known False Positives

- None confirmed yet on a real forensic dataset.
- None observed in the controlled artifact-tree smoke run.
- Fixture findings are intentionally synthetic and should not be treated as real-world accuracy claims.

## Known Misses

- Not yet measured on a real Windows case.
- Real SIFT-backed filesystem tools need a real disk image before depth can be evaluated.
- Controlled artifact-tree smoke run detected all 8 expected artifact categories.

## What's Actually Complete vs. What Remains

**COMPLETED:**
- ✓ Infrastructure: bounded orchestrator, verification layer, evidence linking
- ✓ Local fixture backend: 100% working
- ✓ Remote SIFT SSH backend: 100% working (tested in runs/local-utm-bridge, runs/remote-case)
- ✓ Tool bridge deployment: core Windows triage tools wired to real remote collection paths
- ✓ Self-correction behavior: blocks unsupported claims (demonstrated on fixture)
- ✓ Controlled artifact-tree smoke run: 10/10 tools successful, 8/8 expected artifact categories produced evidence

**INCOMPLETE:**
- ✗ Full real Windows disk image analysis: no actual forensic disk image has been analyzed yet
- ✗ Accuracy measurement: claims about true positive rate, false positive rate, and missed artifacts cannot be made without a real case
- ✗ Real-world findings credibility: artifact-tree and fixture findings should not be treated as real incident accuracy

**TO COMPLETE THE SUBMISSION:**
1. Obtain a real Windows forensic disk image (public DFIR dataset, CTF, etc.)
2. Run: `python3 -m findevil analyze --case <name> --disk <image.E01> --profile windows --output runs/real-case-analysis [--tool-backend sift-ssh --remote-host ...]`
3. Review findings against known ground truth
4. Document false positives, misses, and accuracy metrics
5. Update ACCURACY_REPORT.md with real evaluation results

## Blocked Hallucinations

Current fixture behavior blocks this unsupported finding:

- Claim: credential theft likely followed the suspicious browser session.
- Decision: blocked as unsupported.
- Reason: no credential-access artifacts were present in the collected evidence.
- Status: Verified in `runs/demo-real-case-run` (2 iterations, 1 unsupported claim blocked)
- Artifact-tree status: Verified in `runs/realistic-windows-case-script` (2 iterations, 1 unsupported claim blocked, 0 tool failures)

## Evidence Integrity

- CaseTrace does not expose a generic shell tool to the agent.
- The local fixture backend only reads fixture files.
- The SSH SIFT backend calls a fixed bridge script with typed tool names.
- Raw outputs and parsed records are copied into the run folder.
- The UTM/SIFT setup is intended for development and demonstration, not courtroom-grade forensic acquisition.

## Current Limitations

- The included `image.E01` is a development fixture marker, not a full disk image.
- The controlled artifact-tree case is reproducible and useful for demos, but it is not a disk image.
- Final IR accuracy cannot be claimed until CaseTrace is run against a real Windows disk image with known ground truth.
- Some SIFT tools may be unavailable until the full SIFT installation completes.
- The local Apple Silicon UTM path uses x86_64 emulation and is slower than a native x86 SIFT host.

## Final Report TODO

- [x] Add dataset source and backend (remote SIFT VM via SSH).
- [x] List confirmed findings (4 total: 2 high severity confirmed, 2 high severity inference).
- [x] List false positives (none observed in fixture or controlled artifact-tree; real disk evaluation pending).
- [x] List missed artifacts (controlled artifact-tree detected all 8 expected artifact categories; real disk evaluation pending).
- [x] Include iteration 1 vs final unsupported-claim counts (iteration 1: 2 issues, iteration 2: 1 issue with 1 blocked).
- [x] Include tool failures and whether fallback behavior worked (0 failures; all 10 tools successful).
- [x] Include a short evidence-safety test result (remote bridge uses fixed typed tools, raw output paths, and blocked unsupported claims).
