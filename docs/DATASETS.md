# Dataset Documentation

This file tracks every dataset used to evaluate CaseTrace. Keep hashes, source links, expected artifacts, and run folders here so judges can reproduce the results.

## Included Fixture Case

- Name: `windows_persistence_case`
- Path: `sample_cases/windows_persistence_case`
- Purpose: deterministic development fixture for orchestration, verification, evidence linking, and self-correction behavior.
- Disk path: `sample_cases/windows_persistence_case/image.E01`
- Important note: this is not a real forensic disk image. It is a tiny fixture marker used with JSON artifact exports.
- Expected behavior:
  - Finds suspicious PowerShell execution evidence from Amcache fixture data.
  - Finds web delivery evidence from browser history fixture data.
  - Finds scheduled task persistence from fixture data.
  - Blocks a speculative credential-theft finding because no credential-access evidence exists.
- Recommended command:

```bash
python3 -m findevil analyze \
  --case sample_cases/windows_persistence_case \
  --disk sample_cases/windows_persistence_case/image.E01 \
  --profile windows \
  --max-iterations 3 \
  --output runs/windows-persistence-case
```

## Local UTM Bridge Smoke Test

- Name: `local_utm_bridge_sample`
- Path: `runs/local-utm-bridge`
- Purpose: proves CaseTrace can call the SIFT VM bridge over SSH and degrade cleanly when a non-real image cannot be parsed by filesystem tools.
- Remote host: `127.0.0.1`
- Remote port: `2222`
- Remote workdir: `/home/sift/findevil`
- Expected behavior:
  - Bridge self-test succeeds.
  - Fixture-backed tools still produce structured evidence.
  - Real SIFT-backed filesystem tools may return `Cannot determine file system type` against the fixture image.
  - The run completes without crashing and logs tool failures in `events.jsonl`, `tool_calls.jsonl`, and `report.md`.

## Final Demo Case

- Name: `TBD`
- Source: `TBD`
- Download URL: `TBD`
- License/permission: `TBD`
- Local path: `TBD`
- Disk image path: `TBD`
- Memory image path: `optional/TBD`
- SHA256: `TBD`
- Size: `TBD`
- Known ground truth: `TBD`
- Expected artifacts:
  - `TBD`
- CaseTrace run folder:
  - `TBD`
- Notes:
  - Choose one Windows case with clear execution and persistence artifacts.
  - Prefer a dataset with public write-ups or ground truth so the accuracy report can be honest and judge-friendly.
