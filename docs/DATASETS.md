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

## Controlled Artifact-Tree Demo Case

- Name: `realistic-windows-case`
- Path: `cases/realistic-windows-case`
- Disk input path: `cases/realistic-windows-case/disk_root`
- Source: generated locally by `scripts/create_realistic_artifact_tree.py`
- License/permission: project-owned synthetic artifact data, no external dataset.
- Format: mounted Windows-like artifact tree, not a forensic disk image.
- Size: about 60 KB
- Aggregate tar SHA-256: `4118400f01d7ff45a685a4821fb182f062c2117ed3fa52ea38b03046c5fd8d82`
- Purpose: reproducible smoke demo for the remote SIFT bridge and the full typed-tool workflow while a real Windows image is unavailable.
- Expected artifacts:
  - PowerShell payload under `AppData\Roaming\Microsoft\Windows\Themes`
  - Chrome history and download row for `invoice_update.zip`
  - Prefetch marker for `POWERSHELL.EXE`
  - Amcache text export for `powershell.exe`
  - Scheduled task `ThemeUpdater`
  - Registry autorun export under `CurrentVersion\Run`
  - Security logon XML for user `Analyst`
  - Suspicious downloaded/script files for timeline and YARA-style scanning
- Run output:
  - `runs/realistic-windows-case-script`
  - `runs/realistic-windows-case-final`
- Validation:
  - 10/10 tools succeeded
  - 8/8 expected artifact categories produced evidence
  - 4 retained findings
  - 1 unsupported speculative claim blocked
- Recommended command:

```bash
python3 scripts/create_realistic_artifact_tree.py --case-dir cases/realistic-windows-case
rsync -a cases sift@127.0.0.1:/home/sift/findevil/
RUN_OUTPUT=runs/realistic-windows-case-script bash cases/realistic-windows-case/run_analysis.sh
```

## Generated Raw NTFS Image Demo Case

- Name: `realistic-windows-image`
- Path: `cases/realistic-windows-image`
- Disk input path: `cases/realistic-windows-image/disk.img`
- Source: generated on the SIFT VM by `scripts/create_ntfs_image_from_artifact_tree.sh`
- Source artifacts: `cases/realistic-windows-case/disk_root`
- License/permission: project-owned synthetic artifact data, no external dataset.
- Format: raw NTFS filesystem image, not a native Windows OS install.
- Size: 128 MB
- SHA-256: `4e006be48a4db5d6b10b7ec6336e5c7254fb3c3ae3ecf170c04a53ec66088eb2`
- Purpose: no-Windows image-backed demo proving SIFT can enumerate a real NTFS image while CaseTrace preserves typed evidence and self-correction behavior.
- Run output:
  - `runs/realistic-windows-image`
- Validation:
  - 10/10 tools succeeded
  - 8/8 expected artifact categories produced evidence
  - 4 retained findings
  - 1 unsupported speculative claim blocked
- Recommended command:

```bash
ssh -p 2222 -i vm_assets/ssh/sift_vm_ed25519 sift@127.0.0.1 \
  'cd /home/sift/findevil && OVERWRITE=1 bash scripts/create_ntfs_image_from_artifact_tree.sh'

rsync -a -e "ssh -p 2222 -i vm_assets/ssh/sift_vm_ed25519" \
  sift@127.0.0.1:/home/sift/findevil/cases/realistic-windows-image/disk.img \
  cases/realistic-windows-image/disk.img

bash cases/realistic-windows-image/run_analysis.sh
```

## Final Demo Case

**STATUS:** Ready without Windows. The generated raw NTFS image demo is implemented and validated. A native Windows OS image or external public case is optional future validation.

### Optional Future Native/Public Case
- Name: TBD
- Source: Public DFIR dataset, CTF, or documented forensic case
- License/permission: Verified and documented
- Format: Windows disk image (.E01, .dd, .raw, or equivalent)
- Size: Preferably < 1GB for development speed
- Ground truth: Known artifacts, attack chains, or expected findings documented

### What We Have Ready
- ✅ Code infrastructure to analyze real cases
- ✅ Tool backend selection (fixture or remote SIFT)
- ✅ Evidence linking and finding synthesis
- ✅ Self-correction and verification layer
- ✅ Report generation and audit trails
- ✅ Generated NTFS image workflow when no Windows host is available

### Optional Next Steps
1. Download a Windows forensic dataset with known ground truth
2. Store at `/cases/<case_name>/disk.E01`
3. Run: `python3 -m findevil analyze --case /cases/<case_name> --disk /cases/<case_name>/disk.E01 --profile windows --output runs/real-case-final`
4. Document findings against known artifacts
5. Update ACCURACY_REPORT.md with evaluation results

### Example Public Sources
- DFIR CTF (if available)
- Digital Forensics Research Lab datasets
- Classroom DFIR scenarios with published solutions
- Public incident response reports with IOCs
