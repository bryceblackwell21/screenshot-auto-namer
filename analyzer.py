"""Core vision analysis module — sends screenshots to Claude and gets structured metadata back."""

from __future__ import annotations

import anthropic
import base64
import json
import mimetypes
from pathlib import Path
from dataclasses import dataclass


@dataclass
class AnalysisResult:
    """Structured result from Claude's vision analysis."""
    filename_slug: str  # e.g. "vscode-python-debug-config"
    category: str       # e.g. "code", "email", "design"
    description: str    # Brief description of what's in the screenshot
    confidence: float   # 0.0–1.0, how confident Claude is in the categorization


ANALYSIS_PROMPT = """Analyze this screenshot and provide a structured response for file naming and categorization.

Return a JSON object with exactly these fields:
{
  "filename_slug": "app-specific-content-detail",
  "category": "category-slug",
  "description": "One sentence describing what's shown",
  "confidence": 0.95
}

Rules for filename_slug:
- Lowercase, hyphen-separated, no spaces or special characters
- 3-5 words that describe the SPECIFIC content (not generic)
- ALWAYS lead with the app or context name if recognizable (e.g. "vscode-", "chrome-", "slack-", "figma-")
- Focus on what makes this screenshot UNIQUE — the specific feature, page, error, conversation topic, etc.
- Do NOT include dates unless a date shown in the content is central to the screenshot's meaning (e.g. a calendar event, a dated report)
- Do NOT use generic words like "screenshot", "image", "screen", "view", "window"
- Each screenshot of different content MUST produce a different slug — be specific enough to distinguish
- Good: "vscode-python-debug-breakpoint", "slack-standup-thread", "figma-landing-hero-section", "chrome-anthropic-api-docs"
- Bad: "screenshot", "code-editor", "chat-conversation", "web-page", "2025-03-24-slack-message"

Rules for category (pick the best fit, or create a new lowercase-hyphen slug):
- code: Code editors, terminals, IDE output, git diffs
- email: Email clients, inbox views
- chat: Slack, Discord, Teams, iMessage conversations
- social-media: Twitter/X, LinkedIn, Reddit, etc.
- documentation: API docs, wikis, README files, technical docs
- design: Figma, Sketch, design mockups, wireframes
- browser: General web browsing, articles, blogs
- spreadsheet: Excel, Google Sheets, data tables
- presentation: Slides, keynotes, pitch decks
- settings: System preferences, app settings, config screens
- error: Error messages, crash logs, bug reports
- uncategorized: Only if truly unidentifiable

Rules for confidence:
- 0.9+ : Clear, recognizable content
- 0.7-0.9: Partially obscured or ambiguous
- Below 0.7: Very unclear, use "uncategorized"

Return ONLY the JSON object, no markdown fences, no explanation."""


def encode_image(image_path: Path) -> tuple[str, str]:
    """Read and base64-encode an image file. Returns (base64_data, media_type)."""
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/png"  # sensible default for screenshots

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    return image_data, mime_type


def analyze_screenshot(image_path: Path, client: anthropic.Anthropic | None = None) -> AnalysisResult:
    """Send a screenshot to Claude Vision and get back naming/categorization metadata.

    Args:
        image_path: Path to the screenshot file.
        client: Optional pre-configured Anthropic client. If None, creates one from env var.

    Returns:
        AnalysisResult with filename_slug, category, description, and confidence.

    Raises:
        FileNotFoundError: If image_path doesn't exist.
        ValueError: If Claude's response can't be parsed.
        anthropic.APIError: If the API call fails.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    if client is None:
        client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    image_data, media_type = encode_image(image_path)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT,
                    },
                ],
            }
        ],
    )

    # Parse the response
    raw_text = message.content[0].text.strip()

    # Strip markdown fences if Claude adds them despite instructions
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]  # remove first line
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Claude response as JSON: {e}\nRaw: {raw_text}")

    return AnalysisResult(
        filename_slug=data["filename_slug"],
        category=data["category"],
        description=data["description"],
        confidence=float(data["confidence"]),
    )
