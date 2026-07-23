"""
The AI judgment layer. This is the piece that makes the pipeline an AI tool
rather than a scraper -- every raw signal gets tagged with a category and a
one-sentence rationale, not just stored as-is.

One function, one fixed output schema (see db.StructuredSignal). Today it
judges job postings. Later, feeding it news or funding signals means writing
a different prompt template, but the function signature and output shape
don't change -- so pipeline.py, db.py, and app.py never need to know the
difference.
"""

import json
import os
from datetime import datetime, timezone

import anthropic
from dotenv import load_dotenv

from db import StructuredSignal
from fetchers import RawSignal

# Reads the .env file in the project root (same folder as pipeline.py) and
# sets its contents as environment variables for this process. Without this,
# python has no way to know a .env file exists -- it's just a text file
# until something explicitly loads it.
load_dotenv()

MODEL = "claude-sonnet-4-6"

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError(
        "ANTHROPIC_API_KEY not found. Check that a .env file exists in the "
        "project root (same folder as pipeline.py, NOT inside venv/) and "
        "contains a line like: ANTHROPIC_API_KEY=sk-ant-..."
    )

client = anthropic.Anthropic(api_key=api_key)

JUDGE_PROMPT_TEMPLATE = """You are screening a job posting for a talent-sourcing tool.

Company: {company}
Posting title: {raw_text}

Classify this posting into exactly one of these tags:
- "ai_native": role centers on building or deploying AI/ML systems, agents, or AI-powered products
- "commercial_pm": commercial, project management, program management, or partnerships role
- "senior_ic": senior individual-contributor technical role (not people-management, not commercial)
- "other": doesn't clearly fit the above

Respond with ONLY a JSON object, no other text, in exactly this shape:
{{"tag": "...", "rationale": "<one sentence, under 20 words, explaining why>", "confidence": "high" | "medium" | "low"}}
"""


def judge_signal(raw: RawSignal) -> StructuredSignal:
    """
    Send one raw signal to Claude and return a StructuredSignal.

    Raises on malformed model output rather than silently guessing -- for a
    sourcing tool, a bad tag that looks confident is worse than a visible
    failure you can go inspect.
    """
    prompt = JUDGE_PROMPT_TEMPLATE.format(company=raw["company"], raw_text=raw["raw_text"])

    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON for {raw['company']!r}: {text!r}") from e

    return StructuredSignal(
        company=raw["company"],
        source_type=raw["source_type"],
        tag=parsed["tag"],
        rationale=parsed["rationale"],
        confidence=parsed["confidence"],
        raw_excerpt=raw["raw_text"][:200],
        url=raw["url"],
        fetched_at=raw["fetched_at"],
    )


if __name__ == "__main__":
    # Quick manual smoke test -- requires ANTHROPIC_API_KEY to be set.
    sample = RawSignal(
        company="Example Robotics",
        source_type="job_posting",
        raw_text="Senior Commercial Program Manager, Deployments",
        url="https://example.com/careers/123",
        fetched_at=datetime.now(timezone.utc).isoformat(),
    )
    result = judge_signal(sample)
    print(json.dumps(result, indent=2))