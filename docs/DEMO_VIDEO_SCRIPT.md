# Demo Video Script

Use this as the under-5-minute recording plan for the generated NTFS image demo.

## 0:00-0:25 Problem

AI-assisted attackers can generate plausible intrusion steps faster than human responders can manually collect and connect Windows artifacts. CaseTrace answers with a read-only DFIR agent that must cite evidence IDs for every claim.

## 0:25-0:55 Architecture

Show `docs/ARCHITECTURE.md`.

Key points:
- Bounded orchestration loop
- Typed forensic tools only
- Remote SIFT bridge over SSH
- Evidence-linked findings
- Verification blocks unsupported claims

## 0:55-1:35 No-Windows Image Setup

Show:

```bash
ls -lh cases/realistic-windows-image/disk.img
shasum -a 256 cases/realistic-windows-image/disk.img
sed -n '1,120p' docs/NTFS_IMAGE_VALIDATION.md
```

Say that the image is a 128 MB raw NTFS filesystem generated on SIFT from controlled artifacts because no Windows host is available.

## 1:35-2:20 Agent Run

Show:

```bash
bash cases/realistic-windows-image/run_analysis.sh
```

If re-running is too slow during recording, show the completed summary:

```bash
jq '.summary' runs/realistic-windows-image/run_metadata.json
```

## 2:20-3:10 Tool Traceability

Show:

```bash
bash scripts/print_demo_highlights.sh
```

Point out:
- 10/10 typed tools succeeded
- Raw artifact paths exist for each tool
- Findings cite evidence IDs

## 3:10-4:05 Self-Correction

Show:

```bash
jq '.iteration_history[] | {iteration, tools_run, issues}' runs/realistic-windows-image/run_metadata.json
```

Point out:
- Iteration 1 found weak browser/prefetch evidence
- Iteration 2 collected corroborating timeline, registry, scheduled task, Amcache, and YARA evidence
- Unsupported credential-theft speculation stayed blocked

## 4:05-4:45 Final Report

Show:

```bash
sed -n '1,180p' runs/realistic-windows-image/report.md
```

Close on the result:
- 4 findings
- 2 confirmed, 2 inference
- 1 unsupported claim blocked
- 0 tool failures

## 4:45-5:00 Limitation

Be explicit: this is a reproducible image-backed controlled demo, not a native Windows OS install. The next validation step is a public or native Windows image with known ground truth.
