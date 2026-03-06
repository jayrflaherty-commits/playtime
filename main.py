"""main.py — Playtime newsletter entry point."""
import argparse, sys
from datetime import date
from pathlib import Path

_FILE_DIR = Path(__file__).parent
BASE_DIR = _FILE_DIR.parent if (_FILE_DIR.parent / "shared").exists() else _FILE_DIR
sys.path.insert(0, str(BASE_DIR))

import config
from content_generator import generate_content, format_content_for_template
from affiliates import get_daily_affiliate
from shared.beehiiv_client import BeehiivClient
from shared.email_template import build_email_html, get_theme

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--date", type=str, default=None)
    args = parser.parse_args()

    if not args.preview:
        config.validate()

    for_date = date.fromisoformat(args.date) if args.date else date.today()
    print(f"\nPlaytime — {for_date.strftime('%A, %B %d, %Y')}")

    raw = generate_content(for_date=for_date)
    affiliate = get_daily_affiliate(for_date)
    raw["cta_url"] = affiliate["url"]
    raw["cta_text"] = affiliate.get("cta", "See today's pick →")

    content = format_content_for_template(raw)
    theme = get_theme(config.NEWSLETTER_DIR)
    html = build_email_html(content=content, theme=theme)

    subject = raw.get("subject_line", f"Playtime — {for_date.strftime('%b %d')}")
    preview_text = raw.get("preview_text", "Your daily entertainment pick.")
    print(f"Subject: {subject}")

    if args.preview:
        print(html[:500])
        print("\n[PREVIEW MODE]")
        return

    client = BeehiivClient(api_key=config.BEEHIIV_API_KEY, publication_id=config.BEEHIIV_PUBLICATION_ID)
    post = client.create_post(subject=subject, content_html=html, preview_text=preview_text,
                               draft=args.draft, tags=["playtime"], send_hour_et=config.SEND_HOUR, send_minute_et=config.SEND_MINUTE)
    print(f"✅ {'DRAFT' if args.draft else 'SCHEDULED'}: {post.get('id')}")

if __name__ == "__main__":
    main()
