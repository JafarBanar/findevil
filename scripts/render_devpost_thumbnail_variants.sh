#!/bin/bash
# Render several simple Devpost thumbnail options with safer text layout.

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

cat > "$TMP_DIR/terminal_a.txt" <<'EOF'
$ bash run_analysis.sh

status: completed
findings: 4
blocked claims: 1

confirmed | persistence
confirmed | web delivery
inference | script execution
EOF

cat > "$TMP_DIR/terminal_b.txt" <<'EOF'
$ jq .summary run_metadata.json

case_id: realistic-windows-image
status: completed
iterations: 2
confirmed_count: 2
inference_count: 2
issues_count: 1
EOF

cat > "$TMP_DIR/terminal_c.txt" <<'EOF'
evidence_ids:
- browser-history-2-f95dcbb8fc
- registry-autoruns-1-08277f2bae
- scheduled-tasks-1-b87ae3fe10

blocked:
unsupported credential-theft claim
EOF

render_option_a() {
    ffmpeg -y -hide_banner -loglevel error \
        -f lavfi -i "color=c=0x08111b:s=${WIDTH}x${HEIGHT}" \
        -vf "\
drawbox=x=0:y=0:w=${WIDTH}:h=220:color=0x0d1823@1:t=fill,\
drawtext=fontfile=${FONT}:text='CaseTrace':fontsize=118:fontcolor=0xf6fbff:x=86:y=158,\
drawtext=fontfile=${FONT}:text='Read-only DFIR agent for SIFT':fontsize=38:fontcolor=0xd6e2ea:x=92:y=246,\
drawbox=x=92:y=332:w=250:h=88:color=0x163145:t=fill,\
drawbox=x=92:y=332:w=250:h=88:color=0x57d1ff:t=3,\
drawtext=fontfile=${FONT}:text='10/10 tools':fontsize=40:fontcolor=0xf6fbff:x=130:y=368,\
drawbox=x=370:y=332:w=250:h=88:color=0x342313:t=fill,\
drawbox=x=370:y=332:w=250:h=88:color=0xffb86b:t=3,\
drawtext=fontfile=${FONT}:text='4 findings':fontsize=40:fontcolor=0xf6fbff:x=412:y=368,\
drawbox=x=648:y=332:w=310:h=88:color=0x182714:t=fill,\
drawbox=x=648:y=332:w=310:h=88:color=0x85d175:t=3,\
drawtext=fontfile=${FONT}:text='1 blocked claim':fontsize=37:fontcolor=0xf6fbff:x=686:y=368,\
drawbox=x=92:y=490:w=560:h=260:color=0x0d151d@0.97:t=fill,\
drawbox=x=92:y=490:w=560:h=260:color=0x243442@0.95:t=3,\
drawtext=fontfile=${FONT}:text='Generated 128 MB NTFS image':fontsize=46:fontcolor=0xa8d5ff:x=124:y=560,\
drawtext=fontfile=${FONT}:text='Real SIFT execution over SSH':fontsize=36:fontcolor=0xd6e2ea:x=124:y=630,\
drawtext=fontfile=${FONT}:text='Traceable findings with evidence IDs':fontsize=32:fontcolor=0x91a7b8:x=124:y=690,\
drawbox=x=820:y=120:w=590:h=720:color=0x111922@0.98:t=fill,\
drawbox=x=820:y=120:w=590:h=720:color=0x2c3a47@0.95:t=3,\
drawbox=x=820:y=120:w=590:h=46:color=0x1a2430:t=fill,\
drawbox=x=842:y=138:w=12:h=12:color=0xff6b6b:t=fill,\
drawbox=x=864:y=138:w=12:h=12:color=0xffd166:t=fill,\
drawbox=x=886:y=138:w=12:h=12:color=0x82d173:t=fill,\
drawtext=fontfile=${MONO_FONT}:text='run_analysis.sh':fontsize=20:fontcolor=0xa5b7c6:x=930:y=136,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/terminal_a.txt:fontsize=24:fontcolor=0xe8eef5:x=856:y=210:line_spacing=12,\
drawtext=fontfile=${FONT}:text='github.com/JafarBanar/findevil':fontsize=24:fontcolor=0x7f96a6:x=96:y=912" \
        -frames:v 1 -q:v 2 "$OUT_DIR/devpost_option_a.jpg"
}

