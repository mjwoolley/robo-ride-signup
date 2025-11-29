import asyncio
import os
import subprocess
from typing import Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from .config import GOOGLE_API_KEY, WCCC_USERNAME, WCCC_PASSWORD, RIDE_SEARCH_TERM, get_system_prompt
from .logger import setup_logger, get_screenshot_path, log_screenshot, get_current_log_session

logger = setup_logger()

# Global variables to hold browser state during agent execution
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None

def cleanup_stale_playwright_processes():
    """Kill any stale Playwright/Chrome processes and remove lock files.

    Uses aggressive pkill -9 approach since this is the only service in the container.
    """
    logger.info("Cleaning up stale Playwright processes...")

    # Kill any existing chrome/playwright processes (aggressive cleanup approved)
    try:
        subprocess.run(["pkill", "-9", "chrome"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "chromium"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "node"], stderr=subprocess.DEVNULL)
        logger.info("Killed stale browser processes")
    except Exception as e:
        logger.warning(f"Error killing processes: {e}")

    # Remove lock files
    lock_dirs = [
        "/root/.cache/ms-playwright",
        "/tmp/.ms-playwright",
        os.path.expanduser("~/.config/chromium")
    ]

    for lock_dir in lock_dirs:
        if os.path.exists(lock_dir):
            try:
                # Find and remove .lock files
                subprocess.run(["find", lock_dir, "-name", "*.lock", "-delete"],
                               stderr=subprocess.DEVNULL)
                logger.info(f"Cleaned lock files from {lock_dir}")
            except Exception as e:
                logger.warning(f"Error cleaning {lock_dir}: {e}")

async def _get_page() -> Page:
    """Get the current page instance."""
    if _page is None:
        raise RuntimeError("Browser not initialized. Call this tool only after browser is ready.")
    return _page

@tool
async def browser_navigate(url: str) -> str:
    """Navigate to a URL.

    Args:
        url: The URL to navigate to

    Returns:
        Success message with the current URL
    """
    page = await _get_page()
    logger.info(f"Navigating to: {url}")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    logger.info(f"Successfully navigated to: {page.url}")
    return f"Successfully navigated to {page.url}"

@tool
async def browser_click(element_selector: str) -> str:
    """Click on an element.

    Args:
        element_selector: CSS selector or text to click on (e.g., 'button', 'text=Login', '#submit')

    Returns:
        Success message
    """
    page = await _get_page()
    logger.info(f"Clicking element: {element_selector}")
    await page.click(element_selector, timeout=10000)
    logger.info(f"Successfully clicked: {element_selector}")
    return f"Successfully clicked element: {element_selector}"

@tool
async def browser_fill(element_selector: str, text: str) -> str:
    """Fill text into an input field.

    Args:
        element_selector: CSS selector for the input field
        text: Text to fill into the field

    Returns:
        Success message
    """
    page = await _get_page()
    logger.info(f"Filling element {element_selector} with text")
    await page.fill(element_selector, text, timeout=10000)
    logger.info(f"Successfully filled: {element_selector}")
    return f"Successfully filled element: {element_selector}"

@tool
async def browser_type(element_selector: str, text: str) -> str:
    """Type text into an input field (slower but more realistic than fill).

    Args:
        element_selector: CSS selector for the input field
        text: Text to type into the field

    Returns:
        Success message
    """
    page = await _get_page()
    logger.info(f"Typing into element: {element_selector}")
    await page.type(element_selector, text, timeout=10000)
    logger.info(f"Successfully typed into: {element_selector}")
    return f"Successfully typed into element: {element_selector}"

@tool
async def browser_press_key(key: str) -> str:
    """Press a keyboard key.

    Args:
        key: Key name (e.g., 'Enter', 'Tab', 'Escape')

    Returns:
        Success message
    """
    page = await _get_page()
    logger.info(f"Pressing key: {key}")
    await page.keyboard.press(key)
    logger.info(f"Successfully pressed key: {key}")
    return f"Successfully pressed key: {key}"

@tool
async def browser_screenshot(name: str = "screenshot") -> str:
    """Take a screenshot of the current page.

    Args:
        name: Optional name for the screenshot file

    Returns:
        Path to the saved screenshot
    """
    page = await _get_page()
    log_session = get_current_log_session()
    screenshot_path = get_screenshot_path(name, log_session)

    logger.info(f"Taking screenshot: {screenshot_path}")
    await page.screenshot(path=screenshot_path, full_page=True)
    log_screenshot(screenshot_path)
    logger.info(f"Screenshot saved: {screenshot_path}")

    return f"Screenshot saved to {screenshot_path}"

