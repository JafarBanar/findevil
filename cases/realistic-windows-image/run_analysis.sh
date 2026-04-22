#!/bin/bash
set -e

RUN_OUTPUT="${RUN_OUTPUT:-runs/realistic-windows-image}"
REMOTE_DISK_PATH="${REMOTE_DISK_PATH:-/home/sift/findevil/cases/realistic-windows-image/disk.img}"

python3 -m findevil analyze \
  --case cases/realistic-windows-image \
  --disk cases/realistic-windows-image/disk.img \
  --profile windows \
  --max-iterations 3 \
  --output "$RUN_OUTPUT" \
  --tool-backend sift-ssh \
  --remote-host 127.0.0.1 \
  --remote-port 2222 \
  --remote-user sift \
  --remote-workdir /home/sift/findevil \
  --remote-disk-path "$REMOTE_DISK_PATH" \
  --remote-identity-file vm_assets/ssh/sift_vm_ed25519 \
  --remote-insecure-no-host-key-check \
  --remote-timeout-sec 240
