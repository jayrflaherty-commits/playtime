"""config.py — Playtime newsletter configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

NEWSLETTER_NAME        = "Playtime"
NEWSLETTER_DIR         = "playtime"
TAGLINE                = "Games, fun, and entertainment — every single day"
SEND_HOUR              = 7
TIMEZONE               = "America/New_York"

ANTHROPIC_API_KEY      = os.getenv("ANTHROPIC_API_KEY", "")
BEEHIIV_API_KEY        = os.getenv("PLAYTIME_BEEHIIV_API_KEY", os.getenv("BEEHIIV_API_KEY", ""))
BEEHIIV_PUBLICATION_ID = os.getenv("PLAYTIME_BEEHIIV_PUBLICATION_ID", "")
CLAUDE_MODEL           = "claude-sonnet-4-5"


def validate():
    missing = [k for k, v in {
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "PLAYTIME_BEEHIIV_API_KEY": BEEHIIV_API_KEY,
        "PLAYTIME_BEEHIIV_PUBLICATION_ID": BEEHIIV_PUBLICATION_ID,
    }.items() if not v]
    if missing:
        raise EnvironmentError(f"Missing required env vars: {', '.join(missing)}")
