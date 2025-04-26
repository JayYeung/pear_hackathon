import subprocess
import os
import json
from mcp.fastmcp import create_app
from langchain_core.tools import tool

from typing import Annotated

@tool
def run_semgrep_scan(
    repo_path: Annotated[str, "The local path to the cloned repository."],
    config: Annotated[str, "Semgrep rules configuration, e.g., 'auto', 'p/ci', 'r/python'."]
) -> str:
    """Runs Semgrep scan on the specified repository path and returns JSON output.

    Args:
        repo_path: The local path to the cloned repository.
        config: Semgrep rules configuration (e.g., 'auto', 'p/ci', 'r/python'). Default is 'auto'.

    Returns:
        A JSON string representing the Semgrep scan results,
        or an error message starting with 'Error:'.
    """
    if not os.path.isdir(repo_path):
        return json.dumps({"error": f"Repository path '{repo_path}' not found or not a directory."})

    command = ["semgrep", "scan", "--config", config, "--json", "."]
    try:
        # Run semgrep from within the repo directory
        result = subprocess.run(command, capture_output=True, text=True, check=True, cwd=repo_path)
        # Validate if the output is JSON before returning
        try:
            json.loads(result.stdout)
            return result.stdout
        except json.JSONDecodeError:
             return json.dumps({"error": "Semgrep ran but did not produce valid JSON output.", "stdout": result.stdout, "stderr": result.stderr})

    except subprocess.CalledProcessError as e:
        return json.dumps({"error": f"Semgrep scan failed with exit code {e.returncode}", "stderr": e.stderr, "stdout": e.stdout})
    except FileNotFoundError:
        return json.dumps({"error": "'semgrep' command not found. Is Semgrep installed and in the PATH?"})
    except Exception as e:
        return json.dumps({"error": f"An unexpected error occurred during Semgrep scan: {e}"})

# Create the FastAPI app exposing the tool via MCP
# This server expects to be run via STDIO when launched by MultiServerMCPClient
app = create_app([run_semgrep_scan])

# Example for running standalone (HTTP/SSE) for testing:
# import uvicorn
# if __name__ == "__main__":
#     print("Semgrep MCP Server running.")
#     uvicorn.run(app, host="0.0.0.0", port=8002)
