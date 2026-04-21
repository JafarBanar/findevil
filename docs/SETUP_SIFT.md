# SIFT Setup

## About the OVA
`sift-2026.03.24.ova` is the SIFT appliance image. Keep it outside git and import it into a VM product that can run x86 guests.

If you decide to use a remote x86 SIFT host instead, you do not need to keep the local OVA in this repo directory.

## Apple Silicon Note
If you are on an Apple Silicon Mac, the OVA may be slow or awkward locally because SIFT appliances are typically x86-focused.

Best options:
- use an x86 Windows/Linux host with VirtualBox or VMware
- use a remote x86 VM
- use local fixture-backed development first, then finish integration on x86

## Once the VM Boots
Inside the SIFT guest:

```bash
curl -fsSL https://raw.githubusercontent.com/teamdfir/protocol-sift/main/install.sh | bash
```

Then either:
- clone this repo directly in the guest, or
- share the repo folder into the guest, or
- run CaseTrace on the host against exported artifacts from the guest

## Recommended Integration Pattern
- Keep CaseTrace logic in this repo.
- Replace the fixture-backed tool handlers with real wrappers around SIFT commands.
- Preserve the same `ToolResult` and `EvidenceRecord` schemas so reporting does not need to change.

For the SSH-backed path, see [REMOTE_SIFT.md](./REMOTE_SIFT.md).
