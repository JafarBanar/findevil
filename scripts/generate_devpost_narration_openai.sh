#!/bin/bash
# Generate narration audio with the OpenAI Audio API.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-demo/devpost_narration.mp3}"
NARRATION_FILE="${NARRATION_FILE:-$ROOT/docs/DEVPOST_DEMO_NARRATION.txt}"
ENV_FILE="${ENV_FILE:-}"
MODEL="${MODEL:-gpt-4o-mini-tts}"
VOICE="${VOICE:-alloy}"

if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq not found"
    exit 1
fi

if [ ! -f "$NARRATION_FILE" ]; then
    echo "ERROR: narration file not found: $NARRATION_FILE"
    exit 1
fi

if [ -z "${OPENAI_API_KEY:-}" ] && [ -n "$ENV_FILE" ]; then
    if [ ! -f "$ENV_FILE" ]; then
        echo "ERROR: env file not found: $ENV_FILE"
        exit 1
    fi

    OPENAI_API_KEY="$(awk -F= '/^OPENAI_API_KEY=/{print substr($0, index($0, "=") + 1)}' "$ENV_FILE" | head -n 1 | sed 's/^"//; s/"$//')"
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: set OPENAI_API_KEY or provide ENV_FILE=/path/to/.env"
    exit 1
fi

mkdir -p "$(dirname "$OUT")"

PAYLOAD="$(jq -Rs --arg model "$MODEL" --arg voice "$VOICE" --arg instructions "Speak clearly, calmly, and like a technical product demo narrator." '{model:$model, voice:$voice, input:., instructions:$instructions, format:"mp3"}' < "$NARRATION_FILE")"

curl -fsSL https://api.openai.com/v1/audio/speech \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  --output "$OUT"

echo "Created narration audio: $OUT"
