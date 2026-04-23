#!/bin/bash
# Render a clean Devpost thumbnail that looks like a terminal screenshot.

set -euo pipefail

OUT="${1:-demo/devpost_terminal_thumbnail.jpg}"
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
$ bash cases/realistic-windows-image/run_analysis.sh

{
  "case_id": "realistic-windows-image",
  "status": "completed",
  "iterations": 2,
  "findings": 4,
  "issues": 1
}

# CaseTrace report summary
- confirmed: persistence established
- confirmed: suspicious web delivery
- inference: script execution observed
- blocked: unsupported credential-theft claim
EOF

ffmpeg -y -hide_banner -loglevel error \
    -f lavfi -i "color=c=0x091018:s=${WIDTH}x${HEIGHT}" \
    -vf "\
drawtext=fontfile=${FONT}:text='CaseTrace':fontsize=64:fontcolor=0xf7fbff:x=92:y=86,\
drawtext=fontfile=${FONT}:text='Read-only DFIR agent for SIFT':fontsize=24:fontcolor=0xa9bfd0:x=95:y=126,\
drawbox=x=72:y=170:w=1356:h=730:color=0x111922@0.98:t=fill,\
drawbox=x=72:y=170:w=1356:h=730:color=0x2c3a47@0.95:t=3,\
drawbox=x=72:y=170:w=1356:h=48:color=0x1a2430:t=fill,\
drawbox=x=96:y=188:w=12:h=12:color=0xff6b6b:t=fill,\
drawbox=x=118:y=188:w=12:h=12:color=0xffd166:t=fill,\
drawbox=x=140:y=188:w=12:h=12:color=0x82d173:t=fill,\
drawtext=fontfile=${MONO_FONT}:text='casetrace terminal run':fontsize=20:fontcolor=0xa5b7c6:x=186:y=184,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/terminal.txt:fontsize=25:fontcolor=0xe8eef5:x=108:y=266:line_spacing=12,\
drawtext=fontfile=${FONT}:text='10/10 tools  •  4 findings  •  1 blocked claim':fontsize=28:fontcolor=0x93d7ff:x=84:y=948,\
drawtext=fontfile=${FONT}:text='github.com/JafarBanar/findevil':fontsize=22:fontcolor=0x7f96a6:x=1048:y=948" \
    -frames:v 1 -q:v 2 "$OUT"

echo "Created thumbnail: $OUT"
