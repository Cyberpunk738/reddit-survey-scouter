"""
Unit tests for telegram_notifier.py: HTML safety, message layout, and relative time formatting.
"""

import time
from filters import ClassificationResult
from telegram_notifier import TelegramNotifier


def test_format_time_ago():
    notifier = TelegramNotifier()
    now = time.time()

    assert "second" in notifier.format_time_ago(now - 10)
    assert "minute" in notifier.format_time_ago(now - 180)
    assert "hour" in notifier.format_time_ago(now - 7200)
    assert "day" in notifier.format_time_ago(now - 100000)


def test_html_escaping_in_message():
    notifier = TelegramNotifier()
    raw_post = {
        "id": "t3_test",
        "title": "<script>alert('pwned')</script> & Focus Group",
        "subreddit": "SampleSize <safe>",
        "url": "https://www.reddit.com/r/SampleSize/comments/t3_test",
        "permalink": "/r/SampleSize/comments/t3_test",
        "created_utc": time.time() - 120
    }
    classification = ClassificationResult(
        is_match=True,
        score=11,
        reward="$50 <Gift Card> & Cash",
        reasons=["focus group (+3)", "$50 (+3)"]
    )

    formatted = notifier.format_opportunity_message(raw_post, classification)

    # HTML tags must be properly escaped
    assert "<script>" not in formatted
    assert "&lt;script&gt;alert(&#x27;pwned&#x27;)&lt;/script&gt; &amp; Focus Group" in formatted
    assert "&lt;Gift Card&gt; &amp; Cash" in formatted
    assert "<b>SURVEY SCOUT</b>" in formatted
    assert "View Reddit Post" in formatted
