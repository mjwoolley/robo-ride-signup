import asyncio
import os
import subprocess
from typing import Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from .config import GOOGLE_API_KEY, WCCC_USERNAME, WCCC_PASSWORD, RIDE_SEARCH_TERM, get_system_prompt
from .logger import setup_logger, get_screenshot_path, log_screenshot, get_current_log_session, get_current_screenshot_dir

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
        Success message with the current URL or error description
    """
    page = await _get_page()
    logger.info(f"Navigating to: {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Additional wait for dynamic content to load
        await page.wait_for_timeout(1000)

        logger.info(f"Successfully navigated to: {page.url}")
        return f"Successfully navigated to {page.url}"
    except Exception as e:
        error_msg = f"Failed to navigate to '{url}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_click(element_selector: str) -> str:
    """Click on an element.

    Args:
        element_selector: CSS selector or text to click on (e.g., 'button', 'text=Login', '#submit')

    Returns:
        Success message or error description
    """
    page = await _get_page()
    logger.info(f"Clicking element: {element_selector}")
    try:
        # Wait for element to be visible and attached to DOM
        await page.wait_for_selector(element_selector, state="visible", timeout=15000)

        # Scroll element into view if needed
        await page.locator(element_selector).scroll_into_view_if_needed()

        # Click with force=True to handle elements that might be covered
        await page.click(element_selector, timeout=10000, force=True)

        # Small delay to allow click to process
        await page.wait_for_timeout(500)

        logger.info(f"Successfully clicked: {element_selector}")
        return f"Successfully clicked element: {element_selector}"
    except Exception as e:
        error_msg = f"Failed to click element '{element_selector}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_fill(element_selector: str, text: str) -> str:
    """Fill text into an input field.

    Args:
        element_selector: CSS selector for the input field
        text: Text to fill into the field

    Returns:
        Success message or error description
    """
    page = await _get_page()
    logger.info(f"Filling element {element_selector} with text")
    try:
        # Wait for element to be visible and editable
        await page.wait_for_selector(element_selector, state="visible", timeout=15000)

        # Scroll element into view if needed
        await page.locator(element_selector).scroll_into_view_if_needed()

        # Click to focus the field first
        await page.click(element_selector, timeout=10000)

        # Clear existing content
        await page.fill(element_selector, "", timeout=5000)

        # Fill with new text
        await page.fill(element_selector, text, timeout=10000)

        # Small delay to allow value to register
        await page.wait_for_timeout(300)

        logger.info(f"Successfully filled: {element_selector}")
        return f"Successfully filled element: {element_selector}"
    except Exception as e:
        error_msg = f"Failed to fill element '{element_selector}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_type(element_selector: str, text: str) -> str:
    """Type text into an input field (slower but more realistic than fill).

    Args:
        element_selector: CSS selector for the input field
        text: Text to type into the field

    Returns:
        Success message or error description
    """
    page = await _get_page()
    logger.info(f"Typing into element: {element_selector}")
    try:
        await page.type(element_selector, text, timeout=10000)
        logger.info(f"Successfully typed into: {element_selector}")
        return f"Successfully typed into element: {element_selector}"
    except Exception as e:
        error_msg = f"Failed to type into element '{element_selector}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_press_key(key: str) -> str:
    """Press a keyboard key.

    Args:
        key: Key name (e.g., 'Enter', 'Tab', 'Escape')

    Returns:
        Success message or error description
    """
    page = await _get_page()
    logger.info(f"Pressing key: {key}")
    try:
        await page.keyboard.press(key)
        logger.info(f"Successfully pressed key: {key}")
        return f"Successfully pressed key: {key}"
    except Exception as e:
        error_msg = f"Failed to press key '{key}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_screenshot(name: str = "screenshot") -> str:
    """Take a screenshot of the current page.

    Args:
        name: Optional name for the screenshot file

    Returns:
        Path to the saved screenshot or error description
    """
    page = await _get_page()
    try:
        screenshot_path = get_screenshot_path(name)
        logger.info(f"Taking screenshot: {screenshot_path}")
        await page.screenshot(path=screenshot_path, full_page=True)
        log_screenshot(logger, screenshot_path)
        logger.info(f"Screenshot saved: {screenshot_path}")
        return f"Screenshot saved to {screenshot_path}"
    except Exception as e:
        error_msg = f"Failed to take screenshot '{name}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_get_content() -> str:
    """Get the text content of the current page.

    Returns:
        Text content of the page (first 5000 characters) or error description
    """
    page = await _get_page()
    logger.info("Getting page content")
    try:
        content = await page.content()
        # Return first 5000 chars to avoid overwhelming the LLM
        truncated = content[:5000]
        logger.info(f"Retrieved page content ({len(content)} chars, returning {len(truncated)})")
        return truncated
    except Exception as e:
        error_msg = f"Failed to get page content: {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_get_text(element_selector: str) -> str:
    """Get the text content of a specific element.

    Args:
        element_selector: CSS selector for the element

    Returns:
        Text content of the element or error description
    """
    page = await _get_page()
    logger.info(f"Getting text from element: {element_selector}")
    try:
        text = await page.text_content(element_selector, timeout=10000)
        logger.info(f"Retrieved text from {element_selector}: {text[:100] if text else 'None'}...")
        return text or ""
    except Exception as e:
        error_msg = f"Failed to get text from element '{element_selector}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_wait_for_selector(element_selector: str, timeout_ms: int = 10000) -> str:
    """Wait for an element to appear on the page.

    Args:
        element_selector: CSS selector for the element to wait for
        timeout_ms: Maximum time to wait in milliseconds (default 10000)

    Returns:
        Success message or error description
    """
    page = await _get_page()
    logger.info(f"Waiting for element: {element_selector}")
    try:
        await page.wait_for_selector(element_selector, timeout=timeout_ms)
        logger.info(f"Element appeared: {element_selector}")
        return f"Element appeared: {element_selector}"
    except Exception as e:
        error_msg = f"Failed to find element '{element_selector}' within {timeout_ms}ms: {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_wait(seconds: int) -> str:
    """Wait for a specified number of seconds. Use this when you need to wait for a page to finish loading or processing.

    Args:
        seconds: Number of seconds to wait (1-10)

    Returns:
        Success message
    """
    if seconds < 1 or seconds > 10:
        return "Error: seconds must be between 1 and 10"

    import asyncio
    logger.info(f"Waiting {seconds} seconds...")
    await asyncio.sleep(seconds)
    logger.info(f"Wait complete ({seconds} seconds)")
    return f"Waited {seconds} seconds"

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
        Result of the script execution (converted to string) or error description
    """
    page = await _get_page()
    logger.info(f"Evaluating JavaScript: {script[:100]}...")
    try:
        result = await page.evaluate(script)
        logger.info(f"JavaScript result: {result}")
        return str(result)
    except Exception as e:
        error_msg = f"Failed to evaluate JavaScript: {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_list_frames() -> str:
    """List all iframes on the current page.

    Returns:
        Information about all frames including name, src, and index, or error description
    """
    page = await _get_page()
    logger.info("Listing all frames on page")
    try:
        frames = page.frames
        frame_info = []
        for i, frame in enumerate(frames):
            name = frame.name or "(no name)"
            url = frame.url or "(no URL)"
            is_main = " [MAIN FRAME]" if frame == page.main_frame else ""
            frame_info.append(f"Frame {i}: name='{name}', url='{url}'{is_main}")

        result = "\n".join(frame_info) if frame_info else "No frames found"
        logger.info(f"Found {len(frames)} frames")
        return result
    except Exception as e:
        error_msg = f"Failed to list frames: {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_get_frame_content(frame_selector: str) -> str:
    """Get HTML content from a specific iframe.

    Args:
        frame_selector: Frame name, URL substring, or index number (e.g., "loginFrame", "auth.example.com", or "1")

    Returns:
        HTML content from the specified frame (first 5000 chars) or error description
    """
    page = await _get_page()
    logger.info(f"Getting content from frame: {frame_selector}")
    try:
        frames = page.frames
        target_frame = None

        # Try to find frame by index first
        try:
            frame_index = int(frame_selector)
            if 0 <= frame_index < len(frames):
                target_frame = frames[frame_index]
                logger.info(f"Found frame by index: {frame_index}")
        except ValueError:
            pass

        # If not found by index, try by name or URL
        if target_frame is None:
            for frame in frames:
                if (frame.name and frame_selector.lower() in frame.name.lower()) or \
                   (frame.url and frame_selector.lower() in frame.url.lower()):
                    target_frame = frame
                    logger.info(f"Found frame by name/URL: {frame.name or frame.url}")
                    break

        if target_frame is None:
            return f"Frame not found: '{frame_selector}'. Use browser_list_frames to see available frames."

        content = await target_frame.content()
        truncated = content[:5000]
        logger.info(f"Retrieved frame content ({len(content)} chars, returning 5000)")
        return truncated
    except Exception as e:
        error_msg = f"Failed to get frame content '{frame_selector}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_fill_in_frame(frame_selector: str, element_selector: str, text: str) -> str:
    """Fill text into an input field inside an iframe.

    Args:
        frame_selector: Frame name, URL substring, or index number
        element_selector: CSS selector for the input field within the frame
        text: Text to fill

    Returns:
        Success message or error description
    """
    page = await _get_page()
    logger.info(f"Filling element '{element_selector}' in frame '{frame_selector}'")
    try:
        frames = page.frames
        target_frame = None

        # Try to find frame by index first
        try:
            frame_index = int(frame_selector)
            if 0 <= frame_index < len(frames):
                target_frame = frames[frame_index]
        except ValueError:
            pass

        # If not found by index, try by name or URL
        if target_frame is None:
            for frame in frames:
                if (frame.name and frame_selector.lower() in frame.name.lower()) or \
                   (frame.url and frame_selector.lower() in frame.url.lower()):
                    target_frame = frame
                    break

        if target_frame is None:
            return f"Frame not found: '{frame_selector}'. Use browser_list_frames to see available frames."

        await target_frame.fill(element_selector, text, timeout=10000)
        logger.info(f"Successfully filled '{element_selector}' in frame")
        return f"Successfully filled element '{element_selector}' in frame '{frame_selector}'"
    except Exception as e:
        error_msg = f"Failed to fill element '{element_selector}' in frame '{frame_selector}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

