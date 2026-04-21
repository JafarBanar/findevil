#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_NAME="${VM_NAME:-SIFT Ubuntu 22.04 x86_64}"
GUEST_USER="${GUEST_USER:-sift}"
GUEST_PASSWORD="${GUEST_PASSWORD:-sift}"
GUEST_HOST="${GUEST_HOST:-127.0.0.1}"
GUEST_PORT="${GUEST_PORT:-2222}"
SSH_KEY="${SSH_KEY:-${ROOT_DIR}/vm_assets/ssh/sift_vm_ed25519}"

python3 "${ROOT_DIR}/scripts/bootstrap_utm_sift_vm.py" \
  --vm-name "${VM_NAME}" \
  --user "${GUEST_USER}" \
  --password "${GUEST_PASSWORD}" \
  --recreate \
  --wait-for-ssh \
  "$@"

"${ROOT_DIR}/scripts/install_sift_in_guest.sh" "${SSH_KEY}" "${GUEST_USER}" "${GUEST_HOST}" "${GUEST_PORT}"
