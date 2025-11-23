import os
from dotenv import load_dotenv

load_dotenv()

# Environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "wccc-ride-signup")
WCCC_USERNAME = os.getenv("WCCC_USERNAME")
WCCC_PASSWORD = os.getenv("WCCC_PASSWORD")
PAGE_TIMEOUT_SECONDS = int(os.getenv("PAGE_TIMEOUT_SECONDS", "15"))

# System prompt for the agent
SYSTEM_PROMPT = """You are an automation agent that helps sign up for cycling rides on the WCCC website.

You have access to browser automation tools through Playwright MCP. Use these tools to:
1. Navigate web pages
2. Fill in forms
3. Click buttons and links
4. Take screenshots to document your progress

Always take a screenshot after important actions to document what you see.
If an action fails, review the current page state and retry up to 3 times before giving up.

Current task context:
- WCCC Username: {username}
- Page timeout: {timeout} seconds
"""

def get_system_prompt():
    return SYSTEM_PROMPT.format(
        username=WCCC_USERNAME,
        timeout=PAGE_TIMEOUT_SECONDS
    )
