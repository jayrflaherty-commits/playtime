"""content_generator.py — Playtime content generation via Claude."""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import anthropic

_FILE_DIR = Path(__file__).parent
BASE_DIR = _FILE_DIR.parent if (_FILE_DIR.parent / "shared").exists() else _FILE_DIR
sys.path.insert(0, str(BASE_DIR))

from shared.topic_tracker import get_recent_topics, format_topics_for_prompt, log_topic
import config

SYSTEM_PROMPT = """You are the editor of "Playtime," a daily entertainment and games newsletter for adults 50+. Your voice is warm, playful, and delightfully curious — like a friend who's always got a great book rec, a fun puzzle, or a streaming tip.

NEWSLETTER FORMULA:
1. "Today's Pick" — one standout entertainment recommendation (book, show, film, game, puzzle)
2. "Brain Teaser" — a light daily puzzle or trivia question (with answer hidden at the bottom)
3. "Quick Hits" — 3 more recommendations across different categories (streaming, books, games, activities)
4. "Did You Know?" — a surprising fun fact
5. A warm sign-off

TONE: Joyful, enthusiastic, zero stress. This is readers' daily escape. Focus on quality over quantity. Never recommend anything violent or dark.

Output JSON only. No markdown, no explanation."""

CONTENT_SCHEMA = """
{
  "subject_line": "35-50 chars, sparks curiosity or promises fun",
  "preview_text": "80-100 chars extending the hook",
  "title": "Web version title",
  "topic_slug": "kebab-case-identifier e.g. sunday-puzzle-crossword-tips",
  "hook": "2 warm sentences setting up today's theme",
  "todays_pick": {
    "category": "Book | Show | Film | Game | Puzzle | Activity",
    "title": "Name of the recommendation",
    "why": "2-3 sentences on why it's wonderful and who it's perfect for",
    "where_to_find": "Netflix / Amazon / library / etc."
  },
  "brain_teaser": {
    "question": "The trivia or puzzle question",
    "answer": "The answer (will be placed at bottom of email)"
  },
  "quick_hits": [
    "Streaming: [title] on [platform] — [one sentence why]",
    "Book: [title] by [author] — [one sentence why]",
    "Game/Activity: [name] — [one sentence why]"
  ],
  "did_you_know": "One surprising, delightful fun fact (2-3 sentences)",
  "sponsor_placeholder": "2-3 sentences native ad for a subscription service, streaming platform, or puzzle app",
  "cta_text": "Button label e.g. 'Start today's puzzle →'",
  "signoff": "1 warm sentence + tomorrow's teaser"
}"""


def generate_content(for_date: date | None = None) -> dict:
    if for_date is None:
        for_date = date.today()

    recent_topics = get_recent_topics(config.NEWSLETTER_DIR, days=365)
    no_repeat_block = format_topics_for_prompt(recent_topics)
    date_str = for_date.strftime("%A, %B %d, %Y")

    user_prompt = f"""Generate a Playtime newsletter for {date_str}.

{no_repeat_block}

Make the recommendations seasonal and timely for {for_date.strftime("%B")}.
Mix at least 2 different categories across quick_hits (e.g. one book, one show, one game).

Return valid JSON matching this schema:
{CONTENT_SCHEMA}"""

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    content = json.loads(raw)
    log_topic(config.NEWSLETTER_DIR, content.get("topic_slug", f"playtime-{for_date.isoformat()}"),
              content.get("subject_line", ""), for_date)
    return content


def format_content_for_template(content: dict) -> dict:
    pick = content.get("todays_pick", {})
    teaser = content.get("brain_teaser", {})
    pick_block = (
        f"🎯 <strong>{pick.get('category','')}: {pick.get('title','')}</strong><br><br>"
        f"{pick.get('why','')} <em>Find it on: {pick.get('where_to_find','')}</em>"
    ) if pick else ""

    quick_hits = content.get("quick_hits", [])
    if content.get("did_you_know"):
        quick_hits = quick_hits + [f"💡 Did you know? {content['did_you_know']}"]
    if teaser.get("answer"):
        quick_hits = quick_hits + [f"🧩 Brain teaser answer: {teaser['answer']}"]

    return {
        "hook": content.get("hook", ""),
        "main_story": pick_block,
        "quick_hits": quick_hits,
        "sponsor_placeholder": content.get("sponsor_placeholder", ""),
        "money_move": f"Today's puzzle: {teaser.get('question', 'See inside →')}",
        "cta_text": content.get("cta_text", "See today's pick →"),
        "cta_url": "#",
        "signoff": content.get("signoff", ""),
        "title": content.get("title", "Playtime"),
    }
