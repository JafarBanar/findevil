# Devpost Submission Copy

Use this file as direct paste material for the Devpost form.

## Elevator Pitch

CaseTrace is a read-only, self-correcting DFIR agent for SIFT that turns Windows forensic artifacts into evidence-linked findings.

## About the Project

## Inspiration

Attackers are getting faster at generating plausible intrusion steps, phishing lures, scripts, and persistence mechanisms. Defenders still spend a lot of time manually collecting artifacts, cross-checking evidence, and deciding which claims are real versus speculative. I wanted to build a DFIR workflow that keeps the speed advantage of AI without accepting the usual tradeoff of unsupported claims.

That became CaseTrace: a read-only, self-correcting DFIR agent that can investigate Windows evidence on SIFT, keep a traceable audit trail, and block findings it cannot actually support.

## What it does

CaseTrace runs a bounded forensic investigation loop over typed tools instead of free-form shell access. It collects evidence, synthesizes candidate findings, verifies those findings, and then either confirms them, downgrades them to inference, or blocks them if they are unsupported.

Every final claim links back to `evidence_ids`, raw tool output is preserved, and the run writes traceable artifacts like:

- `report.md`
- `findings.json`
- `tool_calls.jsonl`
- `events.jsonl`
- `run_metadata.json`

For the final demo, CaseTrace analyzes a reproducible raw NTFS image through a remote SIFT backend over SSH and detects:

- suspicious script execution
- likely web delivery of a payload
- persistence activity
- suspicious artifact matches

It also blocks a speculative credential-theft claim because no supporting evidence exists.

## How I built it

I built CaseTrace in Python around a bounded orchestration loop with explicit phases:

- intake
- plan
- collect
- synthesize
- verify
- self-correct
- finalize

The core safety decision was to avoid giving the model arbitrary shell access. Instead, I exposed typed forensic tools such as:

- `timeline_mft`
- `prefetch_summary`
- `amcache_summary`
- `registry_autoruns`
- `scheduled_tasks`
- `browser_history`
- `user_logons`
- `yara_scan`

Those tools run either against deterministic fixtures or through a SIFT SSH bridge that calls a fixed remote script and returns structured JSON. That means the model can request named forensic actions, but it cannot improvise arbitrary system commands.

Because I did not have a Windows host available for the final demo, I created a no-Windows path that still proves image-backed analysis: a controlled Windows-like artifact tree is converted into a real raw NTFS image on the SIFT VM, then CaseTrace analyzes that image end to end.

## Challenges I ran into

- Running x86_64 SIFT on Apple Silicon through UTM is slow.
- SIFT setup on the VM needed extra hardening around Ubuntu package state.
- The obvious hackathon shortcut would have been to let the model make broad claims from partial evidence, but that would defeat the point of a DFIR tool.
- I did not have Windows available for a native OS image run, so I had to design a no-Windows image-backed workflow that still exercises real forensic parsing and keeps the claims honest.

## What I learned

- In autonomous incident response, auditability matters as much as model quality.
- Verification is not a nice-to-have. It is the difference between a useful investigation assistant and a confident hallucination engine.
- A typed tool surface is a much stronger security boundary than prompt instructions alone.
- It is better for the system to say "I cannot prove this" than to invent a complete attack story.

## What's next

- Validate against a native Windows OS image or a public DFIR dataset with known ground truth.
- Expand the typed artifact surface while preserving the same guardrails.
- Improve visual reporting for analysts and judges.
- Package the no-Windows image workflow into an even simpler one-command demo.

## Built With

- Python
- OpenAI
- SIFT
- UTM
- SSH
- JSON
- Markdown
- jq
- ffmpeg
- macOS
- Linux
- digital forensics
- DFIR

## Try It Out Links

- GitHub repo: https://github.com/JafarBanar/findevil
- Hackathon page: https://findevil.devpost.com/

If you upload the demo video to YouTube as unlisted, add that as another link.

## Media Suggestions

### Thumbnail

Upload:

- `demo/devpost_thumbnail_clean.jpg`

### Gallery Images

Good screenshots to upload:

1. `runs/realistic-windows-image/report.md` in terminal
2. `runs/realistic-windows-image/tool_calls.jsonl` showing evidence traceability
3. `docs/architecture_diagram.png`
4. `docs/NTFS_IMAGE_VALIDATION.md`

### Video Demo Link

Upload `demo/devpost_live_terminal_narrated.mp4` to YouTube as **Unlisted**, then paste the YouTube URL into Devpost.
