"""
shared/optimization_engine.py — Weekly analytics + proactive idea generation.

Runs every Friday at 8AM ET via GitHub Actions.

For each newsletter it:
  1. Pulls last 30 days of Beehiiv post stats (open rate, click rate)
  2. Identifies top/bottom performers
  3. Generates 5 new topic ideas optimized for the coming week
  4. Surfaces 1 new affiliate program to apply to
  5. Compiles a concise weekly briefing and emails it to Jay

The email arrives Friday morning so Jay can review and respond — and Claude
executes any approved actions the same day.

Usage (GitHub Actions):
    python shared/optimization_engine.py

Local test:
    python shared/optimization_engine.py --preview
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
import anthropic

# Allow imports from sibling newsletter dirs
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from shared.beehiiv_client import BeehiivClient
from shared.topic_tracker import get_topic_stats


# ---------------------------------------------------------------------------
# Newsletter registry — add new newsletters here
# ---------------------------------------------------------------------------

NEWSLETTERS = [
    {
        "name": "Silver & Cents",
        "dir": "silver-and-cents",
        "env_prefix": "SILVER_AND_CENTS",
        "audience": "retirees aged 58–75",
        "focus": "retirement finance (Social Security, Medicare, estate planning, investing)",
    },
    {
        "name": "Daily Steals",
        "dir": "daily-steals",
        "env_prefix": "DAILY_STEALS",
        "audience": "deal-hunters aged 35–70",
        "focus": "daily deals, discounts, cashback, limited-time offers",
    },
    {
        "name": "Playtime",
        "dir": "playtime",
        "env_prefix": "PLAYTIME",
        "audience": "adults 50+ seeking entertainment and leisure",
        "focus": "games, puzzles, streaming picks, books, weekend activities",
    },
    {
        "name": "Peak Health",
        "dir": "peak-health",
        "env_prefix": "PEAK_HEALTH",
        "audience": "health-conscious adults aged 45–70",
        "focus": "longevity, nutrition, supplements, fitness for aging, mental sharpness",
    },
    {
        "name": "Money IQ",
        "dir": "money-iq",
        "env_prefix": "MONEY_IQ",
        "audience": "ambitious adults aged 25–50",
        "focus": "investing basics, debt payoff, wealth building, side income, smart spending",
    },
]


# ---------------------------------------------------------------------------
# Per-newsletter analytics
# ---------------------------------------------------------------------------

def _get_newsletter_client(newsletter: dict) -> BeehiivClient | None:
    prefix = newsletter["env_prefix"]
    api_key = os.getenv(f"{prefix}_BEEHIIV_API_KEY") or os.getenv("BEEHIIV_API_KEY")
    pub_id  = os.getenv(f"{prefix}_BEEHIIV_PUBLICATION_ID")
    if not api_key or not pub_id:
        return None
    return BeehiivClient(api_key=api_key, publication_id=pub_id)


def _analyze_newsletter(newsletter: dict) -> dict:
    """Returns performance stats + topic stats for one newsletter."""
    client = _get_newsletter_client(newsletter)
    stats_list = []
    avg_open = avg_click = None

    if client:
        try:
            stats_list = client.get_recent_stats(limit=30)
            if stats_list:
                avg_open  = round(sum(s["open_rate"]  for s in stats_list) / len(stats_list), 4)
                avg_click = round(sum(s["click_rate"] for s in stats_list) / len(stats_list), 4)
        except Exception as e:
            stats_list = []
            print(f"  Warning: Could not fetch stats for {newsletter['name']}: {e}")

    # Sort by open rate
    top3    = sorted(stats_list, key=lambda s: s["open_rate"], reverse=True)[:3]
    bottom3 = sorted(stats_list, key=lambda s: s["open_rate"])[:3]

    topic_stats = get_topic_stats(newsletter["dir"])

    return {
        "newsletter": newsletter,
        "avg_open_rate": avg_open,
        "avg_click_rate": avg_click,
        "total_posts_analyzed": len(stats_list),
        "top_performers": top3,
        "bottom_performers": bottom3,
        "topic_stats": topic_stats,
    }


# ---------------------------------------------------------------------------
# Idea generation via Claude
# ---------------------------------------------------------------------------

def _generate_ideas(analysis: dict) -> dict:
    """Uses Claude to generate 5 topic ideas + 1 affiliate suggestion."""
    nl = analysis["newsletter"]
    top    = analysis["top_performers"]
    bottom = analysis["bottom_performers"]

    top_lines    = "\n".join(f'  - "{s["subject_line"]}" ({s["open_rate"]*100:.1f}% open)' for s in top) or "  (No data yet)"
    bottom_lines = "\n".join(f'  - "{s["subject_line"]}" ({s["open_rate"]*100:.1f}% open)' for s in bottom) or "  (No data yet)"

    prompt = f"""You are the editorial strategist for "{nl["name"]}", a daily newsletter for {nl["audience"]}.
The newsletter covers: {nl["focus"]}

RECENT PERFORMANCE:
Top 3 issues (by open rate):
{top_lines}

Bottom 3 issues (by open rate):
{bottom_lines}

YOUR TASK:
1. Analyze what the top performers have in common (hooks, urgency, specificity, numbers, etc.)
2. Generate exactly 5 fresh newsletter topic ideas for next week that apply those insights.
   - Each idea: one punchy subject line + one sentence on the angle/hook
   - Topics must be timely, specific, and immediately useful to the audience
   - Do NOT repeat topics that have already performed poorly
3. Suggest 1 affiliate program that would be a natural fit for this newsletter
   (name, network, estimated commission, why it fits this audience)