@tool
async def browser_get_content() -> str:
    """Get the text content of the current page.

    Returns:
        Text content of the page (first 5000 characters)
    """
    page = await _get_page()
    logger.info("Getting page content")
    content = await page.content()
    # Return first 5000 chars to avoid overwhelming the LLM
    truncated = content[:5000]
    logger.info(f"Retrieved page content ({len(content)} chars, returning {len(truncated)})")
    return truncated

@tool
async def browser_get_text(element_selector: str) -> str:
    """Get the text content of a specific element.

    Args:
        element_selector: CSS selector for the element

    Returns:
        Text content of the element
    """
    page = await _get_page()
    logger.info(f"Getting text from element: {element_selector}")
    text = await page.text_content(element_selector, timeout=10000)
    logger.info(f"Retrieved text from {element_selector}: {text[:100]}...")
    return text or ""

@tool
async def browser_wait_for_selector(element_selector: str, timeout_ms: int = 10000) -> str:
    """Wait for an element to appear on the page.

    Args:
        element_selector: CSS selector for the element to wait for
        timeout_ms: Maximum time to wait in milliseconds (default 10000)

    Returns:
        Success message
    """
    page = await _get_page()
    logger.info(f"Waiting for element: {element_selector}")
    await page.wait_for_selector(element_selector, timeout=timeout_ms)
    logger.info(f"Element appeared: {element_selector}")
    return f"Element appeared: {element_selector}"

@tool
async def browser_is_visible(element_selector: str) -> str:
    """Check if an element is visible on the page.

    Args:
        element_selector: CSS selector for the element

    Returns:
        "true" if visible, "false" otherwise
    """
    page = await _get_page()
    logger.info(f"Checking visibility of element: {element_selector}")
    try:
        is_visible = await page.is_visible(element_selector, timeout=3000)
        logger.info(f"Element {element_selector} visible: {is_visible}")
        return "true" if is_visible else "false"
    except Exception as e:
        logger.info(f"Element {element_selector} not found or not visible")
        return "false"

@tool
async def browser_evaluate(script: str) -> str:
    """Execute JavaScript code in the browser context.

    Args:
        script: JavaScript code to execute

    Returns:
        Result of the script execution (converted to string)
    """
    page = await _get_page()
    logger.info(f"Evaluating JavaScript: {script[:100]}...")
    result = await page.evaluate(script)
    logger.info(f"JavaScript result: {result}")
    return str(result)

# List of all browser tools
BROWSER_TOOLS = [
    browser_navigate,
    browser_click,
    browser_fill,
    browser_type,
    browser_press_key,
    browser_screenshot,
    browser_get_content,
    browser_get_text,
    browser_wait_for_selector,
    browser_is_visible,
    browser_evaluate,
]

async def run_agent(task: str, debug: bool = False):
    """Run the agent with a given task."""
    global _browser, _context, _page

    logger.info(f"Starting agent with task: {task}")

    # Clean up any stale processes/locks from previous runs
    cleanup_stale_playwright_processes()

    # Set up output directory for screenshots
    output_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "screenshots")
    os.makedirs(output_dir, exist_ok=True)

    # Log environment state for debugging
    logger.info(f"Browser cache path: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH', 'default')}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Working directory: {os.getcwd()}")

    playwright = None
    try:
        # Launch Playwright browser
        logger.info("Starting Playwright browser...")
        playwright = await async_playwright().start()

        _browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-setuid-sandbox',
            ]
        )
        logger.info("Browser launched successfully")

        # Create browser context and page
        _context = await _browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        _page = await _context.new_page()
        logger.info("Browser page ready")

        # Log tool names
        tool_names = [t.name for t in BROWSER_TOOLS]
        logger.info(f"Available tools: {tool_names}")

        # Initialize Gemini LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0,
        )

        # Create the agent
        agent = create_react_agent(
            llm,
            BROWSER_TOOLS,
        )

        try:
            # Get log session for screenshot naming
            log_session = get_current_log_session()

            # Run the agent with increased recursion limit for complex tasks
            result = await agent.ainvoke(
                {
                    "messages": [
                        ("system", get_system_prompt(log_session)),
                        ("user", task)
                    ]
                },
                config={"recursion_limit": 100}
            )

            # Log the agent's response
            if result.get("messages"):
                if debug:
                    # Log all messages in debug mode
                    logger.info("=" * 40)
                    logger.info("DEBUG: Full conversation history")
                    logger.info("=" * 40)
                    for i, msg in enumerate(result["messages"]):
                        msg_type = type(msg).__name__
                        if msg_type == "ToolMessage":
                            continue  # Skip tool messages entirely

                        # Color codes
                        if msg_type == "SystemMessage":
                            color = "\033[36m"  # Cyan
                        elif msg_type == "HumanMessage":
                            color = "\033[32m"  # Green
                        elif msg_type == "AIMessage":
                            color = "\033[35m"  # Magenta
                        else:
                            color = ""
                        reset = "\033[0m" if color else ""

                        if hasattr(msg, 'content'):
                            content = msg.content if isinstance(msg.content, str) else str(msg.content)
                            logger.info(f"{color}[{i}] {msg_type}: {content}{reset}")
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                logger.info(f"{color}    Tool call: {tc.get('name', 'unknown')} - {tc.get('args', {})}{reset}")
                    logger.info("=" * 40)
                else:
                    # Normal mode - just log last message summary
                    last_message = result["messages"][-1]
                    if hasattr(last_message, 'content'):
                        content = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
                        logger.info(f"Agent response: {content[:500]}...")

            logger.info("Agent completed task")
            return result
        except Exception as e:
            logger.error(f"Agent error: {e}")
            raise
    except Exception as e:
        logger.error(f"Failed to start or run browser: {e}", exc_info=True)
        raise
    finally:
        # Clean up browser resources
        logger.info("Cleaning up browser resources...")
        try:
            if _page:
                await _page.close()
                _page = None
            if _context:
                await _context.close()
                _context = None
            if _browser:
                await _browser.close()
                _browser = None
            if playwright:
                await playwright.stop()
            logger.info("Browser cleanup complete")
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}", exc_info=True)

