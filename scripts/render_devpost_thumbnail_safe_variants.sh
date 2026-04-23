#!/bin/bash
# Render safer low-text Devpost thumbnail variants.

set -euo pipefail

OUT_DIR="${1:-demo}"
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

mkdir -p "$OUT_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

cat > "$TMP_DIR/min_term.txt" <<'EOF'
$ bash run_analysis.sh

status: completed
findings: 4
blocked: 1

confirmed | persistence
confirmed | web delivery
inference | script execution
EOF

cat > "$TMP_DIR/meta_term.txt" <<'EOF'
$ jq .summary run_metadata.json

status: completed
iterations: 2
confirmed_count: 2
inference_count: 2
issues_count: 1
EOF

render_minimal() {
    ffmpeg -y -hide_banner -loglevel error \
        -f lavfi -i "color=c=0x081018:s=${WIDTH}x${HEIGHT}" \
        -vf "\
drawtext=fontfile=${FONT}:text='CaseTrace':fontsize=132:fontcolor=0xf7fbff:x=92:y=168,\
drawtext=fontfile=${FONT}:text='DFIR agent for SIFT':fontsize=38:fontcolor=0xd6e2ea:x=98:y=244,\
drawbox=x=98:y=324:w=250:h=84:color=0x163145:t=fill,\
drawbox=x=98:y=324:w=250:h=84:color=0x57d1ff:t=3,\
drawtext=fontfile=${FONT}:text='10/10 tools':fontsize=38:fontcolor=0xf7fbff:x=132:y=358,\
drawbox=x=374:y=324:w=230:h=84:color=0x342313:t=fill,\
drawbox=x=374:y=324:w=230:h=84:color=0xffb86b:t=3,\
drawtext=fontfile=${FONT}:text='4 findings':fontsize=38:fontcolor=0xf7fbff:x=414:y=358,\
drawbox=x=630:y=324:w=250:h=84:color=0x182714:t=fill,\
drawbox=x=630:y=324:w=250:h=84:color=0x85d175:t=3,\
drawtext=fontfile=${FONT}:text='1 blocked':fontsize=38:fontcolor=0xf7fbff:x=670:y=358,\
drawbox=x=98:y=470:w=1304:h=380:color=0x111922@0.98:t=fill,\
drawbox=x=98:y=470:w=1304:h=380:color=0x2c3a47@0.95:t=3,\
drawbox=x=98:y=470:w=1304:h=46:color=0x1a2430:t=fill,\
drawbox=x=122:y=488:w=12:h=12:color=0xff6b6b:t=fill,\
drawbox=x=144:y=488:w=12:h=12:color=0xffd166:t=fill,\
drawbox=x=166:y=488:w=12:h=12:color=0x82d173:t=fill,\
drawtext=fontfile=${MONO_FONT}:text='realistic-windows-image':fontsize=20:fontcolor=0xa5b7c6:x=212:y=486,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/min_term.txt:fontsize=31:fontcolor=0xe8eef5:x=140:y=568:line_spacing=14,\
drawtext=fontfile=${FONT}:text='Generated 128 MB NTFS image':fontsize=32:fontcolor=0xa8d5ff:x=100:y=930,\
drawtext=fontfile=${FONT}:text='github.com/JafarBanar/findevil':fontsize=24:fontcolor=0x7f96a6:x=1000:y=930" \
        -frames:v 1 -q:v 2 "$OUT_DIR/devpost_safe_1.jpg"
}

