# Generated NTFS Image Validation

This validation covers the no-Windows demo path. The image is a real raw NTFS filesystem generated on the SIFT VM from the controlled artifact tree, then analyzed through the `sift-ssh` backend.

Important scope note: this is an image-backed forensic workflow, not a native Windows OS install. It proves CaseTrace can enumerate a raw NTFS image with SIFT tools and preserve evidence traceability when Windows is unavailable.

## Image

- Case: `cases/realistic-windows-image`
- Image: `cases/realistic-windows-image/disk.img`
- Format: raw NTFS filesystem image
- Size: 128 MB
- SHA-256: `4e006be48a4db5d6b10b7ec6336e5c7254fb3c3ae3ecf170c04a53ec66088eb2`
- Builder: `scripts/create_ntfs_image_from_artifact_tree.sh`
- Source artifacts: `cases/realistic-windows-case/disk_root`

## Run

- Backend: `sift-ssh`
- Remote disk path: `/home/sift/findevil/cases/realistic-windows-image/disk.img`
- Run output: `runs/realistic-windows-image`
- Status: completed
- Iterations: 2

## Tool Coverage

| Tool | Result | Evidence Count |
| --- | --- | ---: |
| `case_info` | Success | 1 |
| `mount_image_readonly` | Success | 1 |
| `user_logons` | Success | 1 |
| `browser_history` | Success | 3 |
| `prefetch_summary` | Success | 1 |
| `amcache_summary` | Success | 1 |
| `timeline_mft` | Success | 19 |
| `yara_scan` | Success | 4 |
| `registry_autoruns` | Success | 1 |
| `scheduled_tasks` | Success | 1 |

## Findings

- `Suspicious script execution observed on the endpoint`: inference, backed by `amcache_summary` and `prefetch_summary`
- `Likely web delivery of a suspicious payload`: confirmed, backed by `browser_history` and `timeline_mft`
- `Persistence mechanism likely established on the host`: confirmed, backed by `registry_autoruns` and `scheduled_tasks`
- `Known suspicious artifact matched detection rules`: inference, backed by `yara_scan`

## Validation Result

- Tool failures: 0
- Successful typed tools: 10 / 10
- Expected artifact categories with evidence: 8 / 8
- Findings retained: 4
- Confirmed findings: 2
- Inference findings: 2
- Unsupported speculative credential-theft claim: blocked

## Reproduction

From the project root, with the SIFT VM available on `127.0.0.1:2222`:

```bash
rsync -a -e "ssh -p 2222 -i vm_assets/ssh/sift_vm_ed25519" \
  scripts/create_ntfs_image_from_artifact_tree.sh \
  sift@127.0.0.1:/home/sift/findevil/scripts/

rsync -a -e "ssh -p 2222 -i vm_assets/ssh/sift_vm_ed25519" \
  cases/realistic-windows-case/ \
  sift@127.0.0.1:/home/sift/findevil/cases/realistic-windows-case/

ssh -p 2222 -i vm_assets/ssh/sift_vm_ed25519 sift@127.0.0.1 \
  'cd /home/sift/findevil && OVERWRITE=1 bash scripts/create_ntfs_image_from_artifact_tree.sh'

rsync -a -e "ssh -p 2222 -i vm_assets/ssh/sift_vm_ed25519" \
  sift@127.0.0.1:/home/sift/findevil/cases/realistic-windows-image/disk.img \
  cases/realistic-windows-image/disk.img

bash cases/realistic-windows-image/run_analysis.sh
```
