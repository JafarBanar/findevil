#!/bin/bash
# Create a raw NTFS forensic image from the controlled Windows-like artifact tree.
#
# This is the no-Windows demo path: it produces a real NTFS image that SIFT
# tools can enumerate, while preserving the known artifact ground truth.

set -euo pipefail

SOURCE_TREE="${1:-cases/realistic-windows-case/disk_root}"
IMAGE_PATH="${2:-cases/realistic-windows-image/disk.img}"
IMAGE_SIZE_MB="${3:-128}"
LABEL="${4:-CASETRACE}"

echo "=========================================="
echo "CaseTrace NTFS Image Builder"
echo "=========================================="
echo "Source tree: $SOURCE_TREE"
echo "Image path:  $IMAGE_PATH"
echo "Size:        ${IMAGE_SIZE_MB} MB"
echo ""

for tool in dd mkfs.ntfs sudo mount umount fls; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool not found: $tool"
        exit 1
    fi
done

if [ ! -d "$SOURCE_TREE" ]; then
    echo "ERROR: source artifact tree not found: $SOURCE_TREE"
    exit 1
fi

if [ -e "$IMAGE_PATH" ] && [ "${OVERWRITE:-0}" != "1" ]; then
    echo "ERROR: image already exists: $IMAGE_PATH"
    echo "Set OVERWRITE=1 to rebuild it."
    exit 1
fi

if ! sudo -n true >/dev/null 2>&1; then
    echo "ERROR: passwordless sudo is required to loop-mount the NTFS image."
    exit 1
fi

mkdir -p "$(dirname "$IMAGE_PATH")"
MOUNT_DIR="$(mktemp -d)"

cleanup() {
    if mountpoint -q "$MOUNT_DIR" 2>/dev/null; then
        sudo umount "$MOUNT_DIR" >/dev/null 2>&1 || true
    fi
    rmdir "$MOUNT_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/5] Allocating raw image..."
dd if=/dev/zero of="$IMAGE_PATH" bs=1M count="$IMAGE_SIZE_MB" status=none

echo "[2/5] Formatting NTFS..."
mkfs.ntfs -F -Q -L "$LABEL" "$IMAGE_PATH" >/dev/null

echo "[3/5] Mounting image..."
sudo mount -o loop,rw "$IMAGE_PATH" "$MOUNT_DIR"

echo "[4/5] Copying artifacts into NTFS..."
sudo cp -a "$SOURCE_TREE"/. "$MOUNT_DIR"/
sync

echo "[5/5] Unmounting and validating with fls..."
sudo umount "$MOUNT_DIR"
sudo chown "$(id -u):$(id -g)" "$IMAGE_PATH"
fls "$IMAGE_PATH" >/dev/null

echo ""
echo "Created NTFS image: $IMAGE_PATH"
echo "Image size: $(du -h "$IMAGE_PATH" | awk '{print $1}')"
echo "Top-level entries:"
fls "$IMAGE_PATH" | sed -n '1,12p'
