"""
Reddit Survey Scout - Main Bot Application
CLI entry point, orchestrator, and continuous monitoring loop.
"""

import argparse
import logging
import signal
import sys
import time
from typing import Optional

from config import config
from database import Database
from filters import RuleBasedClassifier, ClassificationResult
from healthcheck import start_health_server
from reddit_monitor import RedditMonitor
from telegram_notifier import TelegramNotifier


def setup_logging() -> None:
    """Configure dual-destination logging (console + logs/bot.log)."""
    log_format = "%(asctime)s %(levelname)s %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(log_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler
    file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)


logger = logging.getLogger(__name__)


class RedditSurveyScout:
    """Core scout orchestrator linking Reddit, Filters, Database, and Telegram."""

    def __init__(
        self,
        reddit_monitor: Optional[RedditMonitor] = None,
        telegram_notifier: Optional[TelegramNotifier] = None,
        classifier: Optional[RuleBasedClassifier] = None,
        db: Optional[Database] = None
    ):
        self.reddit = reddit_monitor or RedditMonitor()
        self.notifier = telegram_notifier or TelegramNotifier()
        self.classifier = classifier or RuleBasedClassifier()
        self.db = db or Database()
        self.running = False

    def print_startup_banner(self) -> None:
        """Display the required console startup banner (Section 16)."""
        monitoring_sources = []
        if config.enable_reddit_search:
            monitoring_sources.append("- Reddit search")
        if config.enable_subreddit_monitoring:
            monitoring_sources.append("- Selected subreddits")

        print("========================================")
        print("Reddit Survey Scout started.")
        print("")
        print("Monitoring:")
        for src in monitoring_sources:
            print(src)
        print("")
        print("Keywords:")
        print(f"{len(config.search_queries)} configured queries")
        print("")
        print("Subreddits:")
        print(", ".join(config.monitored_subreddits))
        print("")
        print(f"Check interval:\n{config.check_interval_seconds} seconds")
        print("")
        print(f"Minimum score:\n{config.min_match_score}")
        print("========================================")

    def process_posts(self) -> int:
        """
        Execute one discovery pass:
        Fetch, deduplicate, score, filter, and notify.
        Returns count of new matched opportunities alerted.
        """
        logger.info("Initiating scan for survey opportunities...")
        try:
            posts = self.reddit.fetch_all_new_posts()
        except Exception as e:
            logger.error("Error retrieving Reddit posts: %s", e)
            return 0

        logger.info("Retrieved %d total posts from Reddit", len(posts))
        matches_found = 0
        duplicates_count = 0
        rejected_count = 0

        for post in posts:
            post_id = post.get("id", "")
            title = post.get("title", "")
            subreddit = post.get("subreddit", "")
            url = post.get("url", "")

            # Duplicate prevention (Section 12)
            if self.db.is_post_seen(post_id):
                duplicates_count += 1
                logger.debug("Duplicate post skipped: [%s] %s", post_id, title)
                continue

            # Classify and score post
            result: ClassificationResult = self.classifier.classify(post)

            # Rejection handling
            if result.rejected:
                rejected_count += 1
                logger.info("Rejected post: %s (Reason: %s)", title, result.reject_reason)
                self.db.record_post(
                    reddit_id=post_id,
                    title=title,
                    subreddit=subreddit,
                    url=url,
                    score=result.score,
                    notified=False
                )
                continue

            # Check if post meets minimum score threshold
            if result.is_match:
                logger.info("Match found: %s (Score: %d, Reward: %s)", title, result.score, result.reward)
                # Send Telegram notification
                alert_sent = self.notifier.send_opportunity_alert(post, result)
                self.db.record_post(
                    reddit_id=post_id,
                    title=title,
                    subreddit=subreddit,
                    url=url,
                    score=result.score,
                    notified=alert_sent
                )
                matches_found += 1
            else:
                logger.debug("Post below score threshold (%d < %d): %s", result.score, config.min_match_score, title)
                # Store seen to avoid processing again
                self.db.record_post(
                    reddit_id=post_id,
                    title=title,
                    subreddit=subreddit,
                    url=url,
                    score=result.score,
                    notified=False
                )

        logger.info(
            "Scan complete. Found: %d matches alerted, %d rejected, %d duplicates skipped.",
            matches_found, rejected_count, duplicates_count
        )
        return matches_found

    def run_once(self) -> None:
        """Perform one scan pass and exit (Section 23)."""
        logger.info("Running Reddit Survey Scout in one-time mode (--once)")
        self.process_posts()

    def run(self) -> None:
        """Continuous execution loop with configurable interval (Section 8 & 16)."""
        self.running = True
        self.print_startup_banner()
        logger.info("Reddit Survey Scout started")

        # Start lightweight health-check server for cloud hosting (Render / Railway)
        if config.enable_healthcheck:
            start_health_server(port=config.port)

        # Send optional Telegram startup notification
        if config.send_startup_message and self.notifier.is_configured():
            self.notifier.send_startup_message()

        while self.running:
            try:
                self.process_posts()
            except Exception as e:
                logger.error("Unexpected error during monitoring cycle: %s", e, exc_info=True)

            logger.info("Sleeping for %d seconds until next scan...", config.check_interval_seconds)
            
            # Sleep in 1-second intervals to allow responsive Ctrl+C exit
            for _ in range(config.check_interval_seconds):
                if not self.running:
                    break
                time.sleep(1)

        logger.info("Reddit Survey Scout stopped")


def handle_signals(scout: RedditSurveyScout):
    """Set up graceful exit handlers for SIGINT and SIGTERM."""
    def _sig_handler(sig, frame):
        print("\nStopping Reddit Survey Scout gracefully...")
        scout.running = False

    signal.signal(signal.SIGINT, _sig_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sig_handler)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Reddit Survey Scout - Real-time survey and research opportunity monitor."
    )
    parser.add_argument(
        "--test-telegram",
        action="store_true",
        help="Verify Telegram credentials and send a test message."
    )
    parser.add_argument(
        "--test-reddit",
        action="store_true",
        help="Verify Reddit API credentials and connectivity."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Perform a single scan pass, notify matches, and exit."
    )

    args = parser.parse_args()
    setup_logging()

    scout = RedditSurveyScout()
    handle_signals(scout)

    # Command: --test-telegram (Section 21)
    if args.test_telegram:
        success, msg = scout.notifier.test_connection()
        if success:
            print("Telegram test successful.")
            sys.exit(0)
        else:
            print(f"Error: {msg}")
            sys.exit(1)

    # Command: --test-reddit (Section 22)
    if args.test_reddit:
        success, msg = scout.reddit.test_connection()
        if success:
            print("Reddit connection successful.")
            sys.exit(0)
        else:
            print(f"Error: {msg}")
            sys.exit(1)

    # Command: --once (Section 23)
    if args.once:
        scout.run_once()
        sys.exit(0)

    # Default: continuous monitoring
    scout.run()


if __name__ == "__main__":
    main()