render_balanced() {
    ffmpeg -y -hide_banner -loglevel error \
        -f lavfi -i "color=c=0x09111a:s=${WIDTH}x${HEIGHT}" \
        -vf "\
drawtext=fontfile=${FONT}:text='CaseTrace':fontsize=114:fontcolor=0xf7fbff:x=90:y=160,\
drawtext=fontfile=${FONT}:text='read-only self-correcting DFIR':fontsize=34:fontcolor=0xd6e2ea:x=98:y=232,\
drawtext=fontfile=${FONT}:text='Evidence-linked findings':fontsize=30:fontcolor=0xa8d5ff:x=100:y=288,\
drawbox=x=98:y=360:w=540:h=260:color=0x0d151d@0.96:t=fill,\
drawbox=x=98:y=360:w=540:h=260:color=0x243442@0.95:t=3,\
drawtext=fontfile=${FONT}:text='Generated NTFS image':fontsize=44:fontcolor=0xf7fbff:x=132:y=430,\
drawtext=fontfile=${FONT}:text='Remote SIFT backend':fontsize=36:fontcolor=0xd6e2ea:x=132:y=494,\
drawtext=fontfile=${FONT}:text='4 findings  •  1 blocked claim':fontsize=32:fontcolor=0xffc98f:x=132:y=556,\
drawbox=x=720:y=120:w=680:h=760:color=0x111922@0.98:t=fill,\
drawbox=x=720:y=120:w=680:h=760:color=0x2c3a47@0.95:t=3,\
drawbox=x=720:y=120:w=680:h=46:color=0x1a2430:t=fill,\
drawbox=x=744:y=138:w=12:h=12:color=0xff6b6b:t=fill,\
drawbox=x=766:y=138:w=12:h=12:color=0xffd166:t=fill,\
drawbox=x=788:y=138:w=12:h=12:color=0x82d173:t=fill,\
drawtext=fontfile=${MONO_FONT}:text='run_metadata.json':fontsize=20:fontcolor=0xa5b7c6:x=834:y=136,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/meta_term.txt:fontsize=30:fontcolor=0xe8eef5:x=762:y=226:line_spacing=16,\
drawbox=x=98:y=700:w=220:h=82:color=0x163145:t=fill,\
drawbox=x=98:y=700:w=220:h=82:color=0x57d1ff:t=3,\
drawtext=fontfile=${FONT}:text='10/10 tools':fontsize=34:fontcolor=0xf7fbff:x=132:y=732,\
drawbox=x=344:y=700:w=220:h=82:color=0x342313:t=fill,\
drawbox=x=344:y=700:w=220:h=82:color=0xffb86b:t=3,\
drawtext=fontfile=${FONT}:text='2 confirmed':fontsize=34:fontcolor=0xf7fbff:x=374:y=732,\
drawtext=fontfile=${FONT}:text='github.com/JafarBanar/findevil':fontsize=24:fontcolor=0x7f96a6:x=100:y=920" \
        -frames:v 1 -q:v 2 "$OUT_DIR/devpost_safe_2.jpg"
}

render_ultra_simple() {
    ffmpeg -y -hide_banner -loglevel error \
        -f lavfi -i "color=c=0x081018:s=${WIDTH}x${HEIGHT}" \
        -vf "\
drawbox=x=0:y=0:w=${WIDTH}:h=1000:color=0x081018:t=fill,\
drawtext=fontfile=${FONT}:text='CaseTrace':fontsize=140:fontcolor=0xf7fbff:x=92:y=190,\
drawtext=fontfile=${FONT}:text='Evidence-linked DFIR agent for SIFT':fontsize=40:fontcolor=0xd6e2ea:x=100:y=270,\
drawbox=x=100:y=360:w=1300:h=470:color=0x111922@0.98:t=fill,\
drawbox=x=100:y=360:w=1300:h=470:color=0x2c3a47@0.95:t=3,\
drawbox=x=100:y=360:w=1300:h=46:color=0x1a2430:t=fill,\
drawbox=x=124:y=378:w=12:h=12:color=0xff6b6b:t=fill,\
drawbox=x=146:y=378:w=12:h=12:color=0xffd166:t=fill,\
drawbox=x=168:y=378:w=12:h=12:color=0x82d173:t=fill,\
drawtext=fontfile=${MONO_FONT}:text='casetrace run':fontsize=20:fontcolor=0xa5b7c6:x=214:y=376,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/min_term.txt:fontsize=33:fontcolor=0xe8eef5:x=144:y=470:line_spacing=16,\
drawtext=fontfile=${FONT}:text='10/10 tools  •  4 findings  •  1 blocked claim':fontsize=34:fontcolor=0xa8d5ff:x=100:y=930" \
        -frames:v 1 -q:v 2 "$OUT_DIR/devpost_safe_3.jpg"
}

render_minimal
render_balanced
render_ultra_simple

echo "Created:"
echo "  $OUT_DIR/devpost_safe_1.jpg"
echo "  $OUT_DIR/devpost_safe_2.jpg"
echo "  $OUT_DIR/devpost_safe_3.jpg"
