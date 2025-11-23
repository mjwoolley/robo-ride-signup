# WCCC Ride Signup Agent - Feature Specification

## Architecture
- **Python LangChain Agent** with **Gemini 2.5** LLM
- **Playwright MCP Server** for browser automation (Chromium, visible)
- **LangSmith** for tracing and session review
- **Built-in Python scheduler** for hourly execution

---

## API Keys Setup

### 1. Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key → `GOOGLE_API_KEY`

### 2. LangSmith API Key
1. Go to [LangSmith](https://smith.langchain.com/)
2. Sign up/sign in
3. Go to Settings → API Keys
4. Create new API key → `LANGSMITH_API_KEY`

---

## Environment Variables (`.env`)
```
GOOGLE_API_KEY=your-gemini-key
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=wccc-ride-signup
LANGCHAIN_TRACING_V2=true
WCCC_USERNAME=your-username
WCCC_PASSWORD=your-password
PAGE_TIMEOUT_SECONDS=15
```

---

## Project Structure
```
src/
├── main.py           # Entry point with scheduler
├── agent.py          # LangChain agent with Gemini + MCP
├── config.py         # System prompt and configuration
└── logger.py         # Custom logger with screenshot links
logs/
├── screenshots/      # Screenshot files (timestamped)
└── run_YYYYMMDD_HHMMSS.log  # Log file per run
.env
.env.example
requirements.txt
feature_spec.md       # This file - feature tracking
```

---

## Features

### [x] Feature 1: Project Setup & Basic Agent
- Create Python project structure and virtual environment
- Install dependencies: `langchain`, `langchain-google-genai`, `langchain-mcp-adapters`, `langsmith`, `python-dotenv`, `schedule`
- Set up `.env`, `.env.example`, `requirements.txt`
- Create logging system with screenshot support (clickable file:// links)
- Create basic agent that connects to Gemini and Playwright MCP (Chromium, visible mode)
- **Validate**: Agent starts, takes screenshot, logs with clickable link
- **Commit**: "feat: initial Python project with Gemini agent, Playwright MCP, and logging"

### [x] Feature 2: Navigate to WCCC Site
- Agent navigates to WCCC homepage
- Screenshot and log confirmation
- **Validate**: Page loads, screenshot captured
- **Commit**: "feat: navigate to WCCC website"

### [x] Feature 3: Sign In
- Agent finds login form and enters credentials from env
- Implements retry logic: review page, retry up to 3 times, then log error with screenshots and stop
- **Validate**: Successfully logs in (verify logged-in state)
- **Commit**: "feat: sign in to WCCC with retry logic"

### [x] Feature 4: Navigate to Calendar Tab
- Agent clicks Calendar tab
- Screenshot calendar view
- **Validate**: Calendar page loads
- **Commit**: "feat: navigate to Calendar tab"

### [x] Feature 5: Find Target Ride
- Agent searches calendar for "B/B- Ride, Jenn"
- Date range: today through today + 10 days
- Screenshot search results
- **Validate**: Finds matching rides or logs "not found"
- **Commit**: "feat: search for target ride on calendar"

### [x] Feature 6: Check Registration & Register
- Agent checks registration status for each matching ride
- Registers for the next unregistered ride
- If already registered for first match, sign up for the next one
- Logs final status with screenshots
- **Validate**: Full registration flow completes
- **Commit**: "feat: check registration and register for next available ride"

### [x] Feature 7: Hourly Scheduler
- Add Python `schedule` library for hourly execution
- Runs agent every hour continuously
- **Validate**: Scheduler triggers agent correctly
- **Commit**: "feat: add hourly scheduler"

### [x] Feature 8: Configurable Ride Search Criteria
- Add `RIDE_SEARCH_TERM` environment variable
- Allow users to customize which ride to search for
- **Validate**: Agent uses search term from .env
- **Commit**: "feat: configurable ride search criteria via env var"

### [x] Feature 9: Auto-save Screenshots After Page Loads
- Take screenshot after every page navigation
- Use descriptive numbered filenames (e.g., "01_homepage.png", "02_login_form.png")
- Include log session in context for organized screenshots
- **Validate**: Screenshots saved with descriptive names after each step
- **Commit**: "feat: auto-save screenshots after each page load"

### [x] Feature 10: Debug Mode and Help
- Add `-d` / `--debug` flag for verbose AI response logging
- Add `-h` / `--help` flag for command line help (via argparse)
- Debug mode logs full conversation history and tool calls
- **Validate**: `python -m src.main -h` shows help, `-d` shows full AI interaction
- **Commit**: "feat: add debug mode for verbose AI response logging"

---

## Error Handling
- **Retry logic**: On failure, agent reviews current page state and retries (up to 3 attempts)
- **On final failure**: Capture screenshot, log detailed error info, stop execution
- **Page timeout**: Configurable via `PAGE_TIMEOUT_SECONDS` env var (default 15s)

## Logging
- Separate log file per run: `logs/run_YYYYMMDD_HHMMSS.log`
- Screenshots: `logs/screenshots/step_YYYYMMDD_HHMMSS.png`
- Clickable `file://` links to screenshots in log entries
- Console output mirrors log file
- LangSmith traces for full agent reasoning review

## Ride Search Logic
- Search date range: today → today + 10 days
- Find all rides matching `RIDE_SEARCH_TERM` (default: "B/B- Ride, Jenn")
- Check registration status for each in chronological order
- Register for first unregistered ride found
