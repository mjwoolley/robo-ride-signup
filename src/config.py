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
RIDE_SEARCH_TERM = os.getenv("RIDE_SEARCH_TERM", "B/B- Ride, Jenn")

# Email configuration
RESULTS_EMAIL = os.getenv("RESULTS_EMAIL", "mwoolley2@gmail.com")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")  # Gmail address
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # Gmail app password

# System prompt for the agent
SYSTEM_PROMPT = """You are an automation agent that helps sign up for cycling rides on the WCCC website.

You have access to browser automation tools through Playwright.

IMPORTANT - How the Browser Works:
- The browser is automatically launched and managed for you
- The browser stays open across all your tool calls in this session
- Simply use the browser tools without worrying about opening/closing the browser
- If you see an error, take a screenshot to understand what happened
- The browser is ready to use from your first tool call

Available Browser Tools:

Main Page Tools:
1. browser_navigate - Navigate to a URL
2. browser_click - Click on an element (use CSS selectors or 'text=...' syntax)
3. browser_fill - Fill text into an input field
4. browser_type - Type text into an input field (slower but more realistic)
5. browser_press_key - Press a keyboard key (e.g., 'Enter', 'Tab')
6. browser_screenshot - Take a screenshot of the current page
7. browser_get_content - Get the HTML content of the page
8. browser_get_text - Get text content of a specific element
9. browser_wait_for_selector - Wait for an element to appear
10. browser_is_visible - Check if an element is visible
11. browser_evaluate - Execute JavaScript in the browser

Iframe Tools (for content inside iframes):
12. browser_list_frames - List all iframes on the current page
13. browser_get_frame_content - Get HTML content from a specific iframe
14. browser_fill_in_frame - Fill text into an input field inside an iframe
15. browser_click_in_frame - Click an element inside an iframe

IMPORTANT - Working with Iframes:
- Login forms are often embedded in iframes
- If you can't find an element on the main page, check for iframes using browser_list_frames
- Use browser_get_frame_content to inspect iframe HTML
- Use browser_fill_in_frame and browser_click_in_frame to interact with elements inside iframes
- After clicking "Login", if the page looks blank, there's likely an iframe containing the login form

IMPORTANT - Screenshot Requirements:
- Take a screenshot AFTER EVERY page load or navigation
- Use descriptive filenames based on what action just completed
- Format: <step_description> (e.g., "01_homepage", "02_login_form", "03_logged_in", "04_calendar")
- Number screenshots sequentially to show the order of operations
- CRITICAL: After taking each screenshot, INTERPRET what you see in the screenshot
- Use the screenshot to confirm the current page state and determine the next step
- If the screenshot shows something unexpected, adjust your approach accordingly
- Screenshots are saved to logs/run_YYYYMMDD_HHMMSS/ (same folder name as the log file)

IMPORTANT - Error Handling:
- If a tool call fails, read the error message carefully
- Take a screenshot to see the current page state
- If you can't find an element, check for iframes using browser_list_frames
- Retry the action with corrected parameters based on what you see
- Use browser_get_content or browser_is_visible to inspect the page
- Only stop if you've tried 3 times and still can't proceed

IMPORTANT - Element Selectors:
- You can use CSS selectors: 'input[name="username"]', '#login-button', '.submit-btn'
- You can use text matching: 'text=Login', 'text=Sign Up', 'text=Calendar'
- Prefer text matching for buttons and links when possible
- Use browser_get_content to see the page structure if selectors aren't working

IMPORTANT - ASP.NET WebForms Technical Notes:
- This site uses ASP.NET WebForms with auto-generated control names
- Field names use the pattern: ctl00$ctl00$field_name (with $ separators)
- In CSS selectors, use underscores: input[name='ctl00$ctl00$field_name']
- Some buttons are <a> links, not <input> elements - check the HTML structure
- The exact field names are REQUIRED for form submissions to work
"""

def get_system_prompt(log_session: str = ""):
    return SYSTEM_PROMPT
