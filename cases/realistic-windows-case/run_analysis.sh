#!/bin/bash
set -e

RUN_OUTPUT="${RUN_OUTPUT:-runs/realistic-windows-case-final}"

python3 -m findevil analyze \
  --case cases/realistic-windows-case \
  --disk cases/realistic-windows-case/disk_root \
  --profile windows \
  --max-iterations 3 \
  --output "$RUN_OUTPUT" \
  --tool-backend sift-ssh \
  --remote-host 127.0.0.1 \
  --remote-port 2222 \
  --remote-user sift \
  --remote-workdir /home/sift/findevil \
  --remote-disk-path /home/sift/findevil/cases/realistic-windows-case/disk_root \
  --remote-identity-file vm_assets/ssh/sift_vm_ed25519 \
  --remote-insecure-no-host-key-check \
  --remote-timeout-sec 180
