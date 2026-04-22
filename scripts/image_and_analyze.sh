#!/bin/bash
# Image a Windows system and run CaseTrace analysis
# This script should run on a Linux system (like SIFT VM) that has access to:
# - The Windows disk (via USB, network, or VM export)
# - SIFT forensic tools (analyzemft, regripper.pl, etc.)
# - Network access to the CaseTrace tools

set -e

# Configuration
CASE_NAME="${1:-realistic-windows-case}"
IMAGE_PATH="${2:-cases/$CASE_NAME/disk.E01}"
DISK_SOURCE="${3:-/dev/sda}"  # Path to Windows disk or image source
VM_HOST="${4:-127.0.0.1}"
VM_PORT="${5:-2222}"
VM_USER="${6:-sift}"
REMOTE_WORKDIR="${7:-/home/sift/findevil}"

echo "=========================================="
echo "CaseTrace Demo: Forensic Imaging & Analysis"
echo "=========================================="
echo "Case Name: $CASE_NAME"
echo "Target Image: $IMAGE_PATH"
echo "Disk Source: $DISK_SOURCE"
echo "Remote Workdir: $REMOTE_WORKDIR"
echo ""

# Phase 1: Validate prerequisites
echo "[PHASE 1] Validating prerequisites..."
if ! command -v mmls &> /dev/null; then
    echo "ERROR: mmls not found. Install SIFT tools."
    exit 1
fi

if ! command -v analyzemft &> /dev/null; then
    echo "ERROR: analyzemft not found. Install SIFT tools."
    exit 1
fi

echo "✓ SIFT tools available"

# Phase 2: Create case directory
echo ""
echo "[PHASE 2] Creating case directory..."
mkdir -p "cases/$CASE_NAME/raw"
mkdir -p "$(dirname "$IMAGE_PATH")"
echo "✓ Created: cases/$CASE_NAME/"

# Phase 3: Handle image source
echo ""
echo "[PHASE 3] Preparing forensic image..."

if [ -f "$DISK_SOURCE" ]; then
    echo "✓ Found existing image at $DISK_SOURCE"
    if [ "$(realpath "$DISK_SOURCE")" != "$(realpath "$IMAGE_PATH" 2>/dev/null || echo "$IMAGE_PATH")" ]; then
        cp "$DISK_SOURCE" "$IMAGE_PATH"
    else
        echo "  Source image is already at target path"
    fi
elif [ -b "$DISK_SOURCE" ]; then
    echo "Creating forensic image from block device: $DISK_SOURCE"
    echo "  (This requires write access to $DISK_SOURCE)"
    if ! sudo ddrescue -D --force "$DISK_SOURCE" "$IMAGE_PATH"; then
        echo "✗ Failed to create image"
        exit 1
    fi
else
    echo "✗ Image source not found: $DISK_SOURCE"
    echo "  Create or convert a real Windows image and place it at: $IMAGE_PATH"
    echo "  For UTM qcow2 disks, convert to raw first, for example:"
    echo "  qemu-img convert -O raw Windows.qcow2 $IMAGE_PATH"
    exit 1
fi

echo "✓ Image available at: $IMAGE_PATH"
echo "  Size: $(du -h "$IMAGE_PATH" | cut -f1)"

# Phase 4: Create case manifest
echo ""
echo "[PHASE 4] Creating case manifest..."
cat > "cases/$CASE_NAME/manifest.json" << EOF
{
  "case_id": "$CASE_NAME",
  "analyst": "CaseTrace Demo",
  "created": "2026-04-22",
  "expected_artifacts": [
    "timeline_mft",
    "registry_autoruns",
    "scheduled_tasks",
    "prefetch_summary",
    "amcache_summary",
    "browser_history",
    "user_logons",
    "yara_scan"
  ],
  "notes": "Realistic Windows workstation with planted attack artifacts for accuracy validation"
}
EOF
echo "✓ Created: cases/$CASE_NAME/manifest.json"

# Phase 5: Validate image with forensic tools
echo ""
echo "[PHASE 5] Validating image structure..."

echo "  Running mmls..."
if mmls "$IMAGE_PATH" 2>/dev/null | head -5; then
    echo "  ✓ mmls succeeded"
else
    echo "  ⚠ mmls check inconclusive (image may be raw or non-standard)"
fi

echo "  Running fls..."
if fls "$IMAGE_PATH" 2>/dev/null | head -10; then
    echo "  ✓ fls succeeded directly"
else
    echo "  ⚠ direct fls check inconclusive; partitioned images may require offset detection in the SIFT bridge"
fi

# Phase 6: Create CaseTrace runner script
echo ""
echo "[PHASE 6] Creating CaseTrace runner script..."
cat > "cases/$CASE_NAME/run_analysis.sh" << EOF
#!/bin/bash
# Run CaseTrace analysis with remote SIFT backend

set -e

CASE_DIR="cases/$CASE_NAME"
IMAGE_PATH="$IMAGE_PATH"
VM_HOST="$VM_HOST"
VM_PORT="$VM_PORT"
VM_USER="$VM_USER"
REMOTE_WORKDIR="$REMOTE_WORKDIR"
IDENTITY_FILE="vm_assets/ssh/sift_vm_ed25519"

echo "Running CaseTrace analysis..."
echo "  Image: \$IMAGE_PATH"
echo "  Remote SIFT: \$VM_USER@\$VM_HOST:\$VM_PORT"
echo ""

python3 -m findevil analyze \\
    --case "$CASE_NAME" \\
    --disk "\$IMAGE_PATH" \\
    --profile windows \\
    --output "runs/$CASE_NAME" \\
    --tool-backend sift-ssh \\
    --remote-host "\$VM_HOST" \\
    --remote-port "\$VM_PORT" \\
    --remote-user "\$VM_USER" \\
    --remote-workdir "\$REMOTE_WORKDIR" \\
    --remote-identity-file "\$IDENTITY_FILE"

echo ""
echo "✓ Analysis complete"
echo "  Report: runs/$CASE_NAME/report.md"
echo "  Findings: runs/$CASE_NAME/findings.json"
EOF

chmod +x "cases/$CASE_NAME/run_analysis.sh"
echo "✓ Created: cases/$CASE_NAME/run_analysis.sh"

# Phase 7: Summary and next steps
echo ""
echo "=========================================="
echo "Image Preparation Complete!"
echo "=========================================="
echo ""
echo "Next Steps:"
echo "1. Verify image accessibility:"
echo "   mmls $IMAGE_PATH"
echo ""
echo "2. Run CaseTrace analysis:"
echo "   bash cases/$CASE_NAME/run_analysis.sh"
echo ""
echo "3. Validate findings:"
echo "   cat runs/$CASE_NAME/report.md"
echo "   cat runs/$CASE_NAME/findings.json | jq '.findings'"
echo ""
