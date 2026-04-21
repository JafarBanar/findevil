# Local UTM x86 SIFT Guest

This repo can bootstrap a local x86 Ubuntu guest in UTM on an Apple Silicon Mac and rebuild it as a disposable SIFT lab when the guest gets contaminated.

## What It Automates
- creates a repo-local SSH keypair
- renders cloud-init files
- builds a `cidata` seed ISO
- creates a QEMU x86_64 VM in UTM
- optionally deletes and recreates an existing VM of the same name
- configures an emulated VLAN `virtio-net-pci` NIC for the guest
- forwards host `127.0.0.1:2222` to guest SSH on port `22`
- seeds DHCP netplan config so Ubuntu brings the VM NIC up automatically
- resizes the guest disk to `80 GiB` when `qemu-img` is available on the Mac host
- hardens a fresh Jammy guest before SIFT install so Noble repositories cannot poison apt

## What You Still Need
- an official Ubuntu 22.04 amd64 cloud image in `vm_assets/images/`
- `qemu-img` on the Mac host if you want bootstrap to auto-grow the guest disk
- macOS approval for UTM automation if prompted
- enough RAM and disk for the VM

## Main Commands
Bootstrap the VM after the cloud image is downloaded:

```bash
python3 scripts/bootstrap_utm_sift_vm.py --wait-for-ssh
```

Rebuild the VM from scratch and run the hardened SIFT installer:

```bash
scripts/rebuild_utm_sift_vm.sh
```

If `qemu-img` is missing, install it once with:

```bash
brew install qemu
```

Query the guest IP if needed:

```bash
utmctl ip-address "SIFT Ubuntu 22.04 x86_64"
```

Install SIFT inside the guest once SSH is up:

```bash
scripts/install_sift_in_guest.sh vm_assets/ssh/sift_vm_ed25519 sift 127.0.0.1 2222
```

## Hardened SIFT Install
The guest installer now:
- verifies the guest is Ubuntu `22.04` / `jammy`
- writes an apt preferences file that blocks `noble`, `noble-updates`, and `noble-security`
- disables a stray `ubuntu.sources` file if it already points at Noble
- prefetches the latest `teamdfir/sift-saltstack` release into the Cast cache
- rewrites the known-bad `ubuntu-universe.sls` and `ubuntu-multiverse.sls` files from Noble to Jammy before `cast install`
- re-checks `apt-cache policy` before and after `sudo cast install teamdfir/sift`
- installs Protocol SIFT after SIFT succeeds

If the current guest already has mixed `22.04` and `24.04` packages installed, rebuild it instead of trying to salvage it in place.