@tool
async def browser_click_in_frame(frame_selector: str, element_selector: str) -> str:
    """Click an element inside an iframe.

    Args:
        frame_selector: Frame name, URL substring, or index number
        element_selector: CSS selector or text for the element within the frame

    Returns:
        Success message or error description
    """
    page = await _get_page()
    logger.info(f"Clicking element '{element_selector}' in frame '{frame_selector}'")
    try:
        frames = page.frames
        target_frame = None

        # Try to find frame by index first
        try:
            frame_index = int(frame_selector)
            if 0 <= frame_index < len(frames):
                target_frame = frames[frame_index]
        except ValueError:
            pass

        # If not found by index, try by name or URL
        if target_frame is None:
            for frame in frames:
                if (frame.name and frame_selector.lower() in frame.name.lower()) or \
                   (frame.url and frame_selector.lower() in frame.url.lower()):
                    target_frame = frame
                    break

        if target_frame is None:
            return f"Frame not found: '{frame_selector}'. Use browser_list_frames to see available frames."

        await target_frame.click(element_selector, timeout=10000)
        logger.info(f"Successfully clicked '{element_selector}' in frame")
        return f"Successfully clicked element '{element_selector}' in frame '{frame_selector}'"
    except Exception as e:
        error_msg = f"Failed to click element '{element_selector}' in frame '{frame_selector}': {str(e)}"
        logger.warning(error_msg)
        return error_msg

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
    browser_wait,
    browser_is_visible,
    browser_evaluate,
    browser_list_frames,
    browser_get_frame_content,
    browser_fill_in_frame,
    browser_click_in_frame,
]

