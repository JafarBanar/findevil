#!/usr/bin/env python3
"""Generate a Devpost thumbnail with the OpenAI Images API.

Requires:
  - OPENAI_API_KEY in the environment
  - network access to api.openai.com

Official docs used for this flow:
https://platform.openai.com/docs/guides/images/image-generation
https://platform.openai.com/docs/api-reference/images
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_PROMPT = """Create a premium Devpost thumbnail for a cybersecurity/DFIR project named CaseTrace.
Style: sleek, dark, technical, high contrast, trustworthy, modern product visual, no stock-photo look.
Composition: 3:2 landscape.
Include the word 'CaseTrace' prominently and legibly.
Secondary line: 'Read-only, self-correcting DFIR agent for SIFT'.
Visually suggest: forensic evidence, terminal output, Windows artifact analysis, traceability, and one blocked unsupported claim.
Palette: deep navy, cool slate, cyan accents, small amber accent.
Avoid clutter, avoid too much small text, avoid cartoons, avoid logos of other companies.
Make it look polished enough for a hackathon project cover image."""


def generate_image(prompt: str, output_path: Path, api_key: str) -> None:
    payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1536x1024",
        "quality": "medium",
        "background": "opaque",
        "output_format": "jpeg",
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"OpenAI API request failed: HTTP {exc.code}\n{body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"OpenAI API request failed: {exc}") from exc

    image_b64 = data["data"][0].get("b64_json")
    if not image_b64:
        raise SystemExit("OpenAI API response did not contain b64_json image data.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(base64.b64decode(image_b64))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="demo/devpost_thumbnail_openai.jpg")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is not set in the current shell.")

    output_path = Path(args.output)
    generate_image(args.prompt, output_path, api_key)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
