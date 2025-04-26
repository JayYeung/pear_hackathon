from pathlib import Path
from typing import List
from fastmcp import FastMCP

from scanners.git_utils import clone_repo
from scanners.api_keys import scan_api_keys
from scanners.input_security import scan_inputs
from scanners.deps import scan_dependencies

mcp = FastMCP("SecureLaunch")

@ mcp.tool()
def checkout_repo(github_url: str) -> str:
    """Clone the repo and return the local path."""
    return str(clone_repo(github_url))

@ mcp.tool()
def api_key_inspector(repo_path: str) -> List[str]:
    """Return any suspected secrets in the repo."""
    return scan_api_keys(Path(repo_path))

@ mcp.tool()
def input_security_analyzer(repo_path: str) -> List[str]:
    """Return potential XSS / SQL-i / etc. findings."""
    return scan_inputs(Path(repo_path))

@ mcp.tool()
def dependency_audit(repo_path: str) -> List[str]:
    """Return vulnerable dependency records."""
    return scan_dependencies(Path(repo_path))

if __name__ == "__main__":
    mcp.run()          # local dev → `fastmcp dev server.py`
