# CaseTrace

CaseTrace is a read-only, self-correcting DFIR agent scaffold for the FIND EVIL! hackathon. It uses a typed tool surface, a bounded orchestration loop, and evidence-linked findings so every claim can be traced back to collected artifacts.

## What Works Today
- `python3 -m findevil analyze ...` runs a bounded triage loop with phases for planning, collection, synthesis, verification, self-correction, and finalization.
- `python3 -m findevil mcp-server ...` exposes typed, read-only tools over MCP stdio.
- `python3 -m findevil evaluate ...` compares iteration 1 against the self-corrected run and writes `evaluation.json`.
- `python3 -m findevil analyze ... --tool-backend sift-ssh ...` can collect `timeline_mft` and `prefetch_summary` from a remote x86 SIFT box over SSH.
- A sample Windows persistence case is included under [sample_cases/windows_persistence_case](./sample_cases/windows_persistence_case).
- Every tool returns structured JSON and writes raw artifacts, `events.jsonl`, `tool_calls.jsonl`, `findings.json`, `run_metadata.json`, and `report.md`.

## Quick Start
Run the included sample case:

```bash
python3 -m findevil analyze \
  --case sample_cases/windows_persistence_case \
  --disk sample_cases/windows_persistence_case/image.E01 \
  --profile windows \
  --max-iterations 3 \
  --output runs/windows-persistence-case
```

Run the benchmark harness:

```bash
python3 -m findevil evaluate \
  --case sample_cases/windows_persistence_case \
  --disk sample_cases/windows_persistence_case/image.E01 \
  --profile windows \
  --max-iterations 3 \
  --output runs/windows-persistence-eval
```

## Outputs
Each run creates:
- `report.md`
- `findings.json`
- `events.jsonl`
- `tool_calls.jsonl`
- `run_metadata.json`
- `raw/<tool_name>/*.json`

## Architecture
- The agent never receives raw shell access.
- Collection uses typed, read-only tools only.
- Verification blocks unsupported claims and downgrades weakly supported findings.
- Self-correction only expands collection when corroboration is missing or a tool failed.

More detail lives in [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md).

Submission support docs:
- [Dataset documentation](./docs/DATASETS.md)
- [Accuracy report draft](./docs/ACCURACY_REPORT.md)
- [Devpost story draft](./docs/DEVPOST_DRAFT.md)

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

That keeps the orchestration local while `timeline_mft`, `prefetch_summary`, `registry_autoruns`, and `scheduled_tasks` are collected on the remote host.

Details: [docs/REMOTE_SIFT.md](./docs/REMOTE_SIFT.md)

## Tests
Run:

```bash
python3 -m unittest discover -s tests -v
```
