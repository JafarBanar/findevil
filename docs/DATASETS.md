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

- Name: `windows_persistence_case` (Fixture-Enhanced)
- Source: Synthetic SIFT forensic fixture with real tool backend execution
- License/permission: Project-internal testing fixture
- Local path: `sample_cases/windows_persistence_case`
- Disk image path: `sample_cases/windows_persistence_case/image.E01` (marker file)
- SHA256: N/A (fixture)
- Size: 104 bytes (fixture marker)
- Known ground truth: 
  - Suspicious PowerShell script execution (amcache + prefetch)
  - Web delivery of payload (browser history + MFT timeline)
  - Persistence via autorun and scheduled task (registry + scheduled tasks)
  - YARA detection match (Suspicious_PowerShell_Downloader)
  - Self-correction: blocks speculative credential theft claim (no evidence)
- Expected artifacts:
  - `amcache_summary`: ✅ execution evidence
  - `browser_history`: ✅ web delivery evidence
  - `prefetch_summary`: ✅ execution summary
  - `registry_autoruns`: ✅ persistence mechanism
  - `scheduled_tasks`: ✅ task persistence
  - `timeline_mft`: ✅ on-disk artifact timeline
  - `user_logons`: ✅ logon evidence
  - `yara_scan`: ✅ signature match
- CaseTrace run folder: `runs/demo-real-case-run`
- Analysis results:
  - Iterations: 2
  - Findings: 4 (1 high severity confirmed, 1 high severity inference, 1 medium severity confirmed, 1 high severity inference)
  - Tool coverage: 10/10 tools successful
  - Self-correction: 1 blocked unsupported claim (credential theft without evidence)
  - Command:
    ```bash
    python3 -m findevil analyze \
      --case sample_cases/windows_persistence_case \
      --disk sample_cases/windows_persistence_case/image.E01 \
      --profile windows \
      --max-iterations 3 \
      --output runs/demo-real-case-run \
      --remote-host 127.0.0.1 \
      --remote-port 2222 \
      --remote-user sift \
      --remote-identity-file vm_assets/ssh/sift_vm_ed25519
    ```
- Notes:
  - Demo case uses fixture data but executes real SIFT tools via SSH bridge (127.0.0.1:2222).
  - Demonstrates: orchestration, evidence linking, bounded iteration, self-correction, unsupported claim verification.
  - Real Windows cases can be substituted following the same command pattern.
