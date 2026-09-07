"""
Reddit Survey Scout - Telegram Notifier Module
Handles formatting and dispatching opportunity alerts and test messages to Telegram.
"""

import html
import logging
import time
from typing import Dict, Any, Tuple, Optional
import requests

from config import config
from filters import ClassificationResult

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notification alerts via Telegram Bot API using safe HTML formatting."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: int = 15
    ):
        self.bot_token = bot_token or config.telegram_bot_token
        self.chat_id = chat_id or config.telegram_chat_id
        self.timeout = timeout
        self.api_base = f"https://api.telegram.org/bot{self.bot_token}"

    def is_configured(self) -> bool:
        """Check if bot token and chat ID are present."""
        return bool(self.bot_token and self.chat_id and 
                    self.bot_token != "your_telegram_bot_token_here" and
                    self.chat_id != "your_telegram_chat_id_here")

    def _post(self, endpoint: str, payload: dict, retries: int = 3) -> Tuple[bool, Optional[str]]:
        """Send a POST request to Telegram API with exponential backoff on transient errors."""
        if not self.is_configured():
            return False, "Telegram credentials not configured in .env"

        url = f"{self.api_base}/{endpoint}"

        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(url, json=payload, timeout=self.timeout)
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}

                if resp.status_code == 200 and data.get("ok"):
                    return True, None

                # Handle rate limiting from Telegram (HTTP 429)
                if resp.status_code == 429:
                    retry_after = data.get("parameters", {}).get("retry_after", attempt * 3)
                    logger.warning("Telegram rate limit hit. Sleeping for %d seconds...", retry_after)
                    time.sleep(retry_after)
                    continue

                error_desc = data.get("description", f"HTTP {resp.status_code} {resp.text}")
                logger.error("Telegram API error: %s", error_desc)

                # Client-side configuration error (invalid token or chat not found) - do not retry
                if resp.status_code in (400, 401, 404):
                    return False, error_desc

            except requests.exceptions.RequestException as e:
                logger.warning("Telegram network error on attempt %d/%d: %s", attempt, retries, e)
                if attempt < retries:
                    time.sleep(attempt * 2)
                else:
                    return False, str(e)

        return False, "Failed after multiple retry attempts"

    def send_raw_message(self, text: str, parse_mode: str = "HTML") -> Tuple[bool, Optional[str]]:
        """Send a text message directly to the configured Telegram chat."""
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False
        }
        return self._post("sendMessage", payload)

    def test_connection(self) -> Tuple[bool, str]:
        """
        Verify Telegram credentials and send a test message.
        Corresponds to Section 21: python bot.py --test-telegram
        """
        if not self.is_configured():
            return False, "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env"

        test_msg = "✅ <b>Reddit Survey Scout</b> Telegram connection is working."
        success, err = self.send_raw_message(test_msg)
        if success:
            return True, "Telegram test successful."
        return False, f"Telegram test failed: {err}"

    def send_startup_message(self) -> Tuple[bool, Optional[str]]:
        """Send the official startup notification to Telegram (Section 16)."""
        msg = (
            "🤖 <b>Reddit Survey Scout is now online.</b>\n\n"
            "Monitoring new survey/research opportunities."
        )
        return self.send_raw_message(msg)

    def format_time_ago(self, created_utc: Optional[float]) -> str:
        """Format UTC timestamp to readable 'X minutes ago' or 'X hours ago'."""
        if not created_utc:
            return "recently"
        now = time.time()
        diff_seconds = max(0, int(now - created_utc))
        if diff_seconds < 60:
            return f"{diff_seconds} seconds ago"
        diff_minutes = diff_seconds // 60
        if diff_minutes < 60:
            return f"{diff_minutes} minute{'s' if diff_minutes != 1 else ''} ago"
        diff_hours = diff_minutes // 60
        if diff_hours < 24:
            return f"{diff_hours} hour{'s' if diff_hours != 1 else ''} ago"
        diff_days = diff_hours // 24
        return f"{diff_days} day{'s' if diff_days != 1 else ''} ago"

    def format_opportunity_message(
        self,
        post: Dict[str, Any],
        classification: ClassificationResult
    ) -> str:
        """
        Format matching opportunity according to Section 13 & 33 specifications:
        🎯 SURVEY SCOUT
        📌 Title (clickable link)
        💰 Reward: ...
        📂 r/Subreddit
        ⏱ Posted X minutes ago
        ⭐ Match Score: X
        🔗 View Study: url
        ⚠️ Verify eligibility and study requirements before participating.
        """
        title = html.escape(post.get("title", "Untitled Post"))
        subreddit = html.escape(post.get("subreddit", "unknown"))
        url = post.get("url", "")
        permalink = post.get("permalink", "")

        # Use canonical Reddit URL if available
        if permalink and not permalink.startswith("http"):
            reddit_link = f"https://www.reddit.com{permalink}"
        elif url and "reddit.com" in url:
            reddit_link = url
        elif permalink:
            reddit_link = permalink
        else:
            reddit_link = url

        reward = html.escape(classification.reward)
        posted_ago = self.format_time_ago(post.get("created_utc"))
        score = classification.score
        min_score = config.min_match_score

        # Clickable title leading to Reddit post
        msg = (
            "🎯 <b>SURVEY SCOUT</b>\n\n"
            f"📌 <a href=\"{reddit_link}\"><b>{title}</b></a>\n\n"
            f"💰 <b>Reward:</b> {reward}\n"
            f"📂 <b>r/{subreddit}</b>\n"
            f"⏱ <b>Posted:</b> {posted_ago}\n"
            f"⭐ <b>Match Score:</b> {score} (threshold: {min_score})\n\n"
            f"🔗 <a href=\"{reddit_link}\">View Reddit Post</a>\n\n"
            "⚠️ <i>Verify eligibility and study requirements before participating.</i>"
        )
        return msg

    def send_opportunity_alert(
        self,
        post: Dict[str, Any],
        classification: ClassificationResult
    ) -> bool:
        """Send formatted survey alert for a matched post."""
        message = self.format_opportunity_message(post, classification)
        success, error = self.send_raw_message(message)
        if success:
            logger.info("Telegram notification sent for post %s", post.get("id"))
            return True
        else:
            logger.error("Failed to send Telegram notification for %s: %s", post.get("id"), error)
            return False


# Global default notifier instance
default_notifier = TelegramNotifier()
