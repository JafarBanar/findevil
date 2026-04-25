# CaseTrace Report

## Case
- Case ID: `windows-persistence-case`
- Profile: `windows`
- Disk: `sample_cases/windows_persistence_case/image.E01`
- Memory: `not provided`
- Iterations: `2`
- Output: `docs/execution_logs/windows-persistence-case`
- Token usage: `prompt=0 completion=0 total=0`

## Findings
### Suspicious script execution observed on the endpoint
- Status: `inference`
- Severity: `high`
- Confidence: `0.74`
- Sources: amcache_summary, prefetch_summary
- Evidence: `amcache-summary-1-bfde8d03fc`, `prefetch-powershell-update`
- Summary: Execution telemetry suggests a script or living-off-the-land binary ran from a suspicious location.
- Notes: Iteration 2: powershell.exe executed 7 times.

### Likely web delivery of a suspicious payload
- Status: `confirmed`
- Severity: `medium`
- Confidence: `0.85`
- Sources: browser_history, timeline_mft
- Evidence: `browser-history-1-0b44ee91cd`, `browser-history-2-44c843441b`, `timeline-mft-2-90342805bb`
- Summary: Browser activity and on-disk artifacts both reference invoice_update.zip, suggesting payload delivery.
- Notes: Iteration 2: Visited https://cdn-login-check.example/invoice_update.zip.

### Persistence mechanism likely established on the host
- Status: `confirmed`
- Severity: `high`
- Confidence: `0.85`
- Sources: registry_autoruns, scheduled_tasks
- Evidence: `registry-autoruns-1-e6b70b4552`, `scheduled-tasks-1-bfc2d01746`
- Summary: Persistence-related telemetry points to a suspicious autorun or scheduled task.
- Notes: Iteration 2: Autorun entry HKCU\Software\Microsoft\Windows\CurrentVersion\Run\ThemeUpdater launches powershell.exe -ExecutionPolicy Bypass -File C:\Users\Analyst\AppData\Roaming\Microsoft\Windows\Themes\update.ps1.

### Known suspicious artifact matched detection rules
- Status: `inference`
- Severity: `high`
- Confidence: `0.74`
- Sources: yara_scan
- Evidence: `yara-scan-1-ac33edc758`
- Summary: At least one artifact matched a detection signature during scanning.
- Notes: Iteration 2: YARA rule Suspicious_PowerShell_Downloader matched C:\Users\Analyst\AppData\Roaming\Microsoft\Windows\Themes\update.ps1.

## Verification

- `high` unsupported_claim: Blocked speculative finding 'Credential theft likely followed the suspicious browser session' because no credential-access evidence exists. Evidence: `browser-history-1-0b44ee91cd`. Action: gather corroborating evidence.

## Tool Coverage

- `amcache_summary`: success=true evidence=1 errors=0
- `browser_history`: success=true evidence=2 errors=0
- `case_info`: success=true evidence=1 errors=0
- `mount_image_readonly`: success=true evidence=1 errors=0
- `prefetch_summary`: success=true evidence=1 errors=0
- `registry_autoruns`: success=true evidence=1 errors=0
- `scheduled_tasks`: success=true evidence=1 errors=0
- `timeline_mft`: success=true evidence=2 errors=0
- `user_logons`: success=true evidence=1 errors=0
- `yara_scan`: success=true evidence=1 errors=0

## Iterations

- Iteration 1: tools=case_info, mount_image_readonly, user_logons, browser_history, prefetch_summary findings=2 issues=2
- Iteration 2: tools=amcache_summary, timeline_mft, yara_scan, registry_autoruns, scheduled_tasks findings=4 issues=1
