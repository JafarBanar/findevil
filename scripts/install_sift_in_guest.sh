#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <ssh-private-key> <guest-user> [guest-host] [port]" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="${SCRIPT_DIR}/install_sift_guest_payload.sh"

if [[ ! -f "${PAYLOAD}" ]]; then
  echo "missing payload script: ${PAYLOAD}" >&2
  exit 1
fi

SSH_KEY="$1"
GUEST_USER="$2"
GUEST_HOST="${3:-127.0.0.1}"
HOST_PORT="${4:-2222}"

SSH_OPTS=(
  -i "$SSH_KEY"
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -p "$HOST_PORT"
)

ssh "${SSH_OPTS[@]}" "${GUEST_USER}@${GUEST_HOST}" "bash -s" < "${PAYLOAD}"
