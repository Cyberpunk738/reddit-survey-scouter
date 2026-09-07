"""
Reddit Survey Scout - Central Configuration Module
Loads environment variables and sets defaults for search, monitoring, scoring, and paths.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Load .env file from base directory
load_dotenv(BASE_DIR / ".env")


def get_bool_env(var_name: str, default: bool) -> bool:
    """Parse a boolean environment variable."""
    val = os.getenv(var_name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def get_int_env(var_name: str, default: int) -> int:
    """Parse an integer environment variable with fallback."""
    val = os.getenv(var_name)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


# Default search keyword queries (Section 6)
DEFAULT_SEARCH_QUERIES = [
    "survey gift",
    "survey gift card",
    "survey giftcard",
    "paid survey",
    "paid survey gift card",
    "survey reward",
    "survey rewards",
    "survey incentive",
    "survey compensation",
    "paid study",
    "paid research",
    "research study gift card",
    "research study reward",
    "research participants gift card",
    "gift card survey",
    "gift card study",
    "gift card research",
    "gift card participants",
    "paid interview",
    "focus group",
    "participants needed",
    "participants wanted",
    "looking for participants",
    "recruiting participants",
    "participant incentive",
    "research incentive",
    "study incentive",
]

# Default monitored subreddits (Section 7)
DEFAULT_SUBREDDITS = [
    "SampleSize",
    "beermoney",
    "BeermoneyGlobal",
    "paidstudy",
    "UXResearch",
]

# Positive keyword score weights (Section 9)
DEFAULT_KEYWORD_SCORES = {
    # High-intent reward & study indicators (+4)
    "gift card": 4,
    "giftcard": 4,
    "paid survey": 4,
    "paid study": 4,
    "paid research": 4,
    # Study formats (+3)
    "research study": 3,
    "focus group": 3,
    "paid interview": 3,
    # General positive indicators (+2)
    "participant": 2,
    "participants": 2,
    "incentive": 2,
    "reward": 2,
    "compensation": 2,
    "amazon": 2,
    "visa": 2,
    "paypal": 2,
}

# Hard rejection keywords (Section 10)
# Posts containing any of these phrases are automatically discarded
DEFAULT_REJECT_KEYWORDS = [
    "homework",
    "assignment",
    "exam",
    "class project",
    "survey exchange",
    "survey swap",
    "karma",
    "spam",
    "mod application",
]


@dataclass
class Config:
    """Application configuration holder."""
    # Paths
    base_dir: Path = BASE_DIR
    data_dir: Path = DATA_DIR
    logs_dir: Path = LOGS_DIR
    db_path: Path = DATA_DIR / "bot.db"
    log_file: Path = LOGS_DIR / "bot.log"

    # Reddit API
    reddit_client_id: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID", "").strip())
    reddit_client_secret: str = field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET", "").strip())
    reddit_user_agent: str = field(default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "reddit-survey-scout/1.0").strip())

    # Telegram Bot API
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", "").strip())
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", "").strip())

    # Monitoring parameters
    check_interval_seconds: int = field(default_factory=lambda: get_int_env("CHECK_INTERVAL_SECONDS", 60))
    min_match_score: int = field(default_factory=lambda: get_int_env("MIN_MATCH_SCORE", 5))
    max_post_age_hours: int = field(default_factory=lambda: get_int_env("MAX_POST_AGE_HOURS", 24))

    # Discovery toggles
    enable_reddit_search: bool = field(default_factory=lambda: get_bool_env("ENABLE_REDDIT_SEARCH", True))
    enable_subreddit_monitoring: bool = field(default_factory=lambda: get_bool_env("ENABLE_SUBREDDIT_MONITORING", True))
    send_startup_message: bool = field(default_factory=lambda: get_bool_env("SEND_STARTUP_MESSAGE", True))

    # Cloud Web Server & Health Check (for Render / Railway)
    port: int = field(default_factory=lambda: get_int_env("PORT", 10000))
    enable_healthcheck: bool = field(default_factory=lambda: get_bool_env("ENABLE_HEALTHCHECK", True))

    # Keywords and targets
    search_queries: List[str] = field(default_factory=lambda: DEFAULT_SEARCH_QUERIES)
    monitored_subreddits: List[str] = field(default_factory=lambda: DEFAULT_SUBREDDITS)
    keyword_scores: Dict[str, int] = field(default_factory=lambda: DEFAULT_KEYWORD_SCORES)
    reject_keywords: List[str] = field(default_factory=lambda: DEFAULT_REJECT_KEYWORDS)

    def validate_reddit_credentials(self) -> List[str]:
        """Check if Reddit credentials are configured."""
        missing = []
        if not self.reddit_client_id or self.reddit_client_id == "your_reddit_client_id_here":
            missing.append("REDDIT_CLIENT_ID")
        if not self.reddit_client_secret or self.reddit_client_secret == "your_reddit_client_secret_here":
            missing.append("REDDIT_CLIENT_SECRET")
        if not self.reddit_user_agent:
            missing.append("REDDIT_USER_AGENT")
        return missing

    def validate_telegram_credentials(self) -> List[str]:
        """Check if Telegram credentials are configured."""
        missing = []
        if not self.telegram_bot_token or self.telegram_bot_token == "your_telegram_bot_token_here":
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_chat_id or self.telegram_chat_id == "your_telegram_chat_id_here":
            missing.append("TELEGRAM_CHAT_ID")
        return missing


# Global default configuration instance
config = Config()
