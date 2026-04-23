#!/bin/bash
# Render one clean, low-text Devpost thumbnail with no crowded overlays.

set -euo pipefail

OUT="${1:-demo/devpost_thumbnail_clean.jpg}"
FONT="${FONT:-/System/Library/Fonts/Supplemental/Arial.ttf}"
MONO_FONT="${MONO_FONT:-/System/Library/Fonts/Menlo.ttc}"
WIDTH=1500
HEIGHT=1000

for tool in ffmpeg; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "ERROR: required tool not found: $tool"
        exit 1
    fi
done

for file in "$FONT" "$MONO_FONT"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: font not found: $file"
        exit 1
    fi
done

mkdir -p "$(dirname "$OUT")"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cat > "$TMP_DIR/terminal.txt" <<'EOF'
$ bash run_analysis.sh

status: completed
iterations: 2
findings: 4
blocked claims: 1

confirmed | persistence
confirmed | web delivery
inference | script execution
EOF

ffmpeg -y -hide_banner -loglevel error \
    -f lavfi -i "color=c=0x081018:s=${WIDTH}x${HEIGHT}" \
    -vf "\
drawtext=fontfile=${FONT}:text='CaseTrace':fontsize=98:fontcolor=0xf7fbff:x=92:y=156,\
drawtext=fontfile=${FONT}:text='Read-only DFIR agent for SIFT':fontsize=30:fontcolor=0xd6e2ea:x=100:y=246,\
drawbox=x=1120:y=92:w=220:h=64:color=0x163145:t=fill,\
drawbox=x=1120:y=92:w=220:h=64:color=0x57d1ff:t=3,\
drawtext=fontfile=${FONT}:text='10/10 tools':fontsize=30:fontcolor=0xf7fbff:x=1162:y=116,\
drawbox=x=90:y=290:w=1320:h=610:color=0x111922@0.98:t=fill,\
drawbox=x=90:y=290:w=1320:h=610:color=0x2c3a47@0.95:t=3,\
drawbox=x=90:y=290:w=1320:h=46:color=0x1a2430:t=fill,\
drawbox=x=116:y=308:w=12:h=12:color=0xff6b6b:t=fill,\
drawbox=x=138:y=308:w=12:h=12:color=0xffd166:t=fill,\
drawbox=x=160:y=308:w=12:h=12:color=0x82d173:t=fill,\
drawtext=fontfile=${MONO_FONT}:text='realistic-windows-image':fontsize=20:fontcolor=0xa5b7c6:x=206:y=306,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/terminal.txt:fontsize=28:fontcolor=0xe8eef5:x=140:y=380:line_spacing=14,\
drawtext=fontfile=${FONT}:text='Generated NTFS image  •  Evidence-linked findings':fontsize=30:fontcolor=0xa8d5ff:x=92:y=940" \
    -frames:v 1 -q:v 2 "$OUT"

echo "Created clean thumbnail: $OUT"
