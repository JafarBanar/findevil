#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import os
import plistlib
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
VM_ASSETS = ROOT / "vm_assets"
SSH_DIR = VM_ASSETS / "ssh"
CLOUD_INIT_DIR = VM_ASSETS / "cloud-init"
IMAGES_DIR = VM_ASSETS / "images"
DEFAULT_KEY = SSH_DIR / "sift_vm_ed25519"
DEFAULT_SEED = CLOUD_INIT_DIR / "seed.iso"
DEFAULT_IMAGE = IMAGES_DIR / "ubuntu-22.04-server-cloudimg-amd64-disk-kvm.img"
DEFAULT_VM_NAME = "SIFT Ubuntu 22.04 x86_64"
DEFAULT_DISK_SIZE_GIB = 80


def run(command: list[str], *, check: bool = True, capture: bool = False, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=check,
        text=True,
        capture_output=capture,
        env=env,
    )


def ensure_dirs() -> None:
    for path in (VM_ASSETS, SSH_DIR, CLOUD_INIT_DIR, IMAGES_DIR):
        path.mkdir(parents=True, exist_ok=True)


def ensure_keypair(private_key: Path) -> Path:
    public_key = Path(f"{private_key}.pub")
    if not private_key.exists():
        run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(private_key)])
    if not public_key.exists():
        raise FileNotFoundError(f"Missing public key {public_key}")
    return public_key


def mac_for_vm(vm_name: str) -> str:
    digest = hashlib.md5(vm_name.encode("utf-8")).digest()
    return "52:54:{:02x}:{:02x}:{:02x}:{:02x}".format(*digest[:4])


