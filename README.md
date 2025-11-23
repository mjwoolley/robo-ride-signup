# WCCC Ride Signup Agent

Automated agent that monitors WCCC (West Chester Cycling Club) ride postings and automatically registers for rides matching your criteria.

## Features

- **Automated Login** - Signs into WCCC website with your credentials
- **Calendar Navigation** - Browses the club calendar for upcoming rides
- **Smart Search** - Finds rides matching configurable search criteria
- **Auto-Registration** - Registers for the first available unregistered ride
- **Screenshot Documentation** - Captures numbered screenshots at each step
- **Hourly Scheduling** - Runs continuously on an hourly schedule
- **LangSmith Tracing** - Full agent reasoning available for review

## Architecture

- **Python LangChain Agent** with **Gemini 2.0** LLM
- **Playwright MCP Server** for browser automation (Chromium, visible mode)
- **LangSmith** for tracing and session review
- **Python schedule** for hourly execution

## Prerequisites

- Python 3.10+
- Node.js (for Playwright MCP)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/mjwoolley/robo-ride-signup.git
   cd robo-ride-signup
   ```

2. **Create virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` with your credentials:
   ```
   GOOGLE_API_KEY=your-gemini-key
   LANGSMITH_API_KEY=your-langsmith-key
   LANGSMITH_PROJECT=wccc-ride-signup
   LANGCHAIN_TRACING_V2=true
   WCCC_USERNAME=your-username
   WCCC_PASSWORD=your-password
   PAGE_TIMEOUT_SECONDS=15
   RIDE_SEARCH_TERM=B/B- Ride, Jenn
   ```

## API Keys Setup

### Google Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key → `GOOGLE_API_KEY`

### LangSmith API Key
1. Go to [LangSmith](https://smith.langchain.com/)
2. Sign up/sign in
3. Go to Settings → API Keys
4. Create new API key → `LANGSMITH_API_KEY`

## Usage

### Run Once
```bash
source venv/bin/activate
python -m src.main
```

### Run with Debug Logging
```bash
python -m src.main -d
```

### Run on Hourly Schedule
```bash
python -m src.main --schedule
```

### Show Help
```bash
python -m src.main -h
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `-h, --help` | Show help message and exit |
| `-d, --debug` | Enable debug mode - log full AI responses and tool calls |
| `-s, --schedule` | Run on hourly schedule instead of once |

## Project Structure

```
src/
├── main.py           # Entry point with scheduler
├── agent.py          # LangChain agent with Gemini + MCP
├── config.py         # System prompt and configuration
└── logger.py         # Custom logger with screenshot links
logs/
├── screenshots/      # Screenshot files (numbered sequentially)
└── run_YYYYMMDD_HHMMSS.log  # Log file per run
.env
.env.example
requirements.txt
feature_spec.md       # Feature tracking
```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Gemini API key | Required |
| `LANGSMITH_API_KEY` | LangSmith API key | Required |
| `WCCC_USERNAME` | WCCC login username | Required |
| `WCCC_PASSWORD` | WCCC login password | Required |
| `RIDE_SEARCH_TERM` | Ride name to search for | "B/B- Ride, Jenn" |
| `PAGE_TIMEOUT_SECONDS` | Browser timeout | 15 |

## Output

### Screenshots
Screenshots are saved to `logs/screenshots/` with descriptive names:
- `01_homepage.png`
- `02_login_form.png`
- `03_logged_in.png`
- `04_calendar.png`
- `05_ride_details.png`
- etc.

### Logs
Each run creates a log file: `logs/run_YYYYMMDD_HHMMSS.log`

### LangSmith
View full agent reasoning at [smith.langchain.com](https://smith.langchain.com/)

## How It Works

1. **Navigate** to WCCC website
2. **Sign in** with credentials from environment
3. **Browse calendar** for rides within 10 days
4. **Search** for rides matching `RIDE_SEARCH_TERM`
5. **Check registration** status for each match
6. **Register** for first available unregistered ride
7. **Document** each step with screenshots

## Error Handling

- **Retry Logic**: Agent retries failed actions up to 3 times
- **Screenshots**: Captures page state on errors
- **Detailed Logging**: Full debug logs for troubleshooting

## License

MIT
