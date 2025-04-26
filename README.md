# SecureLaunch

A security scanning tool for code repositories that checks for:

-   API key/secret exposures
-   Dependency vulnerabilities
-   Input security issues (XSS, SQL injection, etc.)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Start the server:

```bash
fastmcp dev server.py
```

Add to Claude Code:

```bash
claude mcp add securelaunch -- fastmcp run server.py
```

The server exposes endpoints that allow:

-   Repository cloning
-   API key scanning
-   Dependency vulnerability auditing
-   Input security analysis

## Utilities

-   `git_utils.py` - Git repository operations
-   `api_keys.py` - API key/secret scanning
-   `deps.py` - Dependency vulnerability scanning
-   `input_security.py` - Input security vulnerability detection

## License

MIT
