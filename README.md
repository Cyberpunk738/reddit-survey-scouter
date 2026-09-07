# 🎯 Reddit Survey Scout

A modular, lightweight Python application that continuously monitors Reddit for newly posted surveys, research studies, focus groups, user interviews, and recruitment opportunities that offer gift cards, monetary incentives, or rewards.

Matching opportunities are scored, filtered against spam/false positives, deduplicated using an embedded SQLite database, and delivered in real-time to your private Telegram chat with clickable canonical links.

---

## ⚡ Features

- **Dual Discovery Modes**:
  - **Mode A (Global Reddit Search)**: Searches all of Reddit across dozens of configured query phrases (e.g. `survey gift card`, `paid research`, `focus group`, etc.).
  - **Mode B (Subreddit Stream)**: Monitors high-frequency subreddits (`r/SampleSize`, `r/beermoney`, `r/BeermoneyGlobal`, `r/paidstudy`, `r/UXResearch`).
- **Smart Opportunity Scoring**: Points system based on reward keywords and monetary values (e.g., $10, $25, $50, $100+).
- **False-Positive Rejection**: Automatically rejects homework, assignments, exams, karma farming, survey swaps/exchanges, and mod applications.
- **SQLite Deduplication**: Guarantees you never receive the same opportunity twice.
- **Clean Telegram Notifications**: Delivered via Telegram Bot API with post title, extracted reward, subreddit, match score, time posted, and a clickable Reddit link.
- **Resilient & Safe**: Automatic exponential backoff on network errors or rate limits; read-only Reddit access; HTML-safe message escaping.
- **Ready for AI**: Modular `PostClassifier` interface ready for LLM or AI-based ranking extensions.

---

## 📁 Project Structure

```text
Reddit Scouter/
├── bot.py                  # Main CLI entry point, scheduler, signal handler
├── config.py               # Central configuration, env parsing, keyword weights
├── database.py             # SQLite persistence for duplicate prevention
├── filters.py              # Rule-based scoring, negative filtering, reward extraction
├── reddit_monitor.py       # PRAW Reddit API client, search & subreddit streams
├── telegram_notifier.py    # Telegram Bot API client with safe formatting
├── requirements.txt        # Dependencies (praw, python-dotenv, requests, pytest)
├── .env.example            # Environment template
├── .gitignore              # Ignores credentials, database, logs, and venvs
├── README.md               # Documentation and Windows setup guide
├── PROJECT.md — ...        # Project specification
├── data/
│   └── bot.db              # SQLite duplicate database (auto-created)
├── logs/
│   └── bot.log             # Application log file (auto-created)
└── tests/                  # Unit and integration test suite
    ├── test_filters.py
    ├── test_database.py
    ├── test_telegram.py
    └── test_scout_flow.py
```

---

## 📋 Requirements

- **Operating System**: Windows 10/11 (also compatible with Linux / macOS)
- **Python**: Python 3.11+ (Python 3.14 supported)
- **Reddit Account**: For free API developer credentials
- **Telegram Account**: For bot creation and receiving alerts

---

## 🛠️ Setup Instructions (Windows)

### 1. Open PowerShell in the Project Directory

```powershell
cd "c:\Users\cyberdev\Desktop\Reddit Scouter"
```

### 2. (Optional) Create and Activate a Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

> **Note**: If PowerShell prevents script execution, run:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

### 3. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

---

## 🔑 Obtaining API Credentials

### Reddit API Setup

