import subprocess
import os
import shutil
from mcp.fastmcp import create_app
from langchain_core.tools import tool
import uuid

# Define a base directory for cloning. Consider making this configurable.
WORKSPACE_BASE = os.path.abspath("./audit_workspace")

@tool
def clone_repository(repo_url: str) -> str:
    """Clones a Git repository to a unique temporary directory within the workspace.

    Args:
        repo_url: The URL of the Git repository to clone.

    Returns:
        The absolute path to the directory where the repository was cloned,
        or an error message starting with 'Error:'.
    """
    if not os.path.exists(WORKSPACE_BASE):
        try:
            os.makedirs(WORKSPACE_BASE)
        except OSError as e:
            return f"Error: Could not create workspace directory '{WORKSPACE_BASE}': {e}"

    # Create a unique directory for this clone
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    clone_dir = os.path.join(WORKSPACE_BASE, f"{repo_name}_{uuid.uuid4().hex[:8]}")

    command = ["git", "clone", "--depth", "1", repo_url, clone_dir]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        print(f"Clone stdout: {result.stdout}")
        print(f"Clone stderr: {result.stderr}")
        return clone_dir
    except subprocess.CalledProcessError as e:
        # Clean up failed clone attempt
        if os.path.exists(clone_dir):
            shutil.rmtree(clone_dir)
        return f"Error: Git clone failed for {repo_url}: {e}\nStderr: {e.stderr}"
    except FileNotFoundError:
        return "Error: 'git' command not found. Is Git installed and in the PATH?"
    except Exception as e:
        # Catch other potential errors
        if os.path.exists(clone_dir):
            shutil.rmtree(clone_dir)
        return f"Error: An unexpected error occurred during clone: {e}"

# Create the FastAPI app exposing the tool via MCP
# This server expects to be run via STDIO when launched by MultiServerMCPClient
app = create_app([clone_repository])

# Example for running standalone (HTTP/SSE) for testing:
# import uvicorn
# if __name__ == "__main__":
#     print(f"Git MCP Server running. Workspace: {WORKSPACE_BASE}")
#     # Ensure WORKSPACE_BASE exists if running standalone
#     if not os.path.exists(WORKSPACE_BASE):
#         os.makedirs(WORKSPACE_BASE)
#     uvicorn.run(app, host="0.0.0.0", port=8001)
