"""
shared/beehiiv_client.py — Shared Beehiiv API wrapper for all newsletters.

Each newsletter passes its own api_key and publication_id, so this single
client serves the entire media empire without any coupling.

Usage:
    from shared.beehiiv_client import BeehiivClient

    client = BeehiivClient(
        api_key=config.BEEHIIV_API_KEY,
        publication_id=config.BEEHIIV_PUBLICATION_ID,
    )
    post = client.create_post(subject="...", content_html="...", scheduled_at=dt)
"""

import requests
from datetime import datetime
from typing import Optional
import pytz


BEEHIIV_BASE_URL = "https://api.beehiiv.com/v2"


class BeehiivClient:
    def __init__(self, api_key: str, publication_id: str):
        if not api_key or not publication_id:
            raise ValueError("BeehiivClient requires both api_key and publication_id.")
        self.api_key = api_key
        self.publication_id = publication_id
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    # -----------------------------------------------------------------------
    # Posts
    # -----------------------------------------------------------------------

    def create_post(
        self,
        subject: str,
        content_html: str,
        preview_text: str = "",
        scheduled_at: Optional[datetime] = None,
        draft: bool = False,
        tags: Optional[list[str]] = None,
        send_hour_et: int = 7,
        send_minute_et: int = 0,
    ) -> dict:
        """
        Creates (and optionally schedules) a newsletter post.

        Args:
            subject:          Email subject line.
            content_html:     Full HTML body of the email.
            preview_text:     Preheader text shown in inbox previews.
            scheduled_at:     datetime to send. If None, calculated from send_hour_et/send_minute_et.
            draft:            If True, post is saved as draft (not confirmed for send).
            tags:             Optional list of content tags for categorization.
            send_hour_et:     Hour (24h, Eastern Time) to send if scheduled_at not given.
            send_minute_et:   Minute (0-59) to send — allows staggering newsletters.

        Returns:
            Full Beehiiv API response dict with post id, web_url, status, etc.
        """
        # Resolve send time
        status = "draft" if draft else "confirmed"
        send_ts: Optional[int] = None

        if not draft:
            if scheduled_at is None:
                scheduled_at = self._next_send_time(send_hour_et, send_minute_et)
            send_ts = int(scheduled_at.timestamp())

        payload: dict = {
            "publication_id": self.publication_id,
            "subject_line": subject,
            "preview_text": preview_text,
            "content_html": content_html,
            "status": status,
        }
        if send_ts:
            payload["scheduled_at"] = send_ts
        if tags:
            payload["content_tags"] = tags

        url = f"{BEEHIIV_BASE_URL}/publications/{self.publication_id}/posts"
        response = self.session.post(url, json=payload)
        self._raise_for_status(response)
        return response.json().get("data", response.json())

    def get_post(self, post_id: str) -> dict:
        """Fetches full details for a single post by ID."""
        url = f"{BEEHIIV_BASE_URL}/publications/{self.publication_id}/posts/{post_id}"
        response = self.session.get(url)
        self._raise_for_status(response)
        return response.json().get("data", response.json())

    def list_recent_posts(self, limit: int = 10) -> list[dict]:
        """Lists the most recent posts for this publication."""
        url = f"{BEEHIIV_BASE_URL}/publications/{self.publication_id}/posts"
        response = self.session.get(url, params={"limit": limit, "order_by": "created_at", "direction": "desc"})
        self._raise_for_status(response)
        return response.json().get("data", [])

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    def get_post_stats(self, post_id: str) -> dict:
        """
        Returns open rate, click rate, and other stats for a published post.
        NOTE: Stats are only available after a post has been sent.
        """
        post = self.get_post(post_id)
        stats = post.get("stats", {})
        return {
            "post_id": post_id,
            "subject_line": post.get("subject_line", ""),
            "recipients": stats.get("recipients", 0),
            "unique_opens": stats.get("unique_opens", 0),
            "open_rate": round(stats.get("open_rate", 0.0), 4),
            "unique_clicks": stats.get("unique_clicks", 0),
            "click_rate": round(stats.get("click_rate", 0.0), 4),
            "unsubscribes": stats.get("unsubscribes", 0),
            "sent_at": post.get("publish_date", ""),
        }

    def get_recent_stats(self, limit: int = 30) -> list[dict]:
        """
        Returns stats for the most recent `limit` sent posts.
        Used by the optimization engine for performance analysis.
        """
        posts = self.list_recent_posts(limit=limit)
        results = []
        for p in posts:
            if p.get("status") == "confirmed" and p.get("stats"):
                results.append(self.get_post_stats(p["id"]))
        return results

    # -----------------------------------------------------------------------
    # Publications
    # -----------------------------------------------------------------------

    def get_publication(self) -> dict:
        """Fetches metadata about this publication (subscriber count, etc.)."""
        url = f"{BEEHIIV_BASE_URL}/publications/{self.publication_id}"
        response = self.session.get(url)
        self._raise_for_status(response)
        return response.json().get("data", response.json())

    def get_subscriber_count(self) -> int:
        """Returns the active subscriber count for this publication."""
        pub = self.get_publication()
        return pub.get("active_subscriber_count", 0)

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _next_send_time(send_hour_et: int, send_minute_et: int = 0) -> datetime:
        """
        Returns the next occurrence of send_hour_et:send_minute_et in Eastern Time.
        If that time has already passed today, returns tomorrow's occurrence.
        """
        from datetime import timedelta
        et = pytz.timezone("America/New_York")
        now_et = datetime.now(et)
        target = now_et.replace(hour=send_hour_et, minute=send_minute_et, second=0, microsecond=0)
        if now_et >= target:
            target += timedelta(days=1)
        return target

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.status_code == 429:
            raise RuntimeError("Beehiiv rate limit hit (429). Wait and retry.")
        if response.status_code == 401:
            raise RuntimeError("Invalid Beehiiv API key (401). Check BEEHIIV_API_KEY.")
        if response.status_code == 403:
            raise RuntimeError(
                "Beehiiv access denied (403). Posts API requires Enterprise plan."
            )
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(f"Beehiiv API error {response.status_code}: {response.text}") from e
