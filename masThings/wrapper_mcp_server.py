# This MCP server wraps the entire LangGraph pipeline,
# making it callable as a single tool by clients like the 'claude' CLI.

import asyncio
import os
from fastmcp import FastMCP
from dotenv import load_dotenv

# Important: Adjust the import path based on your project structure
from pipeline.orchestrator import run_security_audit_pipeline

# Load environment variables (like ANTHROPIC_API_KEY) from a .env file if it exists
load_dotenv()

mcp = FastMCP("SecurityAuditor")

@mcp.tool()
async def start_security_audit(repo_url: str) -> str:
    """Initiates the autonomous multi-agent security audit pipeline for a given Git repository URL.

    This process involves:
    1. Cloning the repository using a Git MCP server.
    2. Running static analysis (Semgrep) using a Semgrep MCP server.
    3. (Future steps: Dependency scanning, secret detection, reporting, etc.)
    The results from the underlying tools are orchestrated by a LangGraph agent.

    Args:
        repo_url: The full HTTPS or SSH URL of the Git repository to audit.

    Returns:
        A summary string of the audit pipeline's execution and findings, or an error message.
    """
    print(f"[Wrapper Server] Received request to audit: {repo_url}")
    try:
        # Ensure the orchestrator has the necessary environment variables (e.g., API keys)
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("Warning: ANTHROPIC_API_KEY environment variable not set.")
            return "Error: ANTHROPIC_API_KEY environment variable is not set. Please set it in the .env file."

        # Call the main pipeline function
        result_summary = await run_security_audit_pipeline(repo_url)
        print(f"[Wrapper Server] Pipeline finished. Result summary length: {len(result_summary)}")
        # Consider truncating if the summary can be excessively long
        # max_len = 4000
        # if len(result_summary) > max_len:
        #    result_summary = result_summary[:max_len] + "... [truncated]"
        return result_summary
    except Exception as e:
        print(f"[Wrapper Server] Error calling run_security_audit_pipeline: {e}")
        import traceback
        traceback.print_exc()
        return f"Error running security audit pipeline: {e}"

if __name__ == "__main__":
    print("[Wrapper Server] Starting via mcp.run()")
    mcp.run()

# Note: No uvicorn runner here, as this script is intended to be run directly
# by the MCP client (like 'claude') using STDIO transport.
# If you wanted to test this wrapper via HTTP/SSE, you would add:
# import uvicorn
# if __name__ == "__main__":
#     print("Wrapper MCP Server running (for HTTP/SSE testing).")
#     uvicorn.run(app, host="0.0.0.0", port=8000)