Respond in this exact JSON format:
{{
  "performance_insight": "2-3 sentence analysis of what's working",
  "topic_ideas": [
    {{"subject_line": "...", "angle": "..."}},
    {{"subject_line": "...", "angle": "..."}},
    {{"subject_line": "...", "angle": "..."}},
    {{"subject_line": "...", "angle": "..."}},
    {{"subject_line": "...", "angle": "..."}}
  ],
  "affiliate_suggestion": {{
    "name": "...",
    "network": "...",
    "commission": "...",
    "why_it_fits": "..."
  }}
}}"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Weekly briefing email
# ---------------------------------------------------------------------------

def _build_briefing_html(all_results: list[dict]) -> str:
    """Builds the full weekly briefing email in HTML."""
    now = datetime.now().strftime("%B %d, %Y")
    sections = []

    for r in all_results:
        nl   = r["newsletter"]
        a    = r["analysis"]
        ideas = r["ideas"]
        ts   = a["topic_stats"]

        open_pct  = f"{a['avg_open_rate']*100:.1f}%" if a["avg_open_rate"]  is not None else "N/A"
        click_pct = f"{a['avg_click_rate']*100:.1f}%" if a["avg_click_rate"] is not None else "N/A"

        topic_ideas_html = "".join(
            f"<li><strong>{i['subject_line']}</strong> — {i['angle']}</li>"
            for i in ideas.get("topic_ideas", [])
        )

        aff = ideas.get("affiliate_suggestion", {})
        aff_html = (
            f"<p><strong>💡 Affiliate opportunity:</strong> {aff.get('name','')} "
            f"({aff.get('network','')}) — {aff.get('commission','')}. "
            f"{aff.get('why_it_fits','')}</p>"
        ) if aff else ""

        sections.append(f"""
<div style="border:1px solid #e5e7eb;border-radius:8px;padding:20px;margin-bottom:24px;">
  <h2 style="margin:0 0 4px;color:#1e3a5f;font-size:20px;">{nl['name']}</h2>
  <p style="margin:0 0 12px;color:#6b7280;font-size:13px;">
    Avg open: <strong>{open_pct}</strong> &nbsp;|&nbsp;
    Avg click: <strong>{click_pct}</strong> &nbsp;|&nbsp;
    Topics used (last 365 days): <strong>{ts.get('topics_last_365_days', 0)}</strong> /
    <strong>{ts.get('topics_remaining_this_year', 365)}</strong> remaining
  </p>

  <p style="color:#374151;font-size:14px;"><em>{ideas.get('performance_insight','')}</em></p>

  <p style="font-weight:bold;color:#1e3a5f;margin-bottom:6px;">📋 Topic ideas for next week:</p>
  <ul style="margin:0 0 12px;padding-left:20px;color:#374151;font-size:14px;line-height:1.7;">
    {topic_ideas_html}
  </ul>

  {aff_html}
</div>""")

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#222;">
<h1 style="color:#1e3a5f;border-bottom:3px solid #3b82f6;padding-bottom:8px;">
  📬 Weekly Newsletter Briefing — {now}
</h1>
<p style="color:#6b7280;font-size:14px;">
  Your weekly performance summary + next week's topic ideas across all 5 newsletters.
  Reply with "go" on any idea and I'll execute it.
</p>
{body}
<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
<p style="font-size:12px;color:#9ca3af;">
  Generated automatically by the Silver & Cents optimization engine. · {now}
</p>
</body></html>"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(preview: bool = False) -> None:
    print(f"\n{'='*60}")
    print(f"  Newsletter Optimization Engine — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    all_results = []
    for nl in NEWSLETTERS:
        print(f"Analyzing {nl['name']}...")
        try:
            analysis = _analyze_newsletter(nl)
            ideas    = _generate_ideas(analysis)
            all_results.append({"newsletter": nl, "analysis": analysis, "ideas": ideas})
            print(f"  ✓ Open rate avg: {analysis['avg_open_rate']}")
            print(f"  ✓ Generated {len(ideas.get('topic_ideas',[]))} ideas")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    briefing_html = _build_briefing_html(all_results)

    if preview:
        # Print JSON summary to console instead of emailing
        for r in all_results:
            print(f"\n--- {r['newsletter']['name']} ---")
            print(f"Open rate: {r['analysis']['avg_open_rate']}")
            print(f"Ideas: {json.dumps(r['ideas'].get('topic_ideas',[]), indent=2)}")
        print("\n[PREVIEW MODE — email not sent]")
        return

    # Send via Beehiiv to Jay's account as a draft
    # (or send via SMTP if configured — placeholder below)
    _deliver_briefing(briefing_html)
    print("\n✅ Weekly briefing delivered!")


def _deliver_briefing(html: str) -> None:
    """
    Delivers the briefing. Currently posts as a draft to the Silver & Cents
    Beehiiv account so Jay sees it. Can be swapped for SMTP/SendGrid.
    """
    api_key = os.getenv("SILVER_AND_CENTS_BEEHIIV_API_KEY") or os.getenv("BEEHIIV_API_KEY")
    pub_id  = os.getenv("SILVER_AND_CENTS_BEEHIIV_PUBLICATION_ID")

    if not api_key or not pub_id:
        print("  No Beehiiv credentials — printing briefing to stdout instead.")
        print(html)
        return

    client = BeehiivClient(api_key=api_key, publication_id=pub_id)
    now = datetime.now().strftime("%B %d, %Y")
    client.create_post(
        subject=f"📬 Weekly Briefing — {now}",
        content_html=html,
        preview_text="Your weekly performance summary + next week's topic ideas.",
        draft=True,  # Always a draft — Jay reviews before it goes out
        tags=["optimization-briefing", "internal"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Newsletter optimization engine")
    parser.add_argument("--preview", action="store_true",
                        help="Print briefing to console instead of delivering")
    args = parser.parse_args()
    run(preview=args.preview)
