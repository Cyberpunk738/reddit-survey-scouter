"""
Reddit Survey Scout - Scoring, Filtering & Reward Extraction Module
Implements rule-based opportunity scoring, negative filtering, reward detection,
and an extensible PostClassifier interface.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
import logging

from config import config

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Detailed outcome of post classification and scoring."""
    is_match: bool
    score: int
    reward: str
    reasons: List[str] = field(default_factory=list)
    rejected: bool = False
    reject_reason: Optional[str] = None


class BaseClassifier:
    """Base interface for post classification (extensible for future AI models)."""

    def classify(self, post: Dict[str, Any]) -> ClassificationResult:
        raise NotImplementedError("Subclasses must implement classify()")


class RuleBasedClassifier(BaseClassifier):
    """
    Rule-based opportunity scorer and negative filter.
    Scores posts based on positive keywords, reward amounts, and rejects false positives.
    """

    def __init__(
        self,
        min_score: Optional[int] = None,
        keyword_scores: Optional[Dict[str, int]] = None,
        reject_keywords: Optional[List[str]] = None
    ):
        self.min_score = min_score if min_score is not None else config.min_match_score
        self.keyword_scores = keyword_scores or config.keyword_scores
        self.reject_keywords = [k.lower() for k in (reject_keywords or config.reject_keywords)]

    def _extract_monetary_reward(self, text: str) -> Tuple[int, Optional[str], Optional[float]]:
        """
        Extract monetary amount and calculate score bonus.
        Returns (score_bonus, matched_string, numeric_value).
        """
        # Match currency amounts like $50, $50.00, £20, €15, 50 USD, etc.
        currency_pattern = re.compile(
            r'(?:[\$£€]\s*(\d+(?:\.\d{1,2})?)|(\d+(?:\.\d{1,2})?)\s*(?:USD|EUR|GBP|dollars?))',
            re.IGNORECASE
        )
        
        matches = currency_pattern.findall(text)
        if not matches:
            return 0, None, None

        highest_val = 0.0
        for m in matches:
            val_str = m[0] or m[1]
            try:
                val = float(val_str)
                if val > highest_val:
                    highest_val = val
            except ValueError:
                continue

        if highest_val <= 0:
            return 0, None, None

        # Determine points according to specification tiers
        if highest_val >= 200:
            points = 5
        elif highest_val >= 100:
            points = 4
        elif highest_val >= 50:
            points = 3
        elif highest_val >= 25:
            points = 2
        elif highest_val >= 10:
            points = 1
        else:
            points = 1

        formatted_amount = f"${highest_val:g}"
        return points, formatted_amount, highest_val

    def extract_reward_description(self, title: str, selftext: str = "") -> str:
        """
        Extract a human-friendly reward description from title and body.
        Defaults to 'Not specified' if no clear reward indicator is detected.
        """
        full_text = f"{title} {selftext}".strip()

        # Regex patterns for explicit reward phrases
        # e.g., "$50 Amazon Gift Card", "£20 PayPal voucher", "$100 cash", "Amazon giftcard ($25)"
        patterns = [
            # $50 Amazon Gift Card / $50 Visa / $25 PayPal
            r'([\$£€]\s*\d+(?:\.\d{1,2})?\s+(?:Amazon|Visa|PayPal|Mastercard|Apple|Target|Walmart)?\s*(?:gift\s*card|giftcard|voucher|cash|token)?)',
            # Amazon Gift Card ($50) / Gift Card ($20)
            r'((?:Amazon|Visa|PayPal|Mastercard|Apple|Target|Walmart)?\s*(?:gift\s*card|giftcard|voucher)\s*(?:\(\s*[\$£€]\s*\d+(?:\.\d{1,2})?\s*\)|\bfor\s*[\$£€]\s*\d+))',
            # Simple "$50 gift card"
            r'([\$£€]\s*\d+(?:\.\d{1,2})?\s+gift\s*card)',
            # Just dollar amount with mention of gift card or incentive nearby
            r'([\$£€]\s*\d+(?:\.\d{1,2})?)'
        ]

        # Prioritize matching in the title first
        for pat in patterns:
            match = re.search(pat, title, re.IGNORECASE)
            if match:
                reward_str = match.group(0).strip()
                # Clean up multiple whitespaces
                reward_str = re.sub(r'\s+', ' ', reward_str)
                # If only "$50" matched, check if gift card or brand is in title
                if re.match(r'^[\$£€]\s*\d+(?:\.\d{1,2})?$', reward_str):
                    brand_match = re.search(r'\b(Amazon|Visa|PayPal|Mastercard|Apple|Target|Walmart)\b', title, re.IGNORECASE)
                    gc_match = re.search(r'\b(gift\s*card|giftcard|voucher)\b', title, re.IGNORECASE)
                    additions = []
                    if brand_match:
                        additions.append(brand_match.group(0).capitalize())
                    if gc_match:
                        additions.append("Gift Card")
                    if additions:
                        reward_str = f"{reward_str} {' '.join(additions)}"
                return reward_str

        # If not in title, search selftext
        for pat in patterns:
            match = re.search(pat, selftext, re.IGNORECASE)
            if match:
                reward_str = match.group(0).strip()
                reward_str = re.sub(r'\s+', ' ', reward_str)
                return reward_str

        # Check for non-monetary or generic gift card mention
        gc_general = re.search(r'\b((?:Amazon|Visa|PayPal|Mastercard|Apple|Target|Walmart)?\s*(?:gift\s*card|giftcard|voucher))\b', title, re.IGNORECASE)
        if gc_general:
            return gc_general.group(0).strip().title()

        return "Not specified"

    def classify(self, post: Dict[str, Any]) -> ClassificationResult:
        """
        Evaluate a Reddit post dictionary and determine if it meets criteria.
        Expects post dictionary containing 'title' and optional 'selftext'.
        """
        title = post.get("title", "")
        selftext = post.get("selftext", "")
        combined_text = f"{title} {selftext}".lower()

        # Step 1: Check negative / rejection keywords
        for neg in self.reject_keywords:
            # Word boundary regex for clean matching
            pattern = rf'\b{re.escape(neg)}\b'
            if re.search(pattern, combined_text):
                logger.debug("Post '%s' rejected due to negative keyword: '%s'", title, neg)
                return ClassificationResult(
                    is_match=False,
                    score=0,
                    reward="Not specified",
                    reasons=[f"Negative keyword: {neg}"],
                    rejected=True,
                    reject_reason=f"Matched negative keyword '{neg}'"
                )

        score = 0
        reasons = []

        # Step 2: Positive keyword matching
        # Title matches carry higher confidence, but we check combined text
        for kw, weight in self.keyword_scores.items():
            pattern = rf'\b{re.escape(kw.lower())}\b'
            if re.search(pattern, combined_text):
                score += weight
                reasons.append(f"{kw} (+{weight})")

        # Step 3: Monetary reward indicators
        money_points, money_str, num_val = self._extract_monetary_reward(combined_text)
        if money_points > 0 and money_str:
            score += money_points
            reasons.append(f"{money_str} (+{money_points})")

        # Step 4: Extract friendly reward string
        reward = self.extract_reward_description(title, selftext)

        is_match = score >= self.min_score

        return ClassificationResult(
            is_match=is_match,
            score=score,
            reward=reward,
            reasons=reasons,
            rejected=False,
            reject_reason=None
        )


# Default classifier instance
default_classifier = RuleBasedClassifier()
