# Reddit Survey Scout

## 1. Project Overview

Build a Python application that continuously monitors Reddit for newly posted survey, research, focus-group, user-research, and participant-recruitment opportunities that may offer gift cards or other rewards.

The primary purpose is **opportunity discovery**.

The application should:

1. Monitor Reddit for new posts.
2. Search for configurable survey/research keywords.
3. Detect posts mentioning gift cards, rewards, incentives, or monetary compensation.
4. Filter out irrelevant posts as much as possible.
5. Avoid notifying the same Reddit post twice.
6. Send useful matching opportunities to a private Telegram chat.
7. Include the Reddit post title, subreddit, reward information when available, timestamp, and clickable Reddit URL.
8. Be easy to configure without modifying the source code.
9. Run continuously on a Windows computer.
10. Be designed so additional filtering/AI classification can be added later.

---

# 2. Important Scope

The bot is **NOT** intended to:

- Automatically complete surveys.
- Create fake Reddit accounts.
- Create fake survey accounts.
- Bypass survey eligibility requirements.
- Bypass geographic restrictions.
- Spam Reddit.
- Vote, comment, or interact with Reddit posts.
- Automatically claim rewards.

The bot only discovers publicly available opportunities and sends notifications to the owner.

---

# 3. Recommended Technology Stack

Use:

- Python 3.11+
- Reddit API through `PRAW`
- Telegram Bot API
- `python-dotenv`
- SQLite
- `requests`
- `logging`

Recommended project structure:

```text
reddit-survey-bot/
│
├── bot.py
├── reddit_monitor.py
├── telegram_notifier.py
├── database.py
├── filters.py
├── config.py
├── requirements.txt
├── .env
├── .env.example
├── .gitignore
├── README.md
├── PROJECT.md
│
├── data/
│   └── bot.db
│
└── logs/
    └── bot.log
```

Keep the architecture modular.

---

# 4. Environment Variables

Never hard-code credentials.

Create `.env.example`:

```env
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=reddit-survey-scout/1.0

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

CHECK_INTERVAL_SECONDS=60

MIN_MATCH_SCORE=5

ENABLE_REDDIT_SEARCH=true
ENABLE_SUBREDDIT_MONITORING=true
```

The real `.env` file must never be committed to Git.

---

# 5. Reddit Integration

Use PRAW.

The application should support Reddit OAuth/API credentials.

Required credentials:

```text
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT
```

The bot should use read-only Reddit functionality.

Do not perform actions such as:

```text
submit
comment
vote
subscribe
moderate
message
```

The Reddit integration should primarily retrieve new public posts.

---

# 6. Search Strategy

The user does NOT want country-specific Reddit searches.

Do NOT automatically append:

```text
Nigeria
Nigerian
Africa
```

to every search query.

Instead, search broadly for opportunities and let the user manually determine eligibility from the resulting post.

Primary search terms should include:

```text
survey gift
survey gift card
survey giftcard
paid survey
paid survey gift card
survey reward
survey rewards
survey incentive
survey compensation
paid study
paid research
research study gift card
research study reward
research participants gift card
gift card survey
gift card study
gift card research
gift card participants
paid interview
focus group
participants needed
participants wanted
looking for participants
recruiting participants
participant incentive
research incentive
study incentive
```

The search terms must be configurable.

Store them in a configuration file rather than hard-coding them throughout the application.

---

# 7. Reddit Sources

The application should support two discovery modes.

## Mode A — Reddit Search

Search Reddit using the configured keyword queries.

Example:

```text
survey gift card
```

Search should prioritize recent posts.

## Mode B — Subreddit Monitoring

Monitor selected subreddits for new posts.

Initial configurable subreddit list:

```text
SampleSize
beermoney
BeermoneyGlobal
paidstudy
UXResearch
```

Do not assume that every subreddit allows every type of post.

The application should simply monitor publicly available posts and respect Reddit/API limitations.

The subreddit list should be configurable.

---

# 8. Recency

The bot should prioritize new posts.

Default behavior:

```text
Check every 60 seconds.
```

