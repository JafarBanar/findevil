# Execution Logs

This repo now includes a committed sample execution-log bundle at:

- `docs/execution_logs/windows-persistence-case/`

Included artifacts:

- `report.md`
- `findings.json`
- `events.jsonl`
- `tool_calls.jsonl`
- `run_metadata.json`
- `raw/<tool_name>/*.json`

## Why This Bundle Exists

The main demo and remote SIFT runs are generated locally and are not committed under `runs/`, so this checked-in bundle provides a public judge-accessible example of:

- full iteration trace
- tool execution sequence with timestamps
- structured findings and verification issues
- per-tool `token_usage` fields
- run-level aggregated `token_usage`

## Token Usage Notes

For the current checked-in sample run, token usage is explicitly recorded as zero because the bundled example uses the local deterministic reasoning backend rather than an external hosted model.

That is why the logs show:

- `prompt_tokens: 0`
- `completion_tokens: 0`
- `total_tokens: 0`

with `source: local_reasoning_backend`.
