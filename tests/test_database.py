"""
Unit tests for database.py: SQLite schema, deduplication, and notification marking.
"""

import tempfile
from pathlib import Path
import pytest
from database import Database


@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_bot.db"
        db = Database(db_path=db_path)
        yield db


def test_initial_db_empty(temp_db):
    assert temp_db.get_total_posts_count() == 0
    assert not temp_db.is_post_seen("nonexistent_id")


def test_record_and_deduplicate(temp_db):
    # Insert first time
    inserted = temp_db.record_post(
        reddit_id="t3_abc123",
        title="Test Survey Post",
        subreddit="SampleSize",
        url="https://reddit.com/r/SampleSize/comments/abc123",
        score=10,
        notified=True
    )
    assert inserted is True
    assert temp_db.is_post_seen("t3_abc123") is True
    assert temp_db.get_total_posts_count() == 1
    assert temp_db.get_notified_posts_count() == 1

    # Insert duplicate
    duplicate_inserted = temp_db.record_post(
        reddit_id="t3_abc123",
        title="Duplicate Post",
        subreddit="SampleSize",
        url="https://reddit.com/r/SampleSize/comments/abc123",
        score=10,
        notified=True
    )
    assert duplicate_inserted is False
    assert temp_db.get_total_posts_count() == 1


def test_mark_notified(temp_db):
    temp_db.record_post(
        reddit_id="t3_unnotified",
        title="Unnotified Post",
        subreddit="beermoney",
        url="https://reddit.com/r/beermoney/comments/unnotified",
        score=8,
        notified=False
    )
    assert temp_db.get_notified_posts_count() == 0

    temp_db.mark_notified("t3_unnotified")
    assert temp_db.get_notified_posts_count() == 1

    post = temp_db.get_post("t3_unnotified")
    assert post is not None
    assert post["notified"] == 1
    assert post["reddit_id"] == "t3_unnotified"
