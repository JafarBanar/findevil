#!/usr/bin/env bash
set -euo pipefail

SIFT_TAG="${SIFT_TAG:-}"
INSTALL_PROTOCOL_SIFT="${INSTALL_PROTOCOL_SIFT:-1}"
CAST_CACHE_ROOT="${CAST_CACHE_ROOT:-/var/cache/cast}"
RELEASE_API="${RELEASE_API:-https://api.github.com/repos/teamdfir/sift-saltstack/releases/latest}"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

require_jammy() {
  local version codename
  version="$(. /etc/os-release && printf '%s' "${VERSION_ID}")"
  codename="$(. /etc/os-release && printf '%s' "${VERSION_CODENAME}")"
  [[ "${version}" == "22.04" ]] || fail "Expected Ubuntu 22.04, found ${version}"
  [[ "${codename}" == "jammy" ]] || fail "Expected Ubuntu codename jammy, found ${codename}"
}

install_base_packages() {
  sudo apt update
  sudo apt install -y curl wget git python3 tar ca-certificates
}

install_cast() {
  if command -v cast >/dev/null 2>&1; then
    return
  fi
  local cast_url
  cast_url="$(
    curl -fsSL https://api.github.com/repos/ekristen/cast/releases/latest |
      python3 -c 'import json, sys; data = json.load(sys.stdin); print(next(asset["browser_download_url"] for asset in data["assets"] if asset["browser_download_url"].endswith("linux-amd64.deb")))'
  )"
  wget "${cast_url}" -O /tmp/cast-linux-amd64.deb
  sudo dpkg -i /tmp/cast-linux-amd64.deb || sudo apt-get -f install -y
}

block_noble_releases() {
  sudo tee /etc/apt/preferences.d/casetrace-block-noble.pref >/dev/null <<'EOF'
Package: *
Pin: release n=noble
Pin-Priority: -10

Package: *
Pin: release n=noble-updates
Pin-Priority: -10

Package: *
Pin: release n=noble-security
Pin-Priority: -10

Package: *
Pin: release a=noble
Pin-Priority: -10

Package: *
Pin: release a=noble-updates
Pin-Priority: -10

Package: *
Pin: release a=noble-security
Pin-Priority: -10
EOF
}

disable_noble_sources() {
  if [[ -f /etc/apt/sources.list.d/ubuntu.sources ]] && grep -Eq 'noble|noble-security|noble-updates' /etc/apt/sources.list.d/ubuntu.sources; then
    sudo mv /etc/apt/sources.list.d/ubuntu.sources /etc/apt/sources.list.d/ubuntu.sources.disabled
  fi
}

resolve_sift_tag() {
  if [[ -n "${SIFT_TAG}" ]]; then
    printf '%s\n' "${SIFT_TAG}"
    return
  fi
  curl -fsSL "${RELEASE_API}" |
    python3 -c 'import json, sys; data = json.load(sys.stdin); print(data["tag_name"])'
}

prefetch_and_patch_sift_source() {
  local sift_tag cache_dir archive_url temp_dir extracted_dir
  sift_tag="$(resolve_sift_tag)"
  cache_dir="${CAST_CACHE_ROOT}/teamdfir_sift-saltstack/${sift_tag}"
  archive_url="https://github.com/teamdfir/sift-saltstack/archive/refs/tags/${sift_tag}.tar.gz"
  temp_dir="$(mktemp -d)"
  trap 'rm -rf "${temp_dir}"' RETURN

  curl -fsSL "${archive_url}" -o "${temp_dir}/sift-saltstack.tar.gz"
  tar -xzf "${temp_dir}/sift-saltstack.tar.gz" -C "${temp_dir}"
  extracted_dir="$(find "${temp_dir}" -maxdepth 1 -type d -name 'sift-saltstack-*' | head -n 1)"
  [[ -n "${extracted_dir}" ]] || fail "Failed to unpack sift-saltstack ${sift_tag}"

  sudo mkdir -p "${cache_dir}"
  sudo rm -rf "${cache_dir}/source"
  sudo mv "${extracted_dir}" "${cache_dir}/source"

  local repo_file
  for repo_file in \
    "${cache_dir}/source/sift/repos/ubuntu-universe.sls" \
    "${cache_dir}/source/sift/repos/ubuntu-multiverse.sls"; do
    [[ -f "${repo_file}" ]] || continue
    sudo python3 - "${repo_file}" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
replacements = {
    "Suites: noble-security": "Suites: jammy-security",
    "Suites: noble-updates": "Suites: jammy-updates",
    "Suites: noble": "Suites: jammy",
    "noble-security": "jammy-security",
    "noble-updates": "jammy-updates",
    "noble ": "jammy ",
}
for original, replacement in replacements.items():
    text = text.replace(original, replacement)
path.write_text(text, encoding="utf-8")
PY
  done
}

assert_jammy_candidates() {
  local policy_output
  policy_output="$(apt-cache policy gcc-11-base python3-dev perl-base)"
  printf '%s\n' "${policy_output}"
  grep -q 'jammy' <<<"${policy_output}" || fail "Expected apt policy output to reference jammy repositories"
  if grep -q 'noble' <<<"${policy_output}"; then
    fail "Noble still appears in apt policy output"
  fi
}

install_sift() {
  if [[ -d /var/cache/cast/installer/saltstack/salt ]] && [[ ! -x /var/cache/cast/installer/saltstack/salt/salt-call ]]; then
    sudo rm -rf /var/cache/cast/installer/saltstack/salt
  fi
  sudo cast install teamdfir/sift
}

install_protocol_sift() {
  if [[ "${INSTALL_PROTOCOL_SIFT}" != "1" ]]; then
    return
  fi
  curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash
}

main() {
  require_jammy
  install_base_packages
  install_cast
  block_noble_releases
  disable_noble_sources
  sudo apt update
  prefetch_and_patch_sift_source
  assert_jammy_candidates
  install_sift
  disable_noble_sources
  sudo apt update
  assert_jammy_candidates
  install_protocol_sift
}

main "$@"
