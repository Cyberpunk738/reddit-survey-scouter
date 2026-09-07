"""
Unit tests for filters.py: KeywordScorer, negative keyword rejection,
monetary bonuses, and reward string extraction.
"""

import pytest
from filters import RuleBasedClassifier


@pytest.fixture
def classifier():
    return RuleBasedClassifier(min_score=5)


def test_specification_example_1(classifier):
    """
    Section 11 Example 1:
    Title: '15-minute consumer research study - $50 Amazon Gift Card'
    Expected:
      research study (+3)
      gift card (+4)
      $50 (+3)
      Amazon (+2)
      Total = 12
      is_match = True
    """
    post = {
        "title": "15-minute consumer research study - $50 Amazon Gift Card",
        "selftext": ""
    }
    result = classifier.classify(post)

    assert not result.rejected
    assert result.is_match
    assert result.score == 12
    assert "gift card (+4)" in result.reasons
    assert "research study (+3)" in result.reasons
    assert "amazon (+2)" in result.reasons
    assert "$50 (+3)" in result.reasons
    assert "$50 Amazon Gift Card" in result.reward


def test_specification_example_2(classifier):
    """
    Section 11 Example 2:
    Title: 'Looking for participants for a 30-minute online study'
    Expected:
      participants (+2)
      Total = 2 (< 5)
      is_match = False
    """
    post = {
        "title": "Looking for participants for a 30-minute online study",
        "selftext": ""
    }
    result = classifier.classify(post)

    assert not result.rejected
    assert not result.is_match
    assert result.score == 2
    assert "participants (+2)" in result.reasons


def test_specification_example_3(classifier):
    """
    Section 11 Example 3:
    Title: 'Survey exchange - complete mine and I'll complete yours'
    Expected:
      REJECT
    """
    post = {
        "title": "Survey exchange - complete mine and I'll complete yours",
        "selftext": ""
    }
    result = classifier.classify(post)

    assert result.rejected
    assert not result.is_match
    assert "survey exchange" in result.reject_reason.lower()


def test_negative_keywords_homework(classifier):
    """Negative keywords like homework, assignment, exam must trigger rejection."""
    cases = [
        "Need participants for my college homework survey ($25 gift card)",
        "Quick assignment questionnaire for school project",
        "Exam preparation study feedback needed",
        "Survey swap please help with my graduation project",
        "Looking for karma on free survey subreddit",
        "Mod application open for survey community"
    ]
    for title in cases:
        result = classifier.classify({"title": title, "selftext": ""})
        assert result.rejected, f"Failed to reject post with title: {title}"
        assert not result.is_match


def test_monetary_scoring_tiers(classifier):
    """Verify tier calculations for monetary rewards."""
    # Test $100 -> +4
    res100 = classifier.classify({"title": "Paid survey for $100 reward", "selftext": ""})
    assert any("$100 (+4)" in r for r in res100.reasons)

    # Test $250 -> +5
    res250 = classifier.classify({"title": "Paid research $250 incentive", "selftext": ""})
    assert any("$250 (+5)" in r for r in res250.reasons)

    # Test $25 -> +2
    res25 = classifier.classify({"title": "Study participant $25 voucher", "selftext": ""})
    assert any("$25 (+2)" in r for r in res25.reasons)


def test_reward_description_fallback(classifier):
    """Verify reward description returns 'Not specified' when absent."""
    post = {
        "title": "Research study looking for participants to answer questions",
        "selftext": "Thank you for your time."
    }
    result = classifier.classify(post)
    assert result.reward == "Not specified"
