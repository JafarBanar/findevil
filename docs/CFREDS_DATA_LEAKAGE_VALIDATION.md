# NIST CFReDS Public Validation

This document records the first public native-Windows ground-truth validation run for CaseTrace.

## Dataset

- Source: NIST CFReDS Data Leakage Case
- Overview: https://cfreds-archive.nist.gov/data_leakage_case/data-leakage-case.html
- Public answers: https://cfreds-archive.nist.gov/data_leakage_case/leakage-answers.pdf
- Image used: `cfreds_2015_data_leakage_pc.dd`
- Case wrapper: `cases/cfreds-data-leakage-pc`
- Final run: `runs/cfreds-data-leakage-pc-v3`

## Why This Case

This is a strong validation target because it provides both:

- a public native Windows disk image
- a published answer key with documented investigator expectations

That makes it a better honesty check than the synthetic demo paths.

## What the NIST Answer Key Documents

The published answers describe activity including:

- Internet Explorer usage and web searches
- Google Drive account and sync artifacts
- USB media usage and copying confidential files
- anti-forensics behavior involving Eraser and CCleaner

Those expectations come from the public NIST answer key above.

## CaseTrace Result

Run summary for `runs/cfreds-data-leakage-pc-v3`:

- 2 iterations
- 10/10 tool executions succeeded
- 0 retained findings
- 0 verification issues

This is not a tooling crash. It is a coverage miss.

## What This Validation Proves

- CaseTrace can analyze a public native Windows image through the remote SIFT bridge.
- The read-only guardrails still hold on a real public case.
- The current typed collector set does not yet recover the main artifacts that matter for this Windows 7 leakage scenario.

## Coverage Gaps Exposed By This Run

The current implementation missed the public ground-truth behaviors primarily because it does not yet include:

- Internet Explorer / WebCache parsing
- Google Drive sync-log and SQLite artifact parsing
- USB/removable-media artifact parsing
- Outlook / email artifact parsing
- deleted-record recovery for SQLite and other wiped traces

There is also limited value in `amcache_summary` on this Windows 7 case as currently implemented.

## False Positive Check

An intermediate run (`runs/cfreds-data-leakage-pc-v2`) produced a bad hit on `C:\Boot\memtest.exe` through an overly broad content scan. The remote collector was tightened and the final validation run (`v3`) removed that false positive.

## Bottom Line

CaseTrace no longer has the weakness of "no native Windows/public ground-truth dataset yet."

It now has a more useful and honest result:

- public native-Windows validation exists
- the safety model held
- the current collector coverage is still too narrow for this Windows 7 leakage case
