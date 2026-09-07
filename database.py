"""
Reddit Survey Scout - SQLite Database Module
Handles persistence and duplicate post prevention.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Generator
import logging

from config import config

logger = logging.getLogger(__name__)


class Database:
    """SQLite wrapper for tracking discovered posts and duplicate prevention."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db_path
        self._ensure_dir()
        self.init_db()

    def _ensure_dir(self) -> None:
        """Ensure parent directory for database file exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Create and yield a database connection, ensuring it is closed afterward."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize the database tables if they do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    reddit_id TEXT PRIMARY KEY,
                    title TEXT,
                    subreddit TEXT,
                    url TEXT,
                    score INTEGER,
                    discovered_at TEXT,
                    notified INTEGER DEFAULT 0
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_discovered_at 
                ON posts(discovered_at);
            """)
            conn.commit()
            logger.debug("Database initialized at %s", self.db_path)

    def is_post_seen(self, reddit_id: str) -> bool:
        """
        Check if a Reddit post ID has already been recorded.
        Returns True if the post exists in the database.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM posts WHERE reddit_id = ? LIMIT 1;", (reddit_id,))
            return cursor.fetchone() is not None

    def record_post(
        self,
        reddit_id: str,
        title: str,
        subreddit: str,
        url: str,
        score: int = 0,
        notified: bool = False
    ) -> bool:
        """
        Record a newly discovered post into the database.
        Returns True if inserted, False if it was already present.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO posts (reddit_id, title, subreddit, url, score, discovered_at, notified)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (reddit_id, title, subreddit, url, score, now_utc, 1 if notified else 0))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Already exists
                return False

    def mark_notified(self, reddit_id: str) -> None:
        """Mark a post as notified."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET notified = 1 WHERE reddit_id = ?;", (reddit_id,))
            conn.commit()

    def get_post(self, reddit_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored post by reddit_id."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM posts WHERE reddit_id = ?;", (reddit_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_total_posts_count(self) -> int:
        """Return total count of recorded posts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posts;")
            return cursor.fetchone()[0]

    def get_notified_posts_count(self) -> int:
        """Return count of posts that triggered notifications."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posts WHERE notified = 1;")
            return cursor.fetchone()[0]
