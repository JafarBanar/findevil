# Remote x86 SIFT

Yes, you can use a remote x86 machine running SIFT.

## Recommended Setup
1. Provision an x86 Linux or VM host that can run SIFT comfortably.
2. Install or boot SIFT on that machine.
3. Enable SSH access to the guest or host.
4. Clone this repo onto the remote machine at a stable path such as `/home/sift/findevil`.
5. Put your evidence image on the remote machine, for example `/cases/case1/image.E01`.
6. Run CaseTrace locally with `--tool-backend sift-ssh`.

## What the Current Integration Does
The current remote bridge executes these tools remotely:
- `timeline_mft`
- `prefetch_summary`
- `registry_autoruns`
- `scheduled_tasks`

The rest of the tools remain fixture-backed for now, so the cleanest path is:
- start with the included sample case
- replace more fixture tools one by one with remote SIFT wrappers

## Preflight Check
Before a full run, verify SSH access and the remote bridge:

```bash
python3 -m findevil check-remote \
  --tool-backend sift-ssh \
  --remote-host your-real-host \
  --remote-user sift \
  --remote-workdir /home/sift/findevil
```

For the disposable local UTM VM, use the generated SSH key and localhost port forward:

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

## Remote Command Example
```bash
python3 -m findevil analyze \
  --case sample_cases/windows_persistence_case \
  --disk sample_cases/windows_persistence_case/image.E01 \
  --profile windows \
  --max-iterations 3 \
  --output runs/remote-case \
  --tool-backend sift-ssh \
  --remote-host your-sift-host \
  --remote-user sift \
  --remote-workdir /home/sift/findevil \
  --remote-disk-path /cases/case1/image.E01
```

## How It Works
- Local CaseTrace still runs the orchestrator, verification, and reporting.
- The local process uses SSH to call [scripts/sift_tool_bridge.py](../scripts/sift_tool_bridge.py) on the remote host.
- The bridge emits JSON back over stdout.
- CaseTrace stores the remote command, stdout, stderr, and parsed evidence in run artifacts.

## Practical Notes
- If the remote path is already a read-only mounted directory, `sift_tool_bridge.py` will walk the directory instead of calling `fls`.
- If the remote path is an image file, the bridge tries `fls -r -p` to enumerate artifacts.
- Current remote support is intentionally narrow so we can expand it safely.

## About the OVA
You do not need the local `.ova` if you are using a remote x86 SIFT box.

Keep it only if you want a local fallback lab.
Otherwise, move it outside the repo directory or delete it to save space.
