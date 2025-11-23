import asyncio
import json
import os
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import GOOGLE_API_KEY, WCCC_USERNAME, WCCC_PASSWORD, RIDE_SEARCH_TERM, get_system_prompt
from .logger import setup_logger, get_screenshot_path, log_screenshot, get_current_log_session

logger = setup_logger()

async def run_agent(task: str, debug: bool = False):
    """Run the agent with a given task."""
    logger.info(f"Starting agent with task: {task}")

    # Set up MCP server parameters for Playwright
    output_dir = os.path.join(os.path.dirname(__file__), "..", "logs", "screenshots")
    server_params = StdioServerParameters(
        command="npx",
        args=["@playwright/mcp@latest", "--browser", "chromium", "--output-dir", output_dir],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            # Get available tools from MCP
            tools_result = await session.list_tools()
            logger.info(f"Loaded {len(tools_result.tools)} tools from Playwright MCP")

            # Create tool functions dynamically
            tools = []
            for mcp_tool in tools_result.tools:
                tool_name = mcp_tool.name
                tool_desc = mcp_tool.description or f"Tool: {tool_name}"

                # Add schema info to description
                input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, 'inputSchema') else {}
                if input_schema.get("properties"):
                    schema_info = json.dumps(input_schema, indent=2)
                    tool_desc = f"{tool_desc}\n\nParameters schema:\n{schema_info}"

                # Create a closure to capture tool_name
                def make_tool_func(name):
                    async def tool_func(arguments: str = "{}") -> str:
                        """Execute the MCP tool with JSON arguments."""
                        try:
                            args = json.loads(arguments) if arguments else {}
                        except json.JSONDecodeError:
                            args = {}

                        logger.debug(f"Calling tool {name} with args: {args}")
                        result = await session.call_tool(name, args)

                        # Extract text content from result
                        if result.content:
                            texts = []
                            for c in result.content:
                                if hasattr(c, 'text'):
                                    texts.append(c.text)
                            return "\n".join(texts) if texts else str(result.content)
                        return "Tool executed successfully"

                    return tool_func

                # Create the tool with decorator
                tool_func = make_tool_func(tool_name)
                tool_func.__name__ = tool_name
                tool_func.__doc__ = f"{tool_desc}\n\nPass arguments as a JSON string."

                decorated_tool = tool(tool_func)
                tools.append(decorated_tool)

            # Log tool names
            tool_names = [t.name for t in tools]
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
                tools,
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
                            if hasattr(msg, 'content'):
                                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                                logger.info(f"[{i}] {msg_type}: {content}")
                            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                                for tc in msg.tool_calls:
                                    logger.info(f"    Tool call: {tc.get('name', 'unknown')} - {tc.get('args', {})}")
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
