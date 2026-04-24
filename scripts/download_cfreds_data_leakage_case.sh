#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOST="${REMOTE_HOST:-127.0.0.1}"
REMOTE_PORT="${REMOTE_PORT:-2222}"
REMOTE_USER="${REMOTE_USER:-sift}"
REMOTE_KEY="${REMOTE_KEY:-${ROOT_DIR}/vm_assets/ssh/sift_vm_ed25519}"
REMOTE_BASE="${REMOTE_BASE:-/home/sift/public_cases/cfreds-data-leakage-pc}"

ssh -n -p "${REMOTE_PORT}" \
  -o BatchMode=yes \
  -i "${REMOTE_KEY}" \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  "${REMOTE_USER}@${REMOTE_HOST}" \
  "mkdir -p '${REMOTE_BASE}/raw' '${REMOTE_BASE}/image' '${REMOTE_BASE}/reference'"

for url in \
  "https://cfreds-archive.nist.gov/data_leakage_case/images/pc/cfreds_2015_data_leakage_pc.7z.001" \
  "https://cfreds-archive.nist.gov/data_leakage_case/images/pc/cfreds_2015_data_leakage_pc.7z.002" \
  "https://cfreds-archive.nist.gov/data_leakage_case/images/pc/cfreds_2015_data_leakage_pc.7z.003" \
  "https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf"; do
  ssh -n -p "${REMOTE_PORT}" \
    -o BatchMode=yes \
    -i "${REMOTE_KEY}" \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    "${REMOTE_USER}@${REMOTE_HOST}" \
    "cd '${REMOTE_BASE}/raw' && wget -c -nv '${url}'"
done

ssh -n -p "${REMOTE_PORT}" \
  -o BatchMode=yes \
  -i "${REMOTE_KEY}" \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  "${REMOTE_USER}@${REMOTE_HOST}" \
  "cd '${REMOTE_BASE}/image' && if [ ! -f cfreds_2015_data_leakage_pc.dd ]; then 7z x -y '../raw/cfreds_2015_data_leakage_pc.7z.001'; fi"
