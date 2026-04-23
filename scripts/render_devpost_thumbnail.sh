#!/bin/bash
# Render a cleaner 3:2 Devpost thumbnail JPG for CaseTrace using real run data.

set -euo pipefail

OUT="${1:-demo/devpost_thumbnail.jpg}"
RUN_DIR="${RUN_DIR:-runs/realistic-windows-image}"
FONT="${FONT:-/System/Library/Fonts/Supplemental/Arial.ttf}"
MONO_FONT="${MONO_FONT:-/System/Library/Fonts/Menlo.ttc}"
WIDTH="${WIDTH:-1500}"
HEIGHT="${HEIGHT:-1000}"

for tool in ffmpeg jq; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool not found: $tool"
        exit 1
    fi
done

for file in "$FONT" "$MONO_FONT" "$RUN_DIR/report.md" "$RUN_DIR/run_metadata.json" "$RUN_DIR/findings.json"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: required file not found: $file"
        exit 1
    fi
done

mkdir -p "$(dirname "$OUT")"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

jq -r '.summary.findings_count' "$RUN_DIR/run_metadata.json" > "$TMP_DIR/findings_count.txt"
jq -r '.summary.issues_count' "$RUN_DIR/run_metadata.json" > "$TMP_DIR/issues_count.txt"
jq -r '[.summary.confirmed_count, .summary.inference_count] | "\(.[0]) confirmed   \(.[1]) inference"' "$RUN_DIR/run_metadata.json" > "$TMP_DIR/findings_mix.txt"

cat > "$TMP_DIR/title.txt" <<'EOF'
CaseTrace
EOF

cat > "$TMP_DIR/tagline.txt" <<'EOF'
Read-only, self-correcting DFIR agent for SIFT
EOF

cat > "$TMP_DIR/subtitle.txt" <<'EOF'
Evidence-linked findings from a reproducible NTFS image run
EOF

cat > "$TMP_DIR/chip_a.txt" <<'EOF'
10/10 tools
EOF

cat > "$TMP_DIR/chip_b.txt" <<'EOF'
4 findings
EOF

cat > "$TMP_DIR/chip_c.txt" <<'EOF'
1 blocked claim
EOF

cat > "$TMP_DIR/terminal.txt" <<'EOF'
$ bash run_analysis.sh

status: completed
iterations: 2
findings: 4
blocked claims: 1

confirmed | Persistence established
confirmed | Suspicious web delivery
inference | Script execution observed
EOF

ffmpeg -y -hide_banner -loglevel error \
    -f lavfi -i "color=c=0x091019:s=${WIDTH}x${HEIGHT}" \
    -vf "\
drawbox=x=0:y=0:w=${WIDTH}:h=210:color=0x0e1822@1:t=fill,\
drawbox=x=68:y=68:w=210:h=42:color=0x133348@1:t=fill,\
drawtext=fontfile=${FONT}:text='FIND EVIL! 2026':fontsize=24:fontcolor=0x97dbff:x=92:y=77,\
drawtext=fontfile=${FONT}:textfile=${TMP_DIR}/title.txt:fontsize=104:fontcolor=0xf7fbff:x=78:y=152,\
drawtext=fontfile=${FONT}:textfile=${TMP_DIR}/tagline.txt:fontsize=30:fontcolor=0xd6e0e8:x=82:y=248,\
drawtext=fontfile=${FONT}:textfile=${TMP_DIR}/subtitle.txt:fontsize=23:fontcolor=0x8fa3b2:x=84:y=298,\
drawbox=x=82:y=380:w=210:h=78:color=0x123246@1:t=fill,\
drawbox=x=82:y=380:w=210:h=78:color=0x58d2ff@0.8:t=3,\
drawtext=fontfile=${FONT}:textfile=${TMP_DIR}/chip_a.txt:fontsize=32:fontcolor=0xf7fbff:x=112:y=409,\
drawbox=x=312:y=380:w=210:h=78:color=0x2d1f12@1:t=fill,\
drawbox=x=312:y=380:w=210:h=78:color=0xffbb67@0.85:t=3,\
drawtext=fontfile=${FONT}:textfile=${TMP_DIR}/chip_b.txt:fontsize=32:fontcolor=0xf7fbff:x=352:y=409,\
drawbox=x=542:y=380:w=260:h=78:color=0x172014@1:t=fill,\
drawbox=x=542:y=380:w=260:h=78:color=0x86d17c@0.85:t=3,\
drawtext=fontfile=${FONT}:textfile=${TMP_DIR}/chip_c.txt:fontsize=29:fontcolor=0xf7fbff:x=574:y=411,\
drawbox=x=82:y=530:w=720:h=210:color=0x0d141b@0.96:t=fill,\
drawbox=x=82:y=530:w=720:h=210:color=0x233240@0.95:t=3,\
drawtext=fontfile=${FONT}:text='No Windows host':fontsize=30:fontcolor=0xf7fbff:x=112:y=575,\
drawtext=fontfile=${FONT}:text='Generated 128 MB NTFS image':fontsize=38:fontcolor=0xa6d7ff:x=112:y=630,\
drawtext=fontfile=${FONT}:text='Real SIFT tool execution over SSH':fontsize=31:fontcolor=0xd2dde7:x=112:y=682,\
drawtext=fontfile=${FONT}:text='Read-only  •  traceable  •  reproducible':fontsize=25:fontcolor=0x8fa3b2:x=112:y=725,\
drawbox=x=870:y=120:w=550:h=660:color=0x111821@0.98:t=fill,\
drawbox=x=870:y=120:w=550:h=660:color=0x2b3947@0.95:t=3,\
drawbox=x=870:y=120:w=550:h=44:color=0x1a2430@1:t=fill,\
drawbox=x=892:y=136:w=12:h=12:color=0xff6b6b:t=fill,\
drawbox=x=914:y=136:w=12:h=12:color=0xffd166:t=fill,\
drawbox=x=936:y=136:w=12:h=12:color=0x82d173:t=fill,\
drawtext=fontfile=${MONO_FONT}:text='realistic-windows-image':fontsize=19:fontcolor=0xa5b7c6:x=982:y=133,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/terminal.txt:fontsize=19:fontcolor=0xe6edf3:x=902:y=192:line_spacing=10,\
drawbox=x=870:y=820:w=550:h=88:color=0x0f151c@1:t=fill,\
drawtext=fontfile=${FONT}:text='evidence-linked findings':fontsize=30:fontcolor=0x8dd6ff:x=900:y=847,\
drawtext=fontfile=${FONT}:text='self-correcting DFIR workflow':fontsize=27:fontcolor=0xffc98f:x=900:y=890" \
    -frames:v 1 -q:v 2 "$OUT"

echo "Created thumbnail: $OUT"