def render_cloud_init(public_key: Path, user: str, hostname: str, password: str, mac_address: str) -> tuple[Path, Path, Path]:
    pubkey_text = public_key.read_text(encoding="utf-8").strip()
    user_data = CLOUD_INIT_DIR / "user-data"
    meta_data = CLOUD_INIT_DIR / "meta-data"
    network_config = CLOUD_INIT_DIR / "network-config"
    user_data.write_text(
        "\n".join(
            [
                "#cloud-config",
                f"hostname: {hostname}",
                "manage_etc_hosts: true",
                "write_files:",
                "  - path: /etc/netplan/01-utm-dhcp.yaml",
                "    permissions: '0644'",
                "    content: |",
                "      network:",
                "        version: 2",
                "        ethernets:",
                "          uplink:",
                "            match:",
                f'              macaddress: "{mac_address}"',
                "            dhcp4: true",
                "            optional: true",
                "users:",
                "  - default",
                f"  - name: {user}",
                "    gecos: SIFT Operator",
                "    groups: [adm, sudo]",
                "    shell: /bin/bash",
                "    lock_passwd: false",
                "    sudo: ALL=(ALL) NOPASSWD:ALL",
                "    ssh_authorized_keys:",
                f"      - {pubkey_text}",
                "ssh_pwauth: true",
                "chpasswd:",
                "  expire: false",
                "  list: |",
                f"    {user}:{password}",
                "bootcmd:",
                "  - netplan generate || true",
                "  - netplan apply || true",
                "runcmd:",
                "  - netplan generate || true",
                "  - netplan apply || true",
                "  - systemctl enable --now ssh",
                "  - systemctl restart ssh || systemctl restart sshd || true",
                "  - systemctl enable --now qemu-guest-agent || true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    meta_data.write_text(
        "\n".join(
            [
                f"instance-id: {hostname}",
                f"local-hostname: {hostname}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    network_config.write_text(
        "\n".join(
            [
                "version: 2",
                "ethernets:",
                "  uplink:",
                "    match:",
                f'      macaddress: "{mac_address}"',
                "    dhcp4: true",
                "    optional: true",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return user_data, meta_data, network_config


def create_seed_iso(seed_iso: Path) -> None:
    build_target = seed_iso.with_suffix(".build.iso")
    cdr_path = Path(f"{build_target}.cdr")
    if cdr_path.exists():
        cdr_path.unlink()
    if build_target.exists():
        build_target.unlink()
    run(
        [
            "hdiutil",
            "makehybrid",
            "-o",
            str(build_target),
            str(CLOUD_INIT_DIR),
            "-iso",
            "-joliet",
            "-default-volume-name",
            "cidata",
        ]
    )
    if cdr_path.exists():
        cdr_path.rename(build_target)
    if seed_iso.exists():
        seed_iso.write_bytes(build_target.read_bytes())
        build_target.unlink()
    else:
        build_target.rename(seed_iso)


def create_vm(vm_name: str, image_path: Path, seed_iso: Path, memory_mib: int, cpu_cores: int, host_ssh_port: int) -> None:
    mac_address = mac_for_vm(vm_name)
    create_script = (
        f'tell application "UTM" to activate\n'
        f'tell application "UTM" to set img to (POSIX file "{image_path}")\n'
        f'tell application "UTM" to set seed to (POSIX file "{seed_iso}")\n'
        f'tell application "UTM" to if not (exists virtual machine named "{vm_name}") then '
        f'make new virtual machine with properties {{backend:qemu, configuration:{{name:"{vm_name}", architecture:"x86_64", drives:{{{{source:img}}, {{removable:true, source:seed}}}}}}}}'
    )
    run(["osascript", "-e", create_script])
    update_vm_config(vm_name, seed_iso, memory_mib, cpu_cores, mac_address, host_ssh_port)


def vm_exists(vm_name: str) -> bool:
    query = subprocess.run(
        ["utmctl", "status", vm_name],
        text=True,
        capture_output=True,
    )
    return query.returncode == 0


def stop_vm(vm_name: str) -> None:
    if not vm_exists(vm_name):
        return
    subprocess.run(["utmctl", "stop", vm_name], check=False)
    deadline = time.time() + 30
    while time.time() < deadline:
        status = subprocess.run(
            ["utmctl", "status", vm_name],
            text=True,
            capture_output=True,
        )
        if status.returncode != 0 or "stopped" in status.stdout:
            return
        time.sleep(1)


def delete_vm(vm_name: str) -> None:
    if not vm_exists(vm_name):
        return
    applescript = (
        f'tell application "UTM"\n'
        f'  if exists virtual machine named "{vm_name}" then\n'
        f'    delete virtual machine named "{vm_name}"\n'
        f'  end if\n'
        f'end tell'
    )
    run(["osascript", "-e", applescript])


def vm_bundle_path(vm_name: str) -> Path:
    return Path.home() / "Library/Containers/com.utmapp.UTM/Data/Documents" / f"{vm_name}.utm"


def wait_for_vm_bundle(vm_name: str, timeout_sec: int = 30) -> Path:
    bundle = vm_bundle_path(vm_name)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        config_path = bundle / "config.plist"
        if config_path.exists():
            return bundle
        time.sleep(0.5)
    raise TimeoutError(f"Timed out waiting for VM bundle for {vm_name}")


def update_vm_config(vm_name: str, seed_iso: Path, memory_mib: int, cpu_cores: int, mac_address: str, host_ssh_port: int) -> None:
    bundle = wait_for_vm_bundle(vm_name)
    config_path = bundle / "config.plist"
    data_dir = bundle / "Data"
    data_dir.mkdir(parents=True, exist_ok=True)
    with config_path.open("rb") as handle:
        config = plistlib.load(handle)

    system = config.setdefault("System", {})
    system["MemorySize"] = memory_mib
    system["CPUCount"] = cpu_cores
    system["ForceMulticore"] = cpu_cores > 1

    qemu = config.setdefault("QEMU", {})
    qemu["Hypervisor"] = False

    network = config.setdefault("Network", [])
    port_forward = [
        {
            "Protocol": "TCP",
            "HostAddress": "127.0.0.1",
            "HostPort": host_ssh_port,
            "GuestAddress": "",
            "GuestPort": 22,
        }
    ]
    if network:
        network[0]["Hardware"] = "virtio-net-pci"
        network[0]["Mode"] = "Emulated"
        network[0]["IsolateFromHost"] = False
        network[0]["MacAddress"] = mac_address
        network[0]["PortForward"] = port_forward
    else:
        network.append(
            {
                "Hardware": "virtio-net-pci",
                "IsolateFromHost": False,
                "MacAddress": mac_address,
                "Mode": "Emulated",
                "PortForward": port_forward,
            }
        )

    seed_target = data_dir / seed_iso.name
    seed_target.write_bytes(seed_iso.read_bytes())

    drives = config.setdefault("Drive", [])
    if len(drives) > 1:
        drives[1]["ImageName"] = seed_target.name
        drives[1]["ImageType"] = "CD"
        drives[1]["Interface"] = "IDE"
        drives[1]["InterfaceVersion"] = 1
        drives[1]["ReadOnly"] = True
    else:
        drives.append(
            {
                "Identifier": "",
                "ImageName": seed_target.name,
                "ImageType": "CD",
                "Interface": "IDE",
                "InterfaceVersion": 1,
                "ReadOnly": True,
            }
        )

    with config_path.open("wb") as handle:
        plistlib.dump(config, handle)


def vm_disk_path(vm_name: str) -> Path:
    bundle = vm_bundle_path(vm_name)
    config_path = bundle / "config.plist"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing VM config: {config_path}")
    with config_path.open("rb") as handle:
        config = plistlib.load(handle)
    for drive in config.get("Drive", []):
        if drive.get("ImageType") == "Disk" and drive.get("ImageName"):
            return bundle / "Data" / drive["ImageName"]
    raise FileNotFoundError(f"Could not locate a primary disk image in {config_path}")


def find_qemu_img() -> str | None:
    resolved = subprocess.run(
        ["bash", "-lc", "command -v qemu-img"],
        text=True,
        capture_output=True,
    )
    if resolved.returncode == 0:
        candidate = resolved.stdout.strip()
        if candidate:
            return candidate
    return None


def resize_vm_disk(vm_name: str, disk_size_gib: int) -> tuple[Path, bool]:
    disk_path = vm_disk_path(vm_name)
    qemu_img = find_qemu_img()
    if qemu_img is None:
        return disk_path, False
    run([qemu_img, "resize", str(disk_path), f"{disk_size_gib}G"])
    return disk_path, True


def reload_utm() -> None:
    subprocess.run(["osascript", "-e", 'tell application "UTM" to quit'], check=False)
    time.sleep(3)


def start_vm(vm_name: str) -> None:
    applescript = (
        f'tell application "UTM" to activate\n'
        f'tell application "UTM" to set vm to virtual machine named "{vm_name}"\n'
        f'tell application "UTM" to start vm'
    )
    run(["osascript", "-e", applescript])


def candidate_guest_ips(vm_name: str) -> list[str]:
    candidates: list[str] = []
    ip_lookup = subprocess.run(
        ["utmctl", "ip-address", vm_name],
        text=True,
        capture_output=True,
    )
    if ip_lookup.returncode == 0:
        for line in ip_lookup.stdout.splitlines():
            candidate = line.strip()
            if candidate and "." in candidate and candidate not in candidates:
                candidates.append(candidate)
    for host_octet in range(2, 11):
        fallback = f"192.168.64.{host_octet}"
        if fallback not in candidates:
            candidates.append(fallback)
    return candidates


def wait_for_ssh(user: str, identity_file: Path, timeout_sec: int, vm_name: str, host_ssh_port: int) -> str:
    start = time.time()
    while time.time() - start < timeout_sec:
        for guest_ip, port in [("127.0.0.1", host_ssh_port), *[(ip, 22) for ip in candidate_guest_ips(vm_name)]]:
            command = [
                "ssh",
                "-i",
                str(identity_file),
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "ConnectTimeout=5",
                "-p",
                str(port),
                f"{user}@{guest_ip}",
                "echo ready",
            ]
            completed = subprocess.run(command, text=True, capture_output=True)
            if completed.returncode == 0 and "ready" in completed.stdout:
                return guest_ip
        time.sleep(5)
    raise TimeoutError("Timed out waiting for SSH on the local UTM guest.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare UTM assets for a local x86 SIFT guest.")
    parser.add_argument("--user", default="sift")
    parser.add_argument("--password", default="sift")
    parser.add_argument("--hostname", default="sift-vm")
    parser.add_argument("--vm-name", default=DEFAULT_VM_NAME)
    parser.add_argument("--image", default=str(DEFAULT_IMAGE))
    parser.add_argument("--memory-mib", type=int, default=8192)
    parser.add_argument("--cpu-cores", type=int, default=4)
    parser.add_argument("--disk-size-gib", type=int, default=DEFAULT_DISK_SIZE_GIB)
    parser.add_argument("--host-ssh-port", type=int, default=2222)
    parser.add_argument("--recreate", action="store_true")
    parser.add_argument("--wait-for-ssh", action="store_true")
    parser.add_argument("--ssh-timeout-sec", type=int, default=600)
    args = parser.parse_args(argv)

    ensure_dirs()
    public_key = ensure_keypair(DEFAULT_KEY)
    render_cloud_init(public_key, args.user, args.hostname, args.password, mac_for_vm(args.vm_name))
    create_seed_iso(DEFAULT_SEED)

    image_path = Path(args.image)
    if not image_path.exists():
        raise FileNotFoundError(f"Missing cloud image: {image_path}")

    if args.recreate:
        stop_vm(args.vm_name)
        delete_vm(args.vm_name)

    create_vm(args.vm_name, image_path, DEFAULT_SEED, args.memory_mib, args.cpu_cores, args.host_ssh_port)
    vm_disk, resized = resize_vm_disk(args.vm_name, args.disk_size_gib)
    reload_utm()
    start_vm(args.vm_name)

    guest_ip = None
    if args.wait_for_ssh:
        guest_ip = wait_for_ssh(args.user, DEFAULT_KEY, args.ssh_timeout_sec, args.vm_name, args.host_ssh_port)

    print(
        "\n".join(
            [
                f"VM name: {args.vm_name}",
                f"SSH key: {DEFAULT_KEY}",
                f"Guest password: {args.password}",
                f"Seed ISO: {DEFAULT_SEED}",
                f"VM disk: {vm_disk}",
                (
                    f"Disk resize: resized guest disk to {args.disk_size_gib} GiB"
                    if resized
                    else f"Disk resize: skipped because qemu-img was not found; install qemu and resize {vm_disk}"
                ),
                f'Guest IP query: utmctl ip-address "{args.vm_name}"',
                f"Guest SSH target: ssh -i {DEFAULT_KEY} -p {args.host_ssh_port} {args.user}@127.0.0.1",
                f"Detected guest IP: {guest_ip or '<not detected>'}",
            ]
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