When searching Reddit, use recent/new results where possible.

The bot should not repeatedly process very old posts.

Add configuration:

```env
MAX_POST_AGE_HOURS=24
```

Default:

```text
24
```

However, subreddit monitoring should primarily process posts that have appeared since the previous check.

---

# 9. Matching System

Do not simply notify on every occurrence of the word:

```text
gift
```

Instead implement a scoring system.

Example:

### Strong positive keywords

```text
gift card       +4
giftcard        +4
paid survey     +4
paid study      +4
paid research   +4
research study  +3
participant     +2
participants    +2
incentive       +2
reward          +2
compensation    +2
Amazon          +2
Visa             +2
PayPal           +2
focus group      +3
paid interview   +3
```

### Reward amount indicators

Examples:

```text
$10      +1
$20      +1
$25      +2
$50      +3
$75      +3
$100     +4
$150     +4
$200     +5
```

The scoring system should be configurable.

---

# 10. Negative Keywords

Reduce false positives using negative keywords.

Examples:

```text
homework
assignment
exam
class project
survey exchange
survey swap
karma
spam
mod application
```

Negative matches should subtract points or reject the post depending on severity.

For example:

```text
survey exchange -> reject
homework -> reject
assignment -> reject
```

Make this configurable.

---

# 11. Match Examples

### Example 1

Title:

```text
15-minute consumer research study - $50 Amazon Gift Card
```

Expected:

```text
HIGH MATCH
```

Possible score:

```text
research study +3
gift card +4
$50 +3
Amazon +2
```

Total:

```text
12
```

Send Telegram notification.

---

### Example 2

Title:

```text
Looking for participants for a 30-minute online study
```

Expected:

```text
MEDIUM MATCH
```

Because there is no obvious reward.

Depending on score, either:

- Notify
- Ignore

---

### Example 3

Title:

```text
Survey exchange - complete mine and I'll complete yours
```

Expected:

```text
REJECT
```

---

# 12. Duplicate Prevention

The bot must NEVER repeatedly send the same Reddit post.

Use SQLite.

Create a table similar to:

```sql
CREATE TABLE IF NOT EXISTS posts (
    reddit_id TEXT PRIMARY KEY,
    title TEXT,
    subreddit TEXT,
    url TEXT,
    score INTEGER,
    discovered_at TEXT,
    notified INTEGER DEFAULT 0
);
```

Before sending a notification:

```text
Check reddit_id
        ↓
Already exists?
        ↓
YES → Skip
NO  → Process
```

Reddit's unique post ID should be used as the primary duplicate identifier.

---

# 13. Telegram Integration

Use the Telegram Bot API.

Required:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

The bot should send notifications to the configured chat.

The notification should look approximately like:

```text
🔔 NEW SURVEY OPPORTUNITY

📌 15-Minute Consumer Research Study — $50 Amazon Gift Card

📂 r/SampleSize

💰 Reward:
$50 Amazon Gift Card

⏱ Posted:
3 minutes ago

🎯 Match Score:
12/10

🔗 Open Reddit Post
https://reddit.com/...

⚠️ Check the study's eligibility requirements before participating.
```

Do not fabricate reward information.

If the post doesn't clearly mention a reward:

```text
💰 Reward:
Not specified
```

---

# 14. Telegram Message Formatting

Use Telegram Markdown or HTML safely.

Escape user-generated Reddit text before inserting it into formatted Telegram messages.

Do not allow a Reddit post's content to break the Telegram message formatting.

Keep messages concise.

---

# 15. Reddit URL

Use the canonical Reddit URL whenever possible.

Example:

```text
https://www.reddit.com/r/SampleSize/comments/POST_ID/...
```

Make the Reddit post title clickable if Telegram formatting supports it.

---

# 16. Bot Startup

When the bot starts, display:

```text
Reddit Survey Scout started.

Monitoring:
- Reddit search
- Selected subreddits

Keywords:
XX

Check interval:
60 seconds

Minimum score:
5
```

Also send a Telegram startup message:

