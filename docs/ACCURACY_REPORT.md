# Accuracy Report

This report is a living assessment of CaseTrace accuracy. The final Devpost submission should update this with the real demo case results.

## Current Evaluation Summary

| Run | Dataset | Backend | Result |
| --- | --- | --- | --- |
| `runs/windows-persistence-case` | fixture case | fixture | Completed; evidence-linked findings generated. |
| `runs/windows-persistence-eval` | fixture case | fixture | Completed; iteration comparison available in `evaluation.json`. |
| `runs/local-utm-bridge` | fixture case | local UTM SIFT bridge | Completed; remote bridge worked, real filesystem tools degraded cleanly because the fixture image is not a real disk image. |
| `runs/demo-real-case-run` | fixture case | remote SIFT VM (127.0.0.1:2222) SSH backend | Completed; 4 findings generated across 2 iterations; all 10 tools contributed evidence; self-correction blocked 1 unsupported credential-theft claim. |

## Confirmed Strengths

- Findings cite `evidence_ids` instead of standing alone as free text.
- Tool execution is recorded in `tool_calls.jsonl`.
- Reasoning and phase transitions are recorded in `events.jsonl`.
- Unsupported credential-theft speculation is blocked when no supporting evidence exists.
- Tool failures are represented as verification issues instead of crashing the run.
- The SSH SIFT backend does not expose arbitrary shell execution to the agent.
- Remote SIFT backend (SSH over 127.0.0.1:2222) executes successfully and returns structured JSON.
- Real SIFT tools (analyzemft, regripper.pl) are callable from the remote bridge without errors.
- Tool coverage across 2 iterations spans 10 different forensic tools.

## Known False Positives

- None confirmed yet on a real forensic dataset.
- Fixture findings are intentionally synthetic and should not be treated as real-world accuracy claims.

## Known Misses

- Not yet measured on a real Windows case.
- Real SIFT-backed filesystem tools need a real disk image before depth can be evaluated.

## Blocked Hallucinations

Current fixture behavior blocks this unsupported finding:

- Claim: credential theft likely followed the suspicious browser session.
- Decision: blocked as unsupported.
- Reason: no credential-access artifacts were present in the collected evidence.
- Status: Verified in `runs/demo-real-case-run` (2 iterations, 1 unsupported claim blocked)

## Evidence Integrity

- CaseTrace does not expose a generic shell tool to the agent.
- The local fixture backend only reads fixture files.
- The SSH SIFT backend calls a fixed bridge script with typed tool names.
- Raw outputs and parsed records are copied into the run folder.
- The UTM/SIFT setup is intended for development and demonstration, not courtroom-grade forensic acquisition.

## Current Limitations

- The included `image.E01` is a development fixture marker, not a full disk image.
- Final IR accuracy cannot be claimed until CaseTrace is run against a real Windows disk image with known ground truth.
- Some SIFT tools may be unavailable until the full SIFT installation completes.
- The local Apple Silicon UTM path uses x86_64 emulation and is slower than a native x86 SIFT host.

## Final Report TODO

- [x] Add dataset source and backend (remote SIFT VM via SSH).
- [x] List confirmed findings (4 total: 2 high severity confirmed, 2 high severity inference).
- [ ] List false positives (none observed in fixture; real case evaluation pending).
- [ ] List missed artifacts (fixture includes all expected artifacts; real case evaluation pending).
- [x] Include iteration 1 vs final unsupported-claim counts (iteration 1: 2 issues, iteration 2: 1 issue with 1 blocked).
- [x] Include tool failures and whether fallback behavior worked (0 failures; all 10 tools successful).
- [ ] Include a short evidence-safety test result (in progress).