async def test_agent():
    """Test that the agent can start and take a screenshot."""
    task = """
    Navigate to https://example.com and take a screenshot of the page.
    Report what you see on the page.
    """

    result = await run_agent(task)
    logger.info("Test completed successfully")
    return result

# WCCC Website URL
WCCC_URL = "https://www.wccyclingclub.com/content.aspx?page_id=0&club_id=939827"

async def navigate_to_wccc():
    """Navigate to the WCCC website and take a screenshot."""
    task = f"""
    Navigate to {WCCC_URL} and take a screenshot of the page.
    Confirm that you have successfully loaded the WCCC Cycling Club website.
    Report what you see on the homepage.
    """

    result = await run_agent(task)
    logger.info("WCCC navigation completed")
    return result

async def sign_in_to_wccc():
    """Navigate to WCCC and sign in with credentials."""
    task = f"""
    1. Navigate to {WCCC_URL}
    2. Find the login form on the page
    3. Enter these credentials:
       - Username/Email: {WCCC_USERNAME}
       - Password: {WCCC_PASSWORD}
    4. Submit the login form
    5. Take a screenshot after login attempt
    6. Verify that you are now logged in (look for user profile, logout button, or welcome message)

    IMPORTANT: If the login fails, review what went wrong from the page state, and retry.
    You have up to 3 attempts to successfully log in.
    After 3 failed attempts, report the error and stop.

    Report whether login was successful and what you see on the page after login.
    """

    result = await run_agent(task)
    logger.info("WCCC sign-in completed")
    return result

async def navigate_to_calendar():
    """Sign in to WCCC and navigate to the Calendar tab."""
    task = f"""
    1. Navigate to {WCCC_URL}
    2. Sign in with:
       - Username/Email: {WCCC_USERNAME}
       - Password: {WCCC_PASSWORD}
    3. After successful login, find and click on the "Calendar" tab/link
    4. Take a screenshot of the calendar view
    5. Report what you see on the calendar page

    If any step fails, retry up to 3 times before giving up.
    """

    result = await run_agent(task)
    logger.info("Calendar navigation completed")
    return result

async def find_and_register_for_ride(debug: bool = False):
    """Complete workflow: sign in, find target ride, and register."""
    from datetime import datetime, timedelta

    today = datetime.now().strftime("%B %d, %Y")
    end_date = (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y")

    task = f"""
    Complete the following workflow to register for a cycling ride:

    1. Navigate to {WCCC_URL}
    2. Sign in with:
       - Username/Email: {WCCC_USERNAME}
       - Password: {WCCC_PASSWORD}
    3. After successful login, click on the "Calendar" tab
    4. Search the calendar for rides matching "{RIDE_SEARCH_TERM}"
       - Look for rides from today ({today}) through the next 10 days ({end_date})
       - Navigate through calendar dates as needed
    5. For each matching ride found:
       - Click on the ride to view details
       - Check if you are already registered
       - If NOT registered, click the register/sign-up button
       - If ALREADY registered, note this and check the next matching ride
    6. Take screenshots at key steps (calendar view, ride details, registration confirmation)
    7. Report:
       - Which rides were found
       - Your registration status for each
       - Which ride (if any) you registered for

    IMPORTANT:
    - If login fails, retry up to 3 times
    - If no matching rides are found, report this and stop
    - If all matching rides are already registered, report this
    - Take screenshots to document your progress

    Be thorough in searching the calendar - check multiple days within the date range.
    """

    result = await run_agent(task, debug=debug)
    logger.info("Ride search and registration completed")
    return result
