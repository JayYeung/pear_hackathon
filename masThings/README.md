# Multi-Agent Security Auditor with MCP

This project implements a multi-agent system for autonomous codebase security auditing.
It uses LangGraph for orchestration and MCP (Multi-Agent Communication Protocol) for communication between the orchestrator and specialized tool servers.

The entire pipeline is exposed as a single MCP server (`wrapper_mcp_server.py`) designed to be callable by MCP clients like the `claude` CLI.

## Project Structure

```
/
├── mcp_servers/          # Individual MCP servers wrapping tools
│   ├── git_mcp_server.py
│   └── semgrep_mcp_server.py
│   └── ...               # Future servers (dependencies, secrets, etc.)
├── pipeline/             # LangGraph orchestration logic
│   ├── __init__.py
│   └── orchestrator.py
├── wrapper_mcp_server.py # Top-level MCP server callable by clients
├── requirements.txt      # Python dependencies
├── audit_workspace/      # Directory created dynamically for cloned repos (can be deleted)
├── .env                  # For API keys (create this file)
└── README.md             # This file
```

## Setup

1.  **Prerequisites:**
    *   Python 3.9+
    *   `git` installed and in PATH.
    *   `semgrep` installed and in PATH (`pip install semgrep`).

2.  **Clone the repository (if applicable):**
    ```bash
    # git clone ...
    # cd your-repo-name
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: This now includes `langchain-anthropic`.*

4.  **Set up API Keys:**
    *   Create a file named `.env` in the project root.
    *   Add your LLM provider API key. For Anthropic:
        ```
        ANTHROPIC_API_KEY='your-anthropic-api-key'
        ```
    *   Replace `'your-anthropic-api-key'` with your real key.
    *   The `wrapper_mcp_server.py` and `pipeline/orchestrator.py` will load this using `python-dotenv`.

## Running the Pipeline via the Wrapper MCP Server

The `wrapper_mcp_server.py` is designed to be run directly by an MCP client using STDIO transport. The `MultiServerMCPClient` within the orchestrator will automatically start the `git_mcp_server.py` and `semgrep_mcp_server.py` using their specified commands.

**To run with the `claude` CLI:**

1.  **Register the wrapper server with `claude`:**
    Open your terminal in the project's root directory.
    Run the following command, replacing `/Users/seantai/Desktop/pearVCanthropic` with the actual absolute path to your project directory if it differs:

    ```bash
    claude mcp add security-auditor python /Users/seantai/Desktop/pearVCanthropic/wrapper_mcp_server.py
    ```

    *   `security-auditor`: This is the name you'll use to refer to the tool in Claude.
    *   `python`: The command to run the server script.
    *   `/path/to/wrapper_mcp_server.py`: The absolute path to the wrapper script.

2.  **Invoke the tool in a Claude session:**
    Start a `claude` session. You can now ask Claude to use the tool:

    ```
    > Use the security-auditor tool to start an audit for https://github.com/octocat/Spoon-Knife
    ```
    or
    ```
    > @security-auditor(repo_url="https://github.com/octocat/Spoon-Knife")
    ```

    Claude will execute the `wrapper_mcp_server.py` script. This script will:
    *   Load environment variables.
    *   Call `run_security_audit_pipeline`.
    *   The pipeline will start the Git and Semgrep MCP servers via STDIO.
    *   The LangGraph agent (powered by Anthropic Claude) will orchestrate calls to these servers (clone, scan).
    *   The final summary will be returned to Claude.

## Development & Testing Notes

*   **Standalone Server Testing:** You can uncomment the `uvicorn` sections in the individual MCP server files (`git_mcp_server.py`, `semgrep_mcp_server.py`) to run them standalone via HTTP/SSE for direct testing if needed (e.g., using `curl` or a simple client script).
*   **Workspace Cleanup:** The `audit_workspace` directory will accumulate cloned repositories. You may want to add cleanup logic or manually delete it periodically.
*   **Error Handling:** The current error handling is basic. Robust implementation would require more detailed error capture and reporting.
*   **Adding More Agents:** To add more tools (dependency scan, secrets, etc.):
    1.  Create a new `*_mcp_server.py` in `mcp_servers/`.
    2.  Define the LangChain tool(s) within it.
    3.  Add the server configuration to `server_configs` in `pipeline/orchestrator.py`.
    4.  Update the LangGraph logic in `pipeline/orchestrator.py` to use the new tool(s).
