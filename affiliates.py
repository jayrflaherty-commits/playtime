"""affiliates.py — Affiliate links for Playtime newsletter."""
from __future__ import annotations
from datetime import date
from typing import Optional

AMAZON_ASSOCIATE_TAG = "retirehub09-20"

AFFILIATE_LINKS = {
    "audiobooks": {
        "name": "Audible — audiobooks & podcasts",
        "description": "Try Audible free for 30 days — 1 free credit, cancel anytime",
        "cta": "Start free trial →",
        "url": "https://YOUR_AUDIBLE_AFFILIATE_LINK_HERE",
        # Audible affiliate via Amazon Associates or CJ
        # Commission: $5–10 per trial signup | 24-hr cookie
    },
    "brain_training": {
        "name": "Lumosity — brain training games",
        "description": "Science-backed brain games shown to improve memory and focus in just 10 min/day",
        "cta": "Try free →",
        "url": "https://YOUR_LUMOSITY_AFFILIATE_LINK_HERE",
        # Lumosity affiliate via CJ or direct
        # Commission: $10–20 per paid signup
    },
    "streaming": {
        "name": "MasterClass — learn from the best",
        "description": "Watch Gordon Ramsay cook, Spike Lee direct, and Serena Williams train — all for $10/mo",
        "cta": "Browse all classes →",
        "url": "https://YOUR_MASTERCLASS_AFFILIATE_LINK_HERE",
        # MasterClass affiliate via Impact
        # Commission: $25–50 per new subscription
    },
    "puzzles": {
        "name": "Amazon puzzle picks",
        "description": "Our favorite jigsaw puzzles this month — from 500 to 2,000 pieces",
        "cta": "Browse puzzles →",
        "url": f"https://www.amazon.com/s?k=jigsaw+puzzles+1000+pieces&tag={AMAZON_ASSOCIATE_TAG}",
    },
    "ebooks": {
        "name": "Kindle Unlimited",
        "description": "Read over 4 million books, magazines, and comics — free for 30 days",
        "cta": "Try Kindle Unlimited free →",
        "url": f"https://www.amazon.com/kindle-dbs/hz/subscribe/ku?tag={AMAZON_ASSOCIATE_TAG}",
    },
}

CATEGORY_ORDER = list(AFFILIATE_LINKS.keys())

def get_daily_affiliate(for_date: date | None = None) -> dict:
    if for_date is None:
        for_date = date.today()
    day_index = for_date.toordinal() % len(CATEGORY_ORDER)
    key = CATEGORY_ORDER[day_index]
    affiliate = AFFILIATE_LINKS[key].copy()
    affiliate["category"] = key
    return affiliate

def get_amazon_link(asin: str) -> str:
    return f"https://www.amazon.com/dp/{asin}?tag={AMAZON_ASSOCIATE_TAG}"
