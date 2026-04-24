#!/bin/bash
set -euo pipefail

RUN_OUTPUT="${RUN_OUTPUT:-runs/cfreds-data-leakage-pc}"
REMOTE_DISK_PATH="${REMOTE_DISK_PATH:-/home/sift/public_cases/cfreds-data-leakage-pc/image/cfreds_2015_data_leakage_pc.dd}"
REMOTE_TIMEOUT_SEC="${REMOTE_TIMEOUT_SEC:-480}"

python3 -m findevil analyze \
  --case cases/cfreds-data-leakage-pc \
  --disk cases/cfreds-data-leakage-pc/cfreds_2015_data_leakage_pc.dd \
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
  --remote-timeout-sec "$REMOTE_TIMEOUT_SEC"
