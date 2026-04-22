#!/bin/bash
# Print the strongest artifacts to show in the demo recording.

set -euo pipefail

RUN_DIR="${1:-runs/realistic-windows-image}"

if [ ! -d "$RUN_DIR" ]; then
    echo "ERROR: run directory not found: $RUN_DIR"
    echo "Run: bash cases/realistic-windows-image/run_analysis.sh"
    exit 1
fi

echo "== Run Summary =="
jq '.summary' "$RUN_DIR/run_metadata.json"

echo ""
echo "== Findings =="
jq -r '.[] | "- \(.status) | \(.severity) | \(.title) | evidence=\(.evidence_ids | join(","))"' \
    "$RUN_DIR/findings.json"

echo ""
echo "== Typed Tool Calls =="
jq -r '[.iteration, .tool_name, .success, (.evidence_ids | length), .raw_artifact_path] | @tsv' \
    "$RUN_DIR/tool_calls.jsonl"

echo ""
echo "== Verification Issues =="
jq -r '.issues[] | "- \(.issue_type) | blocked=\(.blocked) | \(.summary)"' \
    "$RUN_DIR/run_metadata.json"
