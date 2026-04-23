#!/bin/bash
# Run the live terminal sequence used in the Devpost screencast.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_OUTPUT="${RUN_OUTPUT:-runs/realistic-windows-image}"

cd "$ROOT"

clear
printf 'CaseTrace live terminal demo\n'
printf 'Read-only DFIR agent for SIFT\n'
sleep 3

printf '$ jq .summary %s/run_metadata.json\n\n' "$RUN_OUTPUT"
jq '.summary' "$RUN_OUTPUT/run_metadata.json"
sleep 7

printf '\n$ jq ".iteration_history[] | {iteration, tools_run, issues}" %s/run_metadata.json\n\n' "$RUN_OUTPUT"
jq '.iteration_history[] | {iteration, tools_run, issues}' "$RUN_OUTPUT/run_metadata.json"
sleep 9

clear
printf '$ bash scripts/print_demo_highlights.sh %s\n\n' "$RUN_OUTPUT"
bash scripts/print_demo_highlights.sh "$RUN_OUTPUT"
sleep 11

clear
printf '$ sed -n "1,180p" %s/report.md\n\n' "$RUN_OUTPUT"
sed -n '1,180p' "$RUN_OUTPUT/report.md"
sleep 11

printf '\nDemo complete.\n'
sleep 3

if [ -n "${DEMO_DONE_FILE:-}" ]; then
    : > "$DEMO_DONE_FILE"
fi
