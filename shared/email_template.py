"""
shared/email_template.py — Base HTML email template for all newsletters.

Each newsletter passes its own NewsletterTheme to customize colors, fonts,
name, and tagline. The structure and responsive layout are shared.

Usage:
    from shared.email_template import build_email_html, NewsletterTheme

    theme = NewsletterTheme(
        name="Silver & Cents",
        tagline="Daily money moves for the golden years",
        primary_color="#1B2A4A",
        accent_color="#C9A84C",
        bg_color="#FDF6E3",
    )
    html = build_email_html(content=generated_content, theme=theme)
"""

from dataclasses import dataclass, field
from datetime import date


# ---------------------------------------------------------------------------
# Theme dataclass — one per newsletter
# ---------------------------------------------------------------------------

@dataclass
class NewsletterTheme:
    name: str
    tagline: str
    primary_color: str          # Header background, CTA buttons
    accent_color: str           # Borders, highlights, links
    bg_color: str               # Light section backgrounds
    text_dark: str = "#222222"
    text_medium: str = "#555555"
    font_family: str = "Georgia, 'Times New Roman', serif"
    body_font_size: str = "17px"
    logo_emoji: str = ""        # Optional emoji as logo fallback


# ---------------------------------------------------------------------------
# Pre-built themes for each newsletter
# ---------------------------------------------------------------------------

SILVER_AND_CENTS = NewsletterTheme(
    name="Silver & Cents",
    tagline="Daily money moves for the golden years",
    primary_color="#1B2A4A",    # Navy
    accent_color="#C9A84C",     # Gold
    bg_color="#FDF6E3",         # Light parchment
    logo_emoji="💰",
)

DAILY_STEALS = NewsletterTheme(
    name="Daily Steals",
    tagline="The best deals of the day — straight to your inbox",
    primary_color="#B91C1C",    # Bold red
    accent_color="#F59E0B",     # Amber
    bg_color="#FFF7ED",         # Warm cream
    font_family="Arial, Helvetica, sans-serif",
    body_font_size="16px",
    logo_emoji="🔥",
)

PLAYTIME = NewsletterTheme(
    name="Playtime",
    tagline="Games, fun, and entertainment — every single day",
    primary_color="#4F46E5",    # Indigo
    accent_color="#EC4899",     # Pink
    bg_color="#F5F3FF",         # Lavender tint
    font_family="Arial, Helvetica, sans-serif",
    body_font_size="16px",
    logo_emoji="🎮",
)

PEAK_HEALTH = NewsletterTheme(
    name="Peak Health",
    tagline="Science-backed wellness for a longer, stronger life",
    primary_color="#065F46",    # Forest green
    accent_color="#10B981",     # Emerald
    bg_color="#ECFDF5",         # Mint tint
    font_family="Arial, Helvetica, sans-serif",
    body_font_size="16px",
    logo_emoji="🌿",
)

MONEY_IQ = NewsletterTheme(
    name="Money IQ",
    tagline="Sharp personal finance for ambitious adults",
    primary_color="#1E3A5F",    # Dark blue
    accent_color="#3B82F6",     # Bright blue
    bg_color="#EFF6FF",         # Ice blue tint
    font_family="Arial, Helvetica, sans-serif",
    body_font_size="16px",
    logo_emoji="📈",
)