render_option_b() {
    ffmpeg -y -hide_banner -loglevel error \
        -f lavfi -i "color=c=0x0a1118:s=${WIDTH}x${HEIGHT}" \
        -vf "\
drawbox=x=70:y=80:w=1360:h=840:color=0x121b24@0.98:t=fill,\
drawbox=x=70:y=80:w=1360:h=840:color=0x263543@0.95:t=3,\
drawbox=x=70:y=80:w=1360:h=56:color=0x1a2430:t=fill,\
drawbox=x=96:y=102:w=13:h=13:color=0xff6b6b:t=fill,\
drawbox=x=121:y=102:w=13:h=13:color=0xffd166:t=fill,\
drawbox=x=146:y=102:w=13:h=13:color=0x82d173:t=fill,\
drawtext=fontfile=${MONO_FONT}:text='casetrace-demo':fontsize=22:fontcolor=0xa5b7c6:x=190:y=98,\
drawtext=fontfile=${FONT}:text='CaseTrace':fontsize=94:fontcolor=0xf6fbff:x=112:y=220,\
drawtext=fontfile=${FONT}:text='evidence-linked self-correcting DFIR workflow':fontsize=34:fontcolor=0xd7e1e9:x=116:y=282,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/terminal_b.txt:fontsize=29:fontcolor=0xe8eef5:x=116:y=380:line_spacing=16,\
drawbox=x=880:y=196:w=420:h=108:color=0x163145:t=fill,\
drawbox=x=880:y=196:w=420:h=108:color=0x57d1ff:t=3,\
drawtext=fontfile=${FONT}:text='10/10 tools succeeded':fontsize=39:fontcolor=0xf6fbff:x=920:y=240,\
drawbox=x=880:y=346:w=420:h=108:color=0x342313:t=fill,\
drawbox=x=880:y=346:w=420:h=108:color=0xffb86b:t=3,\
drawtext=fontfile=${FONT}:text='4 findings retained':fontsize=39:fontcolor=0xf6fbff:x=932:y=390,\
drawbox=x=880:y=496:w=420:h=108:color=0x182714:t=fill,\
drawbox=x=880:y=496:w=420:h=108:color=0x85d175:t=3,\
drawtext=fontfile=${FONT}:text='1 unsupported claim blocked':fontsize=33:fontcolor=0xf6fbff:x=914:y=540,\
drawtext=fontfile=${FONT}:text='Generated NTFS image  |  Remote SIFT backend':fontsize=30:fontcolor=0x94a7b7:x=886:y=696,\
drawtext=fontfile=${FONT}:text='No Windows required for the demo path':fontsize=30:fontcolor=0xa8d5ff:x=886:y=748,\
drawtext=fontfile=${FONT}:text='github.com/JafarBanar/findevil':fontsize=24:fontcolor=0x7f96a6:x=112:y=878" \
        -frames:v 1 -q:v 2 "$OUT_DIR/devpost_option_b.jpg"
}

render_option_c() {
    ffmpeg -y -hide_banner -loglevel error \
        -f lavfi -i "color=c=0x091019:s=${WIDTH}x${HEIGHT}" \
        -vf "\
drawtext=fontfile=${FONT}:text='CaseTrace':fontsize=126:fontcolor=0xf6fbff:x=90:y=170,\
drawtext=fontfile=${FONT}:text='DFIR agent for SIFT':fontsize=40:fontcolor=0xd7e1e9:x=96:y=240,\
drawbox=x=96:y=330:w=300:h=108:color=0x163145:t=fill,\
drawbox=x=96:y=330:w=300:h=108:color=0x57d1ff:t=3,\
drawtext=fontfile=${FONT}:text='Collect':fontsize=44:fontcolor=0xf6fbff:x=190:y=375,\
drawbox=x=460:y=330:w=300:h=108:color=0x342313:t=fill,\
drawbox=x=460:y=330:w=300:h=108:color=0xffb86b:t=3,\
drawtext=fontfile=${FONT}:text='Verify':fontsize=44:fontcolor=0xf6fbff:x=560:y=375,\
drawbox=x=824:y=330:w=300:h=108:color=0x182714:t=fill,\
drawbox=x=824:y=330:w=300:h=108:color=0x85d175:t=3,\
drawtext=fontfile=${FONT}:text='Self-correct':fontsize=44:fontcolor=0xf6fbff:x=886:y=375,\
drawbox=x=1188:y=330:w=220:h=108:color=0x2f1c25:t=fill,\
drawbox=x=1188:y=330:w=220:h=108:color=0xff8eb0:t=3,\
drawtext=fontfile=${FONT}:text='Report':fontsize=42:fontcolor=0xf6fbff:x=1240:y=375,\
drawbox=x=245:y=384:w=215:h=8:color=0x4b6476:t=fill,\
drawbox=x=609:y=384:w=215:h=8:color=0x4b6476:t=fill,\
drawbox=x=973:y=384:w=215:h=8:color=0x4b6476:t=fill,\
drawbox=x=96:y=520:w=620:h=280:color=0x0d151d@0.96:t=fill,\
drawbox=x=96:y=520:w=620:h=280:color=0x243442@0.95:t=3,\
drawtext=fontfile=${FONT}:text='10/10 tools  •  4 findings  •  1 blocked claim':fontsize=34:fontcolor=0xf6fbff:x=128:y=580,\
drawtext=fontfile=${FONT}:text='Generated 128 MB NTFS image':fontsize=44:fontcolor=0xa8d5ff:x=128:y=652,\
drawtext=fontfile=${FONT}:text='Real SIFT execution, evidence IDs, traceable outputs':fontsize=31:fontcolor=0xd7e1e9:x=128:y=716,\
drawtext=fontfile=${FONT}:text='github.com/JafarBanar/findevil':fontsize=24:fontcolor=0x7f96a6:x=128:y=776,\
drawbox=x=830:y=510:w=580:h=320:color=0x111922@0.98:t=fill,\
drawbox=x=830:y=510:w=580:h=320:color=0x2c3a47@0.95:t=3,\
drawtext=fontfile=${MONO_FONT}:textfile=${TMP_DIR}/terminal_c.txt:fontsize=23:fontcolor=0xe8eef5:x=868:y=575:line_spacing=13,\
drawtext=fontfile=${FONT}:text='Evidence-linked findings':fontsize=34:fontcolor=0xffc98f:x=842:y=890" \
        -frames:v 1 -q:v 2 "$OUT_DIR/devpost_option_c.jpg"
}

render_option_a
render_option_b
render_option_c

echo "Created:"
echo "  $OUT_DIR/devpost_option_a.jpg"
echo "  $OUT_DIR/devpost_option_b.jpg"
echo "  $OUT_DIR/devpost_option_c.jpg"
