"""
Reddit Survey Scout - Reddit Monitor Module
Interacts with the Reddit API via PRAW in read-only mode to discover survey opportunities
through both global keyword search (Mode A) and subreddit monitoring (Mode B).
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import praw
from prawcore.exceptions import ResponseException, OAuthException, RequestException, PrawcoreException

from config import config

logger = logging.getLogger(__name__)


class RedditMonitor:
    """Handles Reddit API interactions in read-only mode."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        max_age_hours: Optional[int] = None
    ):
        self.client_id = client_id or config.reddit_client_id
        self.client_secret = client_secret or config.reddit_client_secret
        self.user_agent = user_agent or config.reddit_user_agent
        self.max_age_hours = max_age_hours if max_age_hours is not None else config.max_post_age_hours
        self._reddit: Optional[praw.Reddit] = None

    def is_configured(self) -> bool:
        """Verify if Reddit credentials have been provided."""
        return bool(
            self.client_id and self.client_secret and
            self.client_id != "your_reddit_client_id_here" and
            self.client_secret != "your_reddit_client_secret_here"
        )

    def get_reddit(self) -> praw.Reddit:
        """Instantiate or retrieve PRAW client instance in read-only mode."""
        if self._reddit is None:
            if not self.is_configured():
                raise ValueError("Reddit credentials missing or unconfigured in .env")
            self._reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            self._reddit.read_only = True
        return self._reddit

    def test_connection(self) -> Tuple[bool, str]:
        """
        Verify Reddit API credentials and network accessibility.
        Corresponds to Section 22: python bot.py --test-reddit
        """
        if not self.is_configured():
            return False, "Missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET in .env"

        try:
            r = self.get_reddit()
            # In read-only mode, verify by pulling 1 submission from r/test
            test_sub = r.subreddit("test")
            submissions = list(test_sub.new(limit=1))
            if submissions or test_sub.display_name:
                return True, "Reddit connection successful."
            return True, "Reddit connection successful."
        except OAuthException as e:
            return False, f"Reddit authentication failed: Invalid Client ID or Secret ({e})"
        except ResponseException as e:
            return False, f"Reddit API response error: {e}"
        except RequestException as e:
            return False, f"Reddit network request failed: {e}"
        except Exception as e:
            return False, f"Reddit connection failed: {e}"

    def _normalize_submission(self, submission) -> Dict[str, Any]:
        """Extract submission attributes into a standard dictionary."""
        return {
            "id": submission.id,
            "title": submission.title or "",
            "selftext": getattr(submission, "selftext", "") or "",
            "subreddit": str(submission.subreddit.display_name) if hasattr(submission, "subreddit") else "unknown",
            "url": submission.url or "",
            "permalink": submission.permalink or "",
            "created_utc": float(submission.created_utc) if hasattr(submission, "created_utc") else time.time(),
            "author": str(submission.author.name) if submission.author else "[deleted]"
        }

    def _is_post_too_old(self, created_utc: float) -> bool:
        """Check if post exceeds configured maximum age limit."""
        if self.max_age_hours <= 0:
            return False
        cutoff = time.time() - (self.max_age_hours * 3600)
        return created_utc < cutoff

    def fetch_search_posts(
        self,
        queries: Optional[List[str]] = None,
        limit_per_query: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Mode A: Search Reddit using configured queries sorted by 'new'.
        Filters out posts older than MAX_POST_AGE_HOURS.
        """
        queries = queries or config.search_queries
        results: Dict[str, Dict[str, Any]] = {}
        r = self.get_reddit()

        for query in queries:
            logger.info("Searching Reddit for: %s", query)
            try:
                # Search all of Reddit, sorted by newest
                time_filter = "day" if self.max_age_hours <= 24 else "week"
                submissions = r.subreddit("all").search(
                    query,
                    sort="new",
                    time_filter=time_filter,
                    limit=limit_per_query
                )
                
                count = 0
                for sub in submissions:
                    norm = self._normalize_submission(sub)
                    if self._is_post_too_old(norm["created_utc"]):
                        continue
                    if norm["id"] not in results:
                        results[norm["id"]] = norm
                    count += 1
                logger.debug("Query '%s' retrieved %d active posts", query, count)

                # Respectful brief pause between search queries
                time.sleep(1.0)
            except PrawcoreException as e:
                logger.error("Error executing Reddit search query '%s': %s", query, e)
                continue
            except Exception as e:
                logger.error("Unexpected error during Reddit search query '%s': %s", query, e)
                continue

        logger.info("Total unique posts found via search: %d", len(results))
        return list(results.values())

    def fetch_subreddit_posts(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Mode B: Stream or fetch recent submissions from monitored subreddits.
        """
        subreddits = subreddits or config.monitored_subreddits
        if not subreddits:
            return []

        r = self.get_reddit()
        joined_subs = "+".join(subreddits)
        logger.info("Checking subreddits: %s", joined_subs)
        results: Dict[str, Dict[str, Any]] = {}

        try:
            subreddit_instance = r.subreddit(joined_subs)
            for sub in subreddit_instance.new(limit=limit):
                norm = self._normalize_submission(sub)
                if self._is_post_too_old(norm["created_utc"]):
                    continue
                results[norm["id"]] = norm
        except PrawcoreException as e:
            logger.error("Error fetching recent posts from subreddits '%s': %s", joined_subs, e)
        except Exception as e:
            logger.error("Unexpected error fetching from subreddits '%s': %s", joined_subs, e)

        logger.info("Total unique posts retrieved from subreddits: %d", len(results))
        return list(results.values())

    def fetch_all_new_posts(self) -> List[Dict[str, Any]]:
        """
        Retrieve new posts across all enabled discovery modes (Search and/or Subreddits),
        deduplicating in-memory across the two sources.
        """
        if not self.is_configured():
            logger.warning("Reddit credentials not yet configured. Health check active, waiting for API keys...")
            return []

        combined: Dict[str, Dict[str, Any]] = {}

        # Mode A: Keyword Search
        if config.enable_reddit_search:
            search_posts = self.fetch_search_posts()
            for p in search_posts:
                combined[p["id"]] = p

        # Mode B: Subreddit Monitoring
        if config.enable_subreddit_monitoring:
            sub_posts = self.fetch_subreddit_posts()
            for p in sub_posts:
                combined[p["id"]] = p

        return list(combined.values())


# Global default monitor instance
default_monitor = RedditMonitor()