THEMES = {
    "silver-and-cents": SILVER_AND_CENTS,
    "daily-steals": DAILY_STEALS,
    "playtime": PLAYTIME,
    "peak-health": PEAK_HEALTH,
    "money-iq": MONEY_IQ,
}


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def build_email_html(content: dict, theme: NewsletterTheme) -> str:
    """
    Builds a full responsive HTML email from generated content and a theme.

    Args:
        content: Dict returned by content_generator (keys vary by newsletter).
                 Expected keys: hook, main_story, quick_hits (list),
                 sponsor_placeholder, money_move, signoff, title.
        theme:   NewsletterTheme instance for this newsletter.

    Returns:
        Complete HTML string ready to post to Beehiiv.
    """
    today_str = date.today().strftime("%B %d, %Y")

    hook         = content.get("hook", "")
    main_story   = content.get("main_story", "")
    quick_hits   = content.get("quick_hits", [])
    sponsor      = content.get("sponsor_placeholder", "")
    money_move   = content.get("money_move", "")
    signoff      = content.get("signoff", "")
    title        = content.get("title", theme.name)
    cta_url      = content.get("cta_url", "#")
    cta_text     = content.get("cta_text", "Learn more →")

    # Quick hits as HTML list items
    hits_html = "\n".join(
        f'<li style="margin-bottom:10px;font-size:15px;color:{theme.text_dark};">{hit}</li>'
        for hit in quick_hits
    )

    logo_html = (
        f'<span style="font-size:36px;">{theme.logo_emoji}</span><br>'
        if theme.logo_emoji else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;font-family:{theme.font_family};">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f4f4f4;">
<tr><td align="center" style="padding:20px 10px;">

<!-- OUTER CONTAINER -->
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

  <!-- HEADER -->
  <tr>
    <td style="background-color:{theme.primary_color};padding:28px 32px;text-align:center;">
      {logo_html}
      <h1 style="margin:0;color:#ffffff;font-size:28px;font-weight:bold;letter-spacing:1px;font-family:{theme.font_family};">
        {theme.name.upper()}
      </h1>
      <p style="margin:6px 0 0;color:{theme.accent_color};font-size:13px;letter-spacing:1.5px;text-transform:uppercase;font-family:Arial,sans-serif;">
        {theme.tagline}
      </p>
      <p style="margin:10px 0 0;color:rgba(255,255,255,0.6);font-size:12px;font-family:Arial,sans-serif;">
        {today_str}
      </p>
    </td>
  </tr>

  <!-- HOOK -->
  <tr>
    <td style="padding:28px 32px 12px;border-bottom:2px solid {theme.accent_color};">
      <p style="margin:0;font-size:18px;line-height:1.6;color:{theme.text_dark};font-style:italic;font-family:{theme.font_family};">
        {hook}
      </p>
    </td>
  </tr>

  <!-- MAIN STORY -->
  <tr>
    <td style="padding:24px 32px;">
      <p style="margin:0;font-size:{theme.body_font_size};line-height:1.75;color:{theme.text_dark};font-family:{theme.font_family};">
        {main_story.replace(chr(10), '<br><br>')}
      </p>
    </td>
  </tr>

  <!-- QUICK HITS -->
  <tr>
    <td style="padding:0 32px 24px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0"
             style="background-color:{theme.bg_color};border-left:4px solid {theme.accent_color};border-radius:4px;">
        <tr>
          <td style="padding:18px 20px;">
            <p style="margin:0 0 10px;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{theme.accent_color};font-weight:bold;font-family:Arial,sans-serif;">
              Quick Hits
            </p>
            <ul style="margin:0;padding-left:18px;">
              {hits_html}
            </ul>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- SPONSOR / NATIVE AD -->
  <tr>
    <td style="background-color:{theme.primary_color};padding:22px 32px;">
      <p style="margin:0 0 6px;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:rgba(255,255,255,0.5);font-family:Arial,sans-serif;">
        Sponsored
      </p>
      <p style="margin:0;font-size:15px;line-height:1.65;color:#ffffff;font-family:{theme.font_family};">
        {sponsor}
      </p>
    </td>
  </tr>

  <!-- MONEY MOVE / CTA -->
  <tr>
    <td style="padding:24px 32px;border-left:4px solid {theme.accent_color};">
      <p style="margin:0 0 14px;font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{theme.accent_color};font-weight:bold;font-family:Arial,sans-serif;">
        Today's Action
      </p>
      <p style="margin:0 0 18px;font-size:{theme.body_font_size};line-height:1.65;color:{theme.text_dark};font-family:{theme.font_family};">
        {money_move}
      </p>
      <a href="{cta_url}"
         style="display:inline-block;background-color:{theme.primary_color};color:#ffffff;padding:12px 24px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:bold;font-family:Arial,sans-serif;">
        {cta_text}
      </a>
    </td>
  </tr>

  <!-- SIGN-OFF -->
  <tr>
    <td style="padding:20px 32px 28px;border-top:1px solid #eeeeee;">
      <p style="margin:0;font-size:15px;line-height:1.65;color:{theme.text_medium};font-family:{theme.font_family};">
        {signoff}
      </p>
    </td>
  </tr>

  <!-- FOOTER -->
  <tr>
    <td style="background-color:#f9f9f9;padding:16px 32px;text-align:center;border-top:1px solid #eeeeee;">
      <p style="margin:0;font-size:11px;color:#aaaaaa;font-family:Arial,sans-serif;">
        You're receiving this because you subscribed to {theme.name}.<br>
        <a href="{{{{unsubscribe_url}}}}" style="color:#aaaaaa;text-decoration:underline;">Unsubscribe</a>
        &nbsp;·&nbsp;
        <a href="{{{{browser_url}}}}" style="color:#aaaaaa;text-decoration:underline;">View in browser</a>
      </p>
      <p style="margin:8px 0 0;font-size:10px;color:#cccccc;font-family:Arial,sans-serif;">
        This email is for informational purposes only and does not constitute financial advice.
      </p>
    </td>
  </tr>

</table>
<!-- END OUTER CONTAINER -->

</td></tr>
</table>
</body>
</html>"""


def get_theme(newsletter_name: str) -> NewsletterTheme:
    """Returns the theme for a newsletter by its directory name."""
    theme = THEMES.get(newsletter_name)
    if not theme:
        raise ValueError(
            f"No theme found for '{newsletter_name}'. "
            f"Available: {list(THEMES.keys())}"
        )
    return theme
