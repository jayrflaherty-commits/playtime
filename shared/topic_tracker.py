"""
topic_tracker.py — 365-day topic deduplication for the newsletter media empire.

Each newsletter has its own SQLite DB stored at:
  /Users/Jay/Desktop/Claude stuff/<newsletter-name>/topics.db

HOW IT WORKS:
1. Before content generation: call get_recent_topics(newsletter) to get the
   last 365 days of used topic slugs + subject lines.
2. Inject those into the Claude prompt so it doesn't repeat them.
3. After generation: call log_topic(newsletter, topic_slug, subject_line) to
   record the new issue.
"""

from __future__ import annotations

import sqlite3
import os
from datetime import date, timedelta
from pathlib import Path


# ---------------------------------------------------------------------------
# DB location helpers
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent  # /Users/Jay/Desktop/Claude stuff/


def _db_path(newsletter_name: str) -> str:
    """Returns the path to the SQLite DB for a given newsletter."""
    return str(BASE_DIR / newsletter_name / "topics.db")


def _get_connection(newsletter_name: str) -> sqlite3.Connection:
    """Opens (or creates) the SQLite DB for a newsletter."""
    db = _db_path(newsletter_name)
    os.makedirs(os.path.dirname(db), exist_ok=True)
    conn = sqlite3.connect(db)
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Creates the topics table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_slug     TEXT    NOT NULL,
            subject_line   TEXT    NOT NULL,
            published_date TEXT    NOT NULL,
            created_at     TEXT    DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_published_date ON topics (published_date)
    """)
    conn.commit()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_recent_topics(newsletter_name: str, days: int = 365) -> list[dict]:
    """
    Returns all topics published in the last `days` days for a newsletter.

    Each entry is a dict with:
        - topic_slug: short identifier used to detect duplicates
        - subject_line: full subject line for Claude context
        - published_date: YYYY-MM-DD string

    Usage in content_generator.py:
        recent = get_recent_topics("silver-and-cents")
        # Pass to Claude prompt as "do not repeat these topics"
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = _get_connection(newsletter_name)
    try:
        cursor = conn.execute(
            """
            SELECT topic_slug, subject_line, published_date
            FROM topics
            WHERE published_date >= ?
            ORDER BY published_date DESC
            """,
            (cutoff,),
        )
        rows = cursor.fetchall()
        return [
            {"topic_slug": r[0], "subject_line": r[1], "published_date": r[2]}
            for r in rows
        ]
    finally:
        conn.close()


def log_topic(newsletter_name: str, topic_slug: str, subject_line: str,
              published_date: date | None = None) -> int:
    """
    Records a newly published topic to the DB.

    Returns the row ID of the inserted record.

    Usage after successful Beehiiv post:
        log_topic("silver-and-cents", "social-security-cola-2026",
                  "Social Security just got a raise — here's yours")
    """
    if published_date is None:
        published_date = date.today()

    conn = _get_connection(newsletter_name)
    try:
        cursor = conn.execute(
            """
            INSERT INTO topics (topic_slug, subject_line, published_date)
            VALUES (?, ?, ?)
            """,
            (topic_slug, subject_line, published_date.isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def has_topic_been_used(newsletter_name: str, topic_slug: str,
                        days: int = 365) -> bool:
    """
    Returns True if a topic_slug has been used in the last `days` days.

    Use this for a quick check before generating content.
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    conn = _get_connection(newsletter_name)
    try:
        cursor = conn.execute(
            """
            SELECT COUNT(*) FROM topics
            WHERE topic_slug = ? AND published_date >= ?
            """,
            (topic_slug, cutoff),
        )
        count = cursor.fetchone()[0]
        return count > 0
    finally:
        conn.close()


def format_topics_for_prompt(topics: list[dict], max_topics: int = 60) -> str:
    """
    Formats recent topics into a string ready to inject into a Claude prompt.

    Example output:
        RECENTLY COVERED TOPICS (do not repeat these within the past year):
        - social-security-cola-2026: "Social Security just got a raise — here's yours" (2026-01-15)
        - medicare-part-d-2026: "The one Medicare change that affects your drug costs" (2026-01-14)
        ...

    Usage:
        recent = get_recent_topics("silver-and-cents")
        prompt_block = format_topics_for_prompt(recent)
        # Insert into Claude system prompt
    """
    if not topics:
        return ""

    lines = ["RECENTLY COVERED TOPICS (do not repeat any of these within the past year):"]
    for t in topics[:max_topics]:
        lines.append(f'- {t["topic_slug"]}: "{t["subject_line"]}" ({t["published_date"]})')

    if len(topics) > max_topics:
        lines.append(f"... and {len(topics) - max_topics} more (all off-limits for 365 days).")

    return "\n".join(lines)


def get_topic_stats(newsletter_name: str) -> dict:
    """
    Returns basic stats about the topic history for a newsletter.

    Useful for the optimization engine and debugging.
    """
    conn = _get_connection(newsletter_name)
    try:
        total = conn.execute("SELECT COUNT(*) FROM topics").fetchone()[0]
        last_365 = conn.execute(
            "SELECT COUNT(*) FROM topics WHERE published_date >= ?",
            ((date.today() - timedelta(days=365)).isoformat(),),
        ).fetchone()[0]
        oldest = conn.execute(
            "SELECT MIN(published_date) FROM topics"
        ).fetchone()[0]
        newest = conn.execute(
            "SELECT MAX(published_date) FROM topics"
        ).fetchone()[0]
        return {
            "newsletter": newsletter_name,
            "total_topics": total,
            "topics_last_365_days": last_365,
            "oldest_topic_date": oldest,
            "newest_topic_date": newest,
            "topics_remaining_this_year": max(0, 365 - last_365),
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI for manual inspection
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import json

    newsletter = sys.argv[1] if len(sys.argv) > 1 else "silver-and-cents"
    print(f"\n=== Topic Tracker: {newsletter} ===\n")

    stats = get_topic_stats(newsletter)
    print("Stats:")
    print(json.dumps(stats, indent=2))

    recent = get_recent_topics(newsletter, days=30)
    print(f"\nLast 30 days ({len(recent)} topics):")
    for t in recent:
        print(f"  [{t['published_date']}] {t['topic_slug']}: {t['subject_line']}")

    print("\nPrompt injection block (first 5):")
    print(format_topics_for_prompt(recent[:5]))
