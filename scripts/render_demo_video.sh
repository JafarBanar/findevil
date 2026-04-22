#!/bin/bash
# Render a short text-slide demo video from the validated NTFS image run.

set -euo pipefail

RUN_DIR="${RUN_DIR:-runs/realistic-windows-image}"
OUT="${1:-demo/casetrace_demo.mp4}"
FONT="${FONT:-/System/Library/Fonts/Supplemental/Arial.ttf}"
SLIDE_SECONDS="${SLIDE_SECONDS:-11}"

for tool in ffmpeg ffprobe jq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool not found: $tool"
        exit 1
    fi
done

if [ ! -d "$RUN_DIR" ]; then
    echo "ERROR: run directory not found: $RUN_DIR"
    echo "Run: bash cases/realistic-windows-image/run_analysis.sh"
    exit 1
fi

if [ ! -f "$FONT" ]; then
    echo "ERROR: font not found: $FONT"
    exit 1
fi

mkdir -p "$(dirname "$OUT")"
TMP_DIR="$(mktemp -d)"
cleanup() {
    local status=$?
    if [ "$status" -eq 0 ]; then
        rm -rf "$TMP_DIR"
    else
        echo "Render failed; temp files kept at: $TMP_DIR" >&2
    fi
}
trap cleanup EXIT

summary="$(jq -r '.summary | "Status: \(.status)\nIterations: \(.iterations)\nFindings: \(.findings_count) total, \(.confirmed_count) confirmed, \(.inference_count) inference\nIssues: \(.issues_count) blocked or pending\nOutput: \(.output_path)"' "$RUN_DIR/run_metadata.json")"
tools="$(jq -r '.tool_results[] | "\(.tool_name): success=\(.success), evidence=\(.evidence_ids | length), errors=\(.errors | length)"' "$RUN_DIR/run_metadata.json")"
findings="$(jq -r '.[] | "\(.status) | \(.severity) | \(.title)\n  evidence: \(.evidence_ids | join(", "))"' "$RUN_DIR/findings.json")"
issues="$(jq -r '.issues[] | "\(.issue_type): blocked=\(.blocked)\n\(.summary)"' "$RUN_DIR/run_metadata.json")"

render_slide() {
    local index="$1"
    local title="$2"
    local body="$3"
    local slide_file="$TMP_DIR/slide_${index}.txt"
    local segment_file="$TMP_DIR/segment_${index}.mp4"
    local body_text="${body//\\n/$'\n'}"

    {
        printf '%s\n' "$title"
        printf '%s\n\n' "$(printf '%0.s=' $(seq 1 ${#title}))"
        printf '%s\n' "$body_text"
    } > "$slide_file"

    ffmpeg -y -hide_banner -loglevel error \
        -f lavfi -i "color=c=0x08111f:s=1920x1080:d=${SLIDE_SECONDS}:r=30" \
        -vf "drawtext=fontfile=${FONT}:textfile=${slide_file}:fontsize=42:fontcolor=white:x=90:y=80:line_spacing=18,drawtext=fontfile=${FONT}:text='CaseTrace no-Windows NTFS demo':fontsize=28:fontcolor=0x9fb7ff:x=90:y=1010" \
        -c:v libx264 -pix_fmt yuv420p -movflags +faststart "$segment_file"

    printf "file '%s'\n" "$segment_file" >> "$TMP_DIR/concat.txt"
}

render_slide 1 \
    "Problem and Guardrails" \
    "AI-assisted attackers can move faster than manual IR.\n\nCaseTrace responds with a bounded, read-only DFIR agent.\n\nEvery final claim must cite evidence IDs.\nThe agent does not get a generic shell.\nThe SIFT backend exposes fixed typed tools only." \
    "AI-assisted attackers can move faster than manual incident response. CaseTrace is a read-only DFIR agent with a bounded loop, typed tools, and evidence IDs for every final claim."

render_slide 2 \
    "Architecture" \
    "Case request -> bounded orchestrator -> typed tool planner\n\nTyped tools -> SIFT SSH bridge -> evidence store\n\nSynthesizer -> verifier -> confirmed, inference, or blocked\n\nSelf-correction only runs when more evidence is needed." \
    "The architecture keeps model reasoning behind a typed forensic tool surface. The remote bridge calls fixed SIFT collection tools, stores raw artifacts, and sends findings through verification."

render_slide 3 \
    "No-Windows Image Setup" \
    "No Windows host was available.\n\nSIFT generated a real raw NTFS filesystem image:\n  cases/realistic-windows-image/disk.img\n\nSize: 128 MB\nSHA-256: 4e006be48a4db5d6b10b7ec6336e5c7254fb3c3ae3ecf170c04a53ec66088eb2\n\nBuilder:\n  scripts/create_ntfs_image_from_artifact_tree.sh" \
    "Because no Windows host was available, the demo creates a real raw NTFS image on SIFT from controlled artifacts. It is image-backed and reproducible, but not a native Windows install."

render_slide 4 \
    "Validated Run Summary" \
    "$summary" \
    "The validated run completed in two iterations with four findings, two confirmed findings, two inference findings, and one blocked unsupported claim."

render_slide 5 \
    "Typed Tool Coverage" \
    "$tools" \
    "All ten typed tools succeeded. The run includes browser history, prefetch, Amcache, MFT timeline, YARA scanning, registry autoruns, scheduled tasks, user logons, case info, and read-only mount access."

render_slide 6 \
    "Findings and Evidence" \
    "$findings" \
    "The final report retained four evidence-linked findings: suspicious script execution, likely web delivery, persistence, and a detection hit. Each finding cites concrete evidence IDs."

render_slide 7 \
    "Self-Correction and Blocked Claim" \
    "$issues\n\nIteration 1 had weak or unsupported claims.\nIteration 2 gathered corroborating evidence.\nCredential theft stayed blocked because no credential-access evidence exists." \
    "Self-correction gathered corroborating evidence in the second iteration, while credential theft speculation remained blocked because the evidence did not support it."

render_slide 8 \
    "Result and Limitation" \
    "Result:\n  10/10 tools succeeded\n  8/8 expected artifact categories produced evidence\n  4 retained findings\n  1 unsupported claim blocked\n  0 tool failures\n\nLimitation:\n  This is a generated NTFS image, not a native Windows OS image.\n  Public or native-image validation is the next accuracy step." \
    "The result is a clean, reproducible, image-backed demo. It proves the no-Windows workflow and keeps the limitation honest: broader accuracy needs a native or public Windows image."

ffmpeg -y -hide_banner -loglevel error \
    -f concat -safe 0 -i "$TMP_DIR/concat.txt" \
    -c copy "$OUT"

echo "Created demo video: $OUT"
ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