```text
🤖 Reddit Survey Scout is now online.

Monitoring new survey/research opportunities.
```

Make startup notification configurable.

---

# 17. Error Handling

The application must not crash because of a single failed Reddit request or Telegram request.

Handle:

- Reddit API errors
- Reddit rate limits
- Telegram API errors
- Network errors
- Invalid credentials
- Malformed Reddit posts
- Database errors
- Keyboard interruption

Use retry logic with reasonable delays.

Do not create an aggressive request loop.

---

# 18. Logging

Use Python's `logging` module.

Log:

```text
Bot startup
Reddit searches
Number of posts retrieved
Matched posts
Rejected posts
Duplicate posts
Telegram notifications
API errors
Database errors
Shutdown
```

Example:

```text
2026-09-07 15:30:12 INFO Reddit Survey Scout started
2026-09-07 15:30:13 INFO Searching Reddit for: survey gift card
2026-09-07 15:30:14 INFO Retrieved 25 posts
2026-09-07 15:30:14 INFO Match found: $50 Consumer Research Study
2026-09-07 15:30:15 INFO Telegram notification sent
```

Save logs to:

```text
logs/bot.log
```

---

# 19. Configuration

Create a centralized configuration system.

The user should be able to easily change:

```text
Search keywords
Subreddits
Minimum score
Check interval
Maximum post age
Negative keywords
Reward keywords
Telegram settings
```

Avoid requiring the user to modify Python source code for normal configuration.

---

# 20. Command-Line Interface

Provide useful commands.

Examples:

```bash
python bot.py
```

Optional:

```bash
python bot.py --test-telegram
python bot.py --test-reddit
python bot.py --once
```

`--test-telegram` should send a test message.

`--test-reddit` should verify Reddit credentials.

`--once` should perform one scan and exit.

---

# 21. Telegram Test

Implement:

```bash
python bot.py --test-telegram
```

Expected result:

```text
Telegram test successful.
```

And Telegram should receive:

```text
✅ Reddit Survey Scout Telegram connection is working.
```

---

# 22. Reddit Test

Implement:

```bash
python bot.py --test-reddit
```

Expected:

```text
Reddit connection successful.
```

---

# 23. One-Time Scan

Implement:

```bash
python bot.py --once
```

It should:

1. Connect to Reddit.
2. Search configured keywords.
3. Process posts.
4. Apply filters.
5. Send matching notifications.
6. Exit.

This makes debugging easier.

---

# 24. Future AI Classification

Design the code so an AI classifier can be added later.

Potential future pipeline:

```text
Reddit Post
    ↓
Keyword Filter
    ↓
Score
    ↓
AI Classification
    ↓
Eligibility/Relevance Analysis
    ↓
Telegram
```

The first version should NOT require an AI API.

Build a clean interface such as:

```python
class PostClassifier:
    def classify(self, post):
        ...
```

The initial implementation can use rule-based scoring.

Later, an LLM can replace or supplement the classifier.

---

# 25. Future Eligibility Detection

Eventually, the bot should be able to inspect a post and identify information such as:

```text
Countries accepted
Age requirements
Reward
Estimated completion time
Study type
Application link
Deadline
```

For example:

```text
🌍 Eligibility:
US, UK, Canada

❌ Likely not eligible from Nigeria
```

or:

```text
🌍 Eligibility:
Worldwide

✅ Potentially eligible
```

Important:

The first version should NOT claim that a user is eligible unless the post explicitly provides enough information.

Use:

```text
Potentially eligible
```

rather than:

```text
You are eligible
```

when uncertain.

---

# 26. Future Ranking

Eventually rank opportunities by attractiveness.

Potential factors:

```text
Reward amount
Time required
Gift card value
Study type
Eligibility
Deadline
Researcher reputation
```

Example:

```text
🔥 HIGH VALUE

$100 reward
20-minute study
Potentially international
```

But do not implement complicated ranking until the basic monitoring system works.

---

# 27. Security

Never expose:

```text
REDDIT_CLIENT_SECRET
REDDIT_CLIENT_ID
TELEGRAM_BOT_TOKEN
```