async def run_agent(task: str, debug: bool = False):
    """Run the agent with a given task."""
    global _browser, _context, _page

    logger.info(f"Starting agent with task: {task}")

    # Clean up any stale processes/locks from previous runs
    cleanup_stale_playwright_processes()

    # Get screenshot directory for this run (created by setup_logger)
    screenshot_dir = get_current_screenshot_dir()

    # Log environment state for debugging
    logger.info(f"Browser cache path: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH', 'default')}")
    logger.info(f"Output directory: {screenshot_dir}")
    logger.info(f"Working directory: {os.getcwd()}")

    playwright = None
    try:
        # Launch Playwright browser
        logger.info("Starting Playwright browser...")
        playwright = await async_playwright().start()

        # Use HEADLESS env var to control headless mode (default: True for Cloud Run)
        headless = os.getenv("HEADLESS", "true").lower() != "false"
        logger.info(f"Launching browser with headless={headless}")

        _browser = await playwright.chromium.launch(
            headless=headless,
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
            model="gemini-2.0-flash-exp",
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

            # Always extract and log the final report
            logger.info("=" * 50)
            logger.info("AGENT FINAL REPORT")
            logger.info("=" * 50)
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                final_report = last_message.content if isinstance(last_message.content, str) else str(last_message.content)
                logger.info(final_report)
            logger.info("=" * 50)

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

    1. NAVIGATE TO HOMEPAGE:
       - Navigate to {WCCC_URL}
       - Take screenshot "01_homepage"

    2. LOGIN:
       - Click "Login" button using text=Login
       - Take screenshot "02_login_page"
       - The page will navigate to a login URL - this is NORMAL, not an error
       - Fill TWO SEPARATE fields:
         * User Name field: #ctl00_ctl00_login_name
           Fill with: {WCCC_USERNAME}
         * Password field: #ctl00_ctl00_password
           Fill with: {WCCC_PASSWORD}
       - Click submit button: #ctl00_ctl00_login_button (it's an <a> link, NOT an input!)
       - Take screenshot "03_logged_in"
       - VERIFY login success:
         * Look for "Mike Woolley" in upper right (NOT "Member Login")
         * Verify "Calendar" link is visible
         * If login failed, retry up to 3 times

    3. NAVIGATE TO CALENDAR:
       - Click on the "Calendar" tab using text=Calendar
       - Take screenshot "04_calendar"

    4. FIND TARGET RIDE:
       - Search the calendar for rides matching "{RIDE_SEARCH_TERM}"
       - Look for rides from today ({today}) through {end_date}
       - One month of the calendar is displayed at a time.
       - You may need to search the current month and then navigate to the next month if {end_date} is in the next month
       - To navigate to the next month click the link titled "Go to the next month"
       - Use browser_get_content() to get page HTML and search for ride name
       - Click on the ride using text matching: browser_click("text={RIDE_SEARCH_TERM}")
       - Take screenshot "05_ride_details"

    5. CHECK REGISTRATION STATUS:
       - Use browser_is_visible("text=Cancel Registration") to check status
       - If "Cancel Registration" button EXISTS → You ARE already registered
       - If "Cancel Registration" button DOES NOT exist → You are NOT registered
       - DO NOT rely on text like "You are registered" - only check for the button!

    6. COMPLETE REGISTRATION (if not already registered):
       - There are TWO Register buttons - you MUST click the correct one!
       - TOP button (WRONG): #ctl00_ctl00_user_actions_register_button - DO NOT CLICK
       - BOTTOM button (CORRECT): #ctl00_ctl00_detail_registration_register_button - CLICK THIS
       - Click: browser_click("#ctl00_ctl00_detail_registration_register_button")
       - Take screenshot "06_registration_page1"

       REGISTRATION FLOW:
       - Step 1 - Who's Attending: always click the Next button
         * Take screenshot "07_after_next"
       - Step 2 - Complete Registration:
         * Take screenshot to see the current page state
         * Click "Complete Registration" button using: #ctl00_ctl00_done_button_top
         * browser_click("#ctl00_ctl00_done_button_top")
         * Take screenshot "08_after_complete_registration"
         * Look for popup saying "Your registration has been received" (may disappear quickly)
         * You should be redirected back to the Ride details page

       VERIFY SUCCESS:
       - Check for "Cancel Registration" button using browser_is_visible("text=Cancel Registration")
       - If "Cancel Registration" button is now visible → registration successful!
       - If it isn't visible, take a screenshot and examine what page you're on
       - If registration failed, retry the entire registration flow
       - Take final screenshot showing "Cancel Registration" button

    7. REPORT:
       - Which rides were found
       - Your registration status for each
       - Which ride (if any) you registered for

    IMPORTANT:
    - Take screenshots AFTER EVERY page load or navigation
    - If any action fails, take a screenshot and retry up to 3 times
    - If no matching rides are found, report this and stop
    - If all matching rides are already registered, report this
    """

    result = await run_agent(task, debug=debug)
    logger.info("Ride search and registration completed")
    return result