1. Log in to your Reddit account and navigate to: [https://www.reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
2. Scroll to the bottom and click **"are you a developer? create an app..."** (or **"create another app..."**).
3. Fill in the fields:
   - **name**: `reddit-survey-scout`
   - **type**: Select the **script** option (bubble next to `script`).
   - **description**: (Optional) `Scout surveys for gift cards`
   - **about url**: Leave blank or use `http://localhost`
   - **redirect uri**: `http://localhost:8080` (required by Reddit, but unused since this is a read-only script)
4. Click **"create app"**.
5. Note your credentials:
   - **Client ID**: The string of characters located immediately under the app name (e.g. `k8s9DJw02...`).
   - **Client Secret**: The value listed next to `secret`.

### Telegram Bot Setup

1. Open Telegram and search for `@BotFather`.
2. Start a chat and send `/newbot`.
3. Follow the prompts to name your bot and choose a username ending in `bot` (e.g. `MySurveyScoutBot`).
4. `@BotFather` will give you a **Bot API Token** (e.g. `7123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).
5. Next, find your personal **Chat ID**:
   - Start a chat with your newly created bot and click **Start** (send `/start`).
   - In Telegram, search for `@userinfobot` and send `/start`. It will reply with your numerical `Id` (e.g. `123456789`).

---

## ⚙️ Configuration (.env)

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` in your text editor and fill in your credentials:

```env
# Reddit API
REDDIT_CLIENT_ID=your_reddit_client_id_here
REDDIT_CLIENT_SECRET=your_reddit_client_secret_here
REDDIT_USER_AGENT=reddit-survey-scout/1.0 (by /u/your_reddit_username)

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Monitoring Intervals & Filters
CHECK_INTERVAL_SECONDS=60
MIN_MATCH_SCORE=5
MAX_POST_AGE_HOURS=24

# Features
ENABLE_REDDIT_SEARCH=true
ENABLE_SUBREDDIT_MONITORING=true
SEND_STARTUP_MESSAGE=true
```

---

## 🧪 Verification & Testing Commands

Before starting continuous monitoring, verify each integration using the built-in CLI flags:

### 1. Test Telegram Connection
Sends a test message directly to your Telegram chat:
```powershell
python bot.py --test-telegram
```
*Expected console output*: `Telegram test successful.`

### 2. Test Reddit API
Validates that Reddit Client ID & Secret can connect in read-only mode:
```powershell
python bot.py --test-reddit
```
*Expected console output*: `Reddit connection successful.`

### 3. Run a One-Time Scan
Performs a single complete discovery cycle (search + subreddit stream), filters, sends any matching alerts, and exits:
```powershell
python bot.py --once
```

### 4. Run Automated Test Suite
Run the full test suite (matching, rejection, deduplication, formatting):
```powershell
pytest -v
```

---

## 🚀 Running the Bot Continuously

To run continuous real-time monitoring on your computer:

```powershell
python bot.py
```

### What happens on startup:
1. Displays the startup configuration banner in console.
2. Sends an online confirmation message to your Telegram chat (if `SEND_STARTUP_MESSAGE=true`).
3. Fetches new posts every `CHECK_INTERVAL_SECONDS` (default: 60s).
4. Logs activity simultaneously to console and `logs/bot.log`.
5. To stop the bot cleanly, press `Ctrl + C`.

---

## ☁️ Deploying to Render (Free 24/7 Cloud Hosting)

You can run Reddit Survey Scout 24/7 on Render without keeping your PC powered on.

### 1. Push to GitHub
1. Create a new **Private Repository** on [GitHub](https://github.com/new).
2. Initialize git and push your project:
   ```powershell
   git init
   git add .
   git commit -m "Deploy Reddit Survey Scout"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git push -u origin main
   ```
   *(Note: `.env` is already in `.gitignore`, so your API secrets will never be uploaded to GitHub).*

### 2. Deploy on Render
1. Go to [Render.com](https://render.com) and log in.
2. Click **New +** > **Web Service**.
3. Connect your GitHub repository.
4. Render will automatically detect `render.yaml` or use these settings:
   - **Name**: `reddit-survey-scout`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: `Free`
5. Under **Environment Variables**, click **Add Environment Variable** and enter your credentials:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `CHECK_INTERVAL_SECONDS` = `60`
   - `MIN_MATCH_SCORE` = `5`
6. Click **Deploy Web Service**.

### 3. Keep It Running 24/7 (Prevent Render Sleep)
Because Render's free tier sleeps after 15 minutes if there is no traffic, the bot comes with a built-in health check server.
1. Copy your Render service URL (e.g. `https://reddit-survey-scout.onrender.com`).
2. Go to a free monitoring site like [UptimeRobot.com](https://uptimerobot.com) or [Cron-job.org](https://cron-job.org).
3. Create a free HTTP monitor:
   - **URL**: `https://reddit-survey-scout.onrender.com/health`
   - **Interval**: Every 10 minutes.
4. That's it! Render will stay awake and your bot will continuously scout Reddit and alert your Telegram chat 24 hours a day.

---

## 🔔 Sample Telegram Notification

```text
🎯 SURVEY SCOUT

📌 Consumer Research Study — 20 min

💰 Reward: $50 Amazon Gift Card
📂 r/SampleSize
⏱ Posted: 4 minutes ago
⭐ Match Score: 12 (threshold: 5)

🔗 View Reddit Post

⚠️ Verify eligibility and study requirements before participating.
```

---

## 🔧 Tuning Keywords & Scoring

You can tune default queries, monitored subreddits, scoring weights, or negative words without breaking code by editing `config.py`:

- **Search queries**: Modify `DEFAULT_SEARCH_QUERIES`.
- **Subreddits**: Modify `DEFAULT_SUBREDDITS`.
- **Positive scores**: Adjust weights in `DEFAULT_KEYWORD_SCORES`.
- **Reject keywords**: Add or remove terms from `DEFAULT_REJECT_KEYWORDS`.
- **Threshold**: Adjust `MIN_MATCH_SCORE` in `.env` (lower if you want more alerts, raise for higher exclusivity).

---

## ❓ Troubleshooting

| Issue | Resolution |
|---|---|
| `Telegram API error: Unauthorized` | Double check `TELEGRAM_BOT_TOKEN` in `.env`. Ensure there are no spaces or quotes around the token. |
| `Telegram API error: Chat not found` | Make sure you started your bot in Telegram first by opening it and clicking `/start`. Also verify `TELEGRAM_CHAT_ID`. |
| `OAuthException: Invalid Client ID or Secret` | Check your Reddit app credentials at `reddit.com/prefs/apps`. Ensure the app type is `script`. |
| `Duplicate post skipped` | Working as intended! The SQLite database in `data/bot.db` records every post seen to prevent repeat alerts. |
| `No matches found` | Reddit posts may not currently meet the score threshold (`MIN_MATCH_SCORE=5`). You can temporarily lower it in `.env` to test. |
#
