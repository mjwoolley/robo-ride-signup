import asyncio
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .config import GOOGLE_API_KEY, WCCC_USERNAME, WCCC_PASSWORD, get_system_prompt
from .logger import setup_logger, get_screenshot_path, log_screenshot

logger = setup_logger()

def create_mcp_tool(name: str, description: str, input_schema: dict, session: ClientSession):
    """Create a LangChain tool from an MCP tool definition."""

    async def call_tool(**kwargs):
        result = await session.call_tool(name, kwargs)
        # Extract text content from result
        if result.content:
            texts = [c.text for c in result.content if hasattr(c, 'text')]
            return "\n".join(texts) if texts else str(result.content)
        return "Tool executed successfully"

    # Build parameters from schema
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    return StructuredTool.from_function(
        func=lambda **kwargs: asyncio.get_event_loop().run_until_complete(call_tool(**kwargs)),
        coroutine=call_tool,
        name=name,
        description=description,
        args_schema=None,  # Will use kwargs
    )

async def run_agent(task: str):
    """Run the agent with a given task."""
    logger.info(f"Starting agent with task: {task}")

    # Set up MCP server parameters for Playwright
    server_params = StdioServerParameters(
        command="npx",
        args=["@playwright/mcp@latest", "--browser", "chromium"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()

            # Get available tools from MCP
            tools_result = await session.list_tools()
            logger.info(f"Loaded {len(tools_result.tools)} tools from Playwright MCP")

            # Convert MCP tools to LangChain tools
            tools = []
            for tool in tools_result.tools:
                lc_tool = create_mcp_tool(
                    tool.name,
                    tool.description or "",
                    tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                    session
                )
                tools.append(lc_tool)

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
                prompt=get_system_prompt(),
            )

            try:
                # Run the agent
                result = await agent.ainvoke({
                    "messages": [("user", task)]
                })

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
