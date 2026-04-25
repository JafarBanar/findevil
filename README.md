# CaseTrace

CaseTrace is a read-only, self-correcting DFIR agent for the FIND EVIL! hackathon. It investigates Windows evidence through typed tools instead of free-form shell access, preserves raw outputs, and links every final claim back to collected artifacts.

## Quick Links
- Demo video: https://youtu.be/4jvu_qK-r5Y
- Architecture diagram: [PNG](./docs/architecture_diagram.png), [PDF](./docs/architecture_diagram.pdf)
- Dataset documentation: [docs/DATASETS.md](./docs/DATASETS.md)
- Accuracy report: [docs/ACCURACY_REPORT.md](./docs/ACCURACY_REPORT.md)
- Public Windows validation: [docs/CFREDS_DATA_LEAKAGE_VALIDATION.md](./docs/CFREDS_DATA_LEAKAGE_VALIDATION.md)
- Execution logs: [docs/EXECUTION_LOGS.md](./docs/EXECUTION_LOGS.md)
- Validated demo notes: [docs/NTFS_IMAGE_VALIDATION.md](./docs/NTFS_IMAGE_VALIDATION.md)

## Highlights
- `python3 -m findevil analyze ...` runs a bounded triage loop with phases for planning, collection, synthesis, verification, self-correction, and finalization.
- `python3 -m findevil mcp-server ...` exposes typed, read-only tools over MCP stdio.
- `python3 -m findevil evaluate ...` compares iteration 1 against the self-corrected run and writes `evaluation.json`.
- `python3 -m findevil analyze ... --tool-backend sift-ssh ...` can collect Windows timeline, Prefetch, Amcache, registry autoruns, scheduled tasks, browser history, user logons, and YARA-style hits from a remote x86 SIFT box over SSH.
- A sample Windows persistence case is included under [sample_cases/windows_persistence_case](./sample_cases/windows_persistence_case).
- A no-Windows raw NTFS image demo is included under [cases/realistic-windows-image](./cases/realistic-windows-image).
- A public native-Windows validation case wrapper is included under [cases/cfreds-data-leakage-pc](./cases/cfreds-data-leakage-pc).
- The validated no-Windows demo run retained 4 findings, blocked 1 unsupported claim, and is summarized in [docs/NTFS_IMAGE_VALIDATION.md](./docs/NTFS_IMAGE_VALIDATION.md).
- A public NIST CFReDS validation run is documented in [docs/CFREDS_DATA_LEAKAGE_VALIDATION.md](./docs/CFREDS_DATA_LEAKAGE_VALIDATION.md).
- Every tool returns structured JSON and writes raw artifacts, `events.jsonl`, `tool_calls.jsonl`, `findings.json`, `run_metadata.json`, and `report.md`.

## Quick Start
Fastest local path: run the included fixture case.

```bash
python3 -m findevil analyze \
  --case sample_cases/windows_persistence_case \
  --disk sample_cases/windows_persistence_case/image.E01 \
  --profile windows \
  --max-iterations 3 \
  --output runs/windows-persistence-case
```

Compare iteration 1 against the self-corrected final run:

```bash
python3 -m findevil evaluate \
  --case sample_cases/windows_persistence_case \
  --disk sample_cases/windows_persistence_case/image.E01 \
  --profile windows \
  --max-iterations 3 \
  --output runs/windows-persistence-eval
```