Do not print tokens to logs.

Add `.env` to `.gitignore`.

`.gitignore`:

```gitignore
.env
venv/
__pycache__/
*.pyc
data/*.db
logs/*.log
```

---

# 28. Requirements

Create `requirements.txt`.

At minimum:

```text
praw
python-dotenv
requests
```

Use versions compatible with the selected Python version.

---

# 29. Windows Compatibility

The application should work on Windows.

It should be possible to run:

```powershell
python bot.py
```

from PowerShell.

Provide setup instructions for:

1. Installing Python.
2. Creating a virtual environment.
3. Installing dependencies.
4. Creating Reddit API credentials.
5. Creating Telegram bot credentials.
6. Configuring `.env`.
7. Testing Reddit.
8. Testing Telegram.
9. Running the bot.

---

# 30. README

Create a complete `README.md`.

It should explain:

- What the project does.
- Features.
- Requirements.
- Installation.
- Reddit API setup.
- Telegram setup.
- Environment variables.
- Running the bot.
- Testing.
- Configuration.
- Troubleshooting.
- Project structure.

---

# 31. Development Approach

Build this incrementally.

### Phase 1

Create project structure.

### Phase 2

Implement configuration.

### Phase 3

Implement Reddit connection.

### Phase 4

Implement Reddit search.

### Phase 5

Implement keyword scoring.

### Phase 6

Implement SQLite duplicate detection.

### Phase 7

Implement Telegram notifications.

### Phase 8

Integrate everything.

### Phase 9

Add testing commands.

### Phase 10

Create documentation.

Do not over-engineer the first version.

---

# 32. Important UX Requirement

The Telegram notification should allow me to quickly decide whether an opportunity is worth opening.

Prioritize:

```text
Title
Reward
Subreddit
Match score
Time posted
Reddit link
```

The notification should not contain huge amounts of Reddit text.

---

# 33. Example Notification

```text
🎯 SURVEY SCOUT

📌 Consumer Research Study — 20 min

💰 $50 Amazon Gift Card

📂 r/SampleSize
🕐 Posted 4 minutes ago
⭐ Match Score: 11

🔗 View Study
https://www.reddit.com/...

⚠️ Verify eligibility and study requirements before participating.
```

---

# 34. Important Behavior

The goal is **high signal, not maximum notifications**.

It is better to miss a weak post than to send hundreds of irrelevant alerts.

However, make the threshold configurable:

```env
MIN_MATCH_SCORE=5
```

The user should be able to lower it if too many opportunities are being missed.

---

# 35. Final Acceptance Criteria

The project is considered complete when:

- [ ] Reddit API connection works.
- [ ] Telegram connection works.
- [ ] Configurable search queries work.
- [ ] Configurable subreddit monitoring works.
- [ ] New posts are detected.
- [ ] Posts are scored.
- [ ] Irrelevant posts are filtered.
- [ ] Duplicate posts are prevented.
- [ ] Telegram alerts are delivered.
- [ ] Reward information is extracted when available.
- [ ] Reddit URLs are included.
- [ ] Errors are logged.
- [ ] `.env` credentials are protected.
- [ ] `--test-telegram` works.
- [ ] `--test-reddit` works.
- [ ] `--once` works.
- [ ] Continuous monitoring works.
- [ ] README contains complete setup instructions.

---

# 36. Instruction to Claude

You are the lead developer for this project.

Build the application according to this specification.

Before writing substantial code:

1. Inspect the project directory.
2. Create the required project structure.
3. Explain briefly what you are going to implement.
4. Implement the project incrementally.
5. Keep credentials in `.env`.
6. Never hard-code API secrets.
7. Test each major component.
8. Fix errors rather than leaving TODO placeholders.
9. Keep the implementation simple and maintainable.
10. Do not add unnecessary frameworks.

The first objective is a **working Reddit → Telegram alert system**.

Do not implement AI classification, automatic survey completion, account automation, or eligibility bypassing in the first version.

After the basic version works, the project can be extended with smarter classification and opportunity ranking.