"""
End-to-end orchestration unit tests with mocked Reddit and Telegram services.
"""

import time
from unittest.mock import MagicMock
from bot import RedditSurveyScout
from database import Database
from filters import RuleBasedClassifier


def test_process_posts_orchestration(tmp_path):
    # Setup isolated test database
    db = Database(db_path=tmp_path / "test_flow.db")

    # Mock Reddit monitor
    mock_reddit = MagicMock()
    mock_reddit.fetch_all_new_posts.return_value = [
        {
            "id": "post_1",
            "title": "15-minute consumer research study - $50 Amazon Gift Card",
            "selftext": "Please participate in our consumer study.",
            "subreddit": "SampleSize",
            "url": "https://reddit.com/r/SampleSize/comments/post_1",
            "permalink": "/r/SampleSize/comments/post_1",
            "created_utc": time.time() - 300,
            "author": "researcher_1"
        },
        {
            "id": "post_2",
            "title": "Survey exchange for university homework",
            "selftext": "Help me with my homework survey exchange.",
            "subreddit": "SampleSize",
            "url": "https://reddit.com/r/SampleSize/comments/post_2",
            "permalink": "/r/SampleSize/comments/post_2",
            "created_utc": time.time() - 100,
            "author": "student_1"
        },
        {
            "id": "post_3",
            "title": "Quick survey about daily habits",
            "selftext": "No reward, just 5 questions.",
            "subreddit": "SampleSize",
            "url": "https://reddit.com/r/SampleSize/comments/post_3",
            "permalink": "/r/SampleSize/comments/post_3",
            "created_utc": time.time() - 50,
            "author": "casual_user"
        }
    ]

    # Mock Telegram notifier
    mock_notifier = MagicMock()
    mock_notifier.send_opportunity_alert.return_value = True

    classifier = RuleBasedClassifier(min_score=5)
    scout = RedditSurveyScout(
        reddit_monitor=mock_reddit,
        telegram_notifier=mock_notifier,
        classifier=classifier,
        db=db
    )

    # First run
    alerted = scout.process_posts()
    assert alerted == 1
    mock_notifier.send_opportunity_alert.assert_called_once()
    assert db.is_post_seen("post_1")
    assert db.is_post_seen("post_2")
    assert db.is_post_seen("post_3")

    post_1_record = db.get_post("post_1")
    assert post_1_record["notified"] == 1

    post_2_record = db.get_post("post_2")
    assert post_2_record["notified"] == 0

    post_3_record = db.get_post("post_3")
    assert post_3_record["notified"] == 0

    # Second run should skip all duplicates
    mock_notifier.reset_mock()
    alerted_second_run = scout.process_posts()
    assert alerted_second_run == 0
    mock_notifier.send_opportunity_alert.assert_not_called()
