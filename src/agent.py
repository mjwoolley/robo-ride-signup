import asyncio
import json
import os
from typing import Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import GOOGLE_API_KEY, WCCC_USERNAME, WCCC_PASSWORD, get_system_prompt
from .logger import setup_logger, get_screenshot_path, log_screenshot

logger = setup_logger()

async def run_agent(task: str):
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
                # Run the agent
                result = await agent.ainvoke({
                    "messages": [
                        ("system", get_system_prompt()),
                        ("user", task)
                    ]
                })

                # Log the agent's response
                if result.get("messages"):
                    last_message = result["messages"][-1]
                    if hasattr(last_message, 'content'):
                        logger.info(f"Agent response: {last_message.content[:500]}...")

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
