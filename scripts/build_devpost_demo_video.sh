#!/bin/bash
# Build the final narrated Devpost demo video.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW_VIDEO="${RAW_VIDEO:-$ROOT/demo/devpost_live_terminal_raw.mp4}"
NARRATION_AUDIO="${NARRATION_AUDIO:-$ROOT/demo/devpost_narration.mp3}"
OUT="${1:-$ROOT/demo/devpost_live_terminal_narrated.mp4}"
VIDEO_FILTER="${VIDEO_FILTER:-crop=1868:1108:18:40,scale=1920:-2}"

if [ ! -f "$RAW_VIDEO" ]; then
    echo "ERROR: raw video not found: $RAW_VIDEO"
    exit 1
fi

if [ ! -f "$NARRATION_AUDIO" ]; then
    echo "ERROR: narration audio not found: $NARRATION_AUDIO"
    exit 1
fi

mkdir -p "$(dirname "$OUT")"

ffmpeg -y -hide_banner -loglevel error \
  -i "$RAW_VIDEO" \
  -i "$NARRATION_AUDIO" \
  -filter:v "$VIDEO_FILTER" \
  -filter:a "apad" \
  -c:v libx264 \
  -c:a aac \
  -shortest \
  "$OUT"

echo "Created final narrated video: $OUT"