If you want the no-Windows image-backed demo shown in the submission, jump to [No-Windows Image Demo](#no-windows-image-demo).

## Outputs
Each run creates:
- `report.md`
- `findings.json`
- `events.jsonl`
- `tool_calls.jsonl`
- `run_metadata.json`
- `raw/<tool_name>/*.json`

The validated demo output is summarized in [docs/NTFS_IMAGE_VALIDATION.md](./docs/NTFS_IMAGE_VALIDATION.md).

## Architecture
- The agent never receives raw shell access.
- Collection uses typed, read-only tools only.
- Verification blocks unsupported claims and downgrades weakly supported findings.
- Self-correction only expands collection when corroboration is missing or a tool failed.

More detail lives in [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md), with upload-ready diagram assets in [PNG](./docs/architecture_diagram.png) and [PDF](./docs/architecture_diagram.pdf).

Submission support docs:
- [Dataset documentation](./docs/DATASETS.md)
- [Accuracy report draft](./docs/ACCURACY_REPORT.md)
- [Public Windows validation notes](./docs/CFREDS_DATA_LEAKAGE_VALIDATION.md)
- [Execution logs](./docs/EXECUTION_LOGS.md)
- [Devpost submission copy](./docs/DEVPOST_SUBMISSION.md)
- [Architecture diagram (PNG)](./docs/architecture_diagram.png)
- [Architecture diagram (PDF)](./docs/architecture_diagram.pdf)
- [Artifact-tree validation](./docs/ARTIFACT_TREE_VALIDATION.md)
- [Generated NTFS image validation](./docs/NTFS_IMAGE_VALIDATION.md)
- [Demo video script](./docs/DEMO_VIDEO_SCRIPT.md)
- [Devpost story draft](./docs/DEVPOST_DRAFT.md)

## No-Windows Image Demo
If you do not have Windows, use the SIFT VM to generate a raw NTFS image from the controlled artifacts:

```bash
ssh -p 2222 -i vm_assets/ssh/sift_vm_ed25519 sift@127.0.0.1 \
  'cd /home/sift/findevil && OVERWRITE=1 bash scripts/create_ntfs_image_from_artifact_tree.sh'

rsync -a -e "ssh -p 2222 -i vm_assets/ssh/sift_vm_ed25519" \
  sift@127.0.0.1:/home/sift/findevil/cases/realistic-windows-image/disk.img \
  cases/realistic-windows-image/disk.img

bash cases/realistic-windows-image/run_analysis.sh
```

The validated local run is `runs/realistic-windows-image`.

## Public Ground-Truth Validation
Use the public NIST CFReDS Windows image wrapper when you want a native-Windows honesty check instead of the synthetic demo path:

```bash
bash scripts/download_cfreds_data_leakage_case.sh
bash cases/cfreds-data-leakage-pc/run_analysis.sh
```

The current public validation notes live in [docs/CFREDS_DATA_LEAKAGE_VALIDATION.md](./docs/CFREDS_DATA_LEAKAGE_VALIDATION.md). The latest run is `runs/cfreds-data-leakage-pc-v3`.

Render the local draft demo video:

```bash
bash scripts/render_demo_video.sh
```

## No-VM Development
You do not need the SIFT VM to build most of this project.

Use the host machine to:
- develop the MCP server
- build the orchestration loop
- test the verifier and report generator
- iterate on fixture-backed forensic exports

Use a real SIFT VM only when you want:
- actual forensic tooling runs
- Protocol SIFT installation
- final demo capture for the hackathon

Details: [docs/NO_VM.md](./docs/NO_VM.md)

## Local UTM Recovery
If you are developing on an Apple Silicon Mac, the repo now includes a disposable local UTM workflow for Ubuntu `22.04` x86_64 plus a hardened SIFT installer that blocks the known Noble-on-Jammy repo contamination path.

Quickest rebuild path:

```bash
scripts/rebuild_utm_sift_vm.sh
```

That command recreates the VM, waits for SSH, hardens apt against `noble*`, patches the cached `teamdfir/sift-saltstack` repo files to `jammy`, installs SIFT, and then installs Protocol SIFT.

Details: [docs/LOCAL_UTM.md](./docs/LOCAL_UTM.md)

## Real SIFT Integration
If you have the SIFT appliance, import the OVA into an x86-capable VM environment, boot it, then install Protocol SIFT inside the guest:

```bash
curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash
```

Details: [docs/SETUP_SIFT.md](./docs/SETUP_SIFT.md)

## Remote x86 SIFT
You can keep CaseTrace on your Mac and point selected tools at a remote SIFT host over SSH.

First verify the host and remote bridge:

```bash
python3 -m findevil check-remote \
  --tool-backend sift-ssh \
  --remote-host your-real-host \
  --remote-user sift \
  --remote-workdir /home/sift/findevil
```

For the disposable local UTM VM created by this repo:

```bash
python3 -m findevil check-remote \
  --tool-backend sift-ssh \
  --remote-host 127.0.0.1 \
  --remote-port 2222 \
  --remote-user sift \
  --remote-identity-file vm_assets/ssh/sift_vm_ed25519 \
  --remote-insecure-no-host-key-check \
  --remote-workdir /home/sift/findevil
```

Example:

```bash
python3 -m findevil analyze \
  --case sample_cases/windows_persistence_case \
  --disk sample_cases/windows_persistence_case/image.E01 \
  --profile windows \
  --max-iterations 3 \
  --output runs/remote-case \
  --tool-backend sift-ssh \
  --remote-host 203.0.113.10 \
  --remote-user sift \
  --remote-workdir /home/sift/findevil \
  --remote-disk-path /cases/case1/image.E01
```

That keeps the orchestration local while the core Windows triage tools are collected on the remote host.

Details: [docs/REMOTE_SIFT.md](./docs/REMOTE_SIFT.md)

## Tests
Run:

```bash
python3 -m unittest discover -s tests -v
```
