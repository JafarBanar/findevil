# No-VM Workflow

Yes, you can build most of CaseTrace without the SIFT VM.

## Recommended Approach
1. Develop the agent, verifier, MCP server, and report flow locally on your Mac.
2. Use fixture artifacts or exported JSON from forensic tools instead of running the tools live.
3. Keep the interfaces stable so the fixture-backed tools can later be swapped for real SIFT-backed wrappers.
4. Move to a real SIFT environment only for final integration, benchmarking, and demo capture.

## What You Can Do Without SIFT
- build the repo and CLI
- test self-correction behavior
- test evidence-linked findings
- test MCP tool responses
- write documentation and reports
- benchmark iteration 1 vs final iteration

## What Still Benefits from SIFT
- validating real tool output
- confirming read-only handling against real images
- integrating with Protocol SIFT
- recording the final hackathon demo

## Practical Alternatives
- Use exported artifact JSON generated on another x86 box.
- Use a remote x86 Linux machine with SIFT instead of a local VM.
- Use the included sample case while you build locally, then switch to real evidence later.

If you want that remote path, use the SSH workflow in [REMOTE_SIFT.md](./REMOTE_SIFT.md).
