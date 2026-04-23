#!/bin/bash
# Record a live Terminal screencast for the Devpost submission.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-demo/devpost_live_terminal_raw.mp4}"
SCREEN_DEVICE="${SCREEN_DEVICE:-3}"
PROFILE_NAME="${PROFILE_NAME:-Homebrew}"
RUN_OUTPUT="${RUN_OUTPUT:-runs/realistic-windows-image}"
DONE_FILE="${DONE_FILE:-/tmp/casetrace-devpost-demo-done.$$}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-180}"
BACKDROP_IMAGE="${BACKDROP_IMAGE:-$ROOT/demo/devpost_black_wallpaper.png}"
USE_BACKDROP="${USE_BACKDROP:-1}"

mkdir -p "$(dirname "$OUT")"
rm -f "$DONE_FILE"

cleanup() {
    rm -f "$DONE_FILE"

    if [ "${USE_BACKDROP}" = "1" ]; then
        osascript <<EOF >/dev/null 2>&1 || true
tell application "Preview"
    close (every window whose name is "$(basename "$BACKDROP_IMAGE")")
end tell
EOF
    fi
}

trap cleanup EXIT

if [ "${USE_BACKDROP}" = "1" ]; then
    if [ ! -f "$BACKDROP_IMAGE" ]; then
        ffmpeg -y -hide_banner -loglevel error \
          -f lavfi \
          -i color=c=black:s=3456x2234 \
          -frames:v 1 \
          "$BACKDROP_IMAGE"
    fi

    open -a Preview "$BACKDROP_IMAGE"
    sleep 2

    osascript <<EOF
tell application "Preview"
    activate
    set bounds of front window to {0, 25, 1728, 1117}
end tell
EOF
fi

osascript <<EOF
tell application "Terminal"
    activate
    do script ""
    delay 0.8
    set current settings of front window to settings set "$PROFILE_NAME"
    set bounds of front window to {20, 20, 1710, 1085}
end tell
EOF

ffmpeg -y -hide_banner -loglevel error \
  -f avfoundation \
  -pixel_format nv12 \
  -framerate 30 \
  -capture_cursor 1 \
  -i "${SCREEN_DEVICE}:none" \
  -vf "scale=1920:-2" \
  "$OUT" &
CAPTURE_PID=$!

sleep 2

osascript <<EOF
tell application "Terminal"
    do script "cd \"$ROOT\"; DEMO_DONE_FILE=\"$DONE_FILE\" RUN_OUTPUT=\"$RUN_OUTPUT\" bash scripts/demo_terminal_session.sh" in front window
end tell
EOF

SECONDS_WAITED=0
while [ ! -f "$DONE_FILE" ]; do
    sleep 1
    SECONDS_WAITED=$((SECONDS_WAITED + 1))
    if [ "$SECONDS_WAITED" -ge "$MAX_WAIT_SECONDS" ]; then
        echo "ERROR: demo did not finish within ${MAX_WAIT_SECONDS}s"
        kill -INT "$CAPTURE_PID" 2>/dev/null || true
        wait "$CAPTURE_PID" || true
        exit 1
    fi
done

sleep 2
kill -INT "$CAPTURE_PID" 2>/dev/null || true
wait "$CAPTURE_PID" || true

if [ ! -s "$OUT" ]; then
    echo "ERROR: screencast was not created"
    exit 1
fi

echo "Created raw screencast: $OUT"
