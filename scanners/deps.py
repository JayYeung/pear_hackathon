# scanners/deps.py
import subprocess, json, os
from pathlib import Path

def scan_dependencies(repo: Path):
    req = next(repo.glob("**/requirements*.txt"), None)
    if not req:
        return ["No Python requirements file found"]
    result = subprocess.run(
        ["pip-audit", "-r", str(req), "-f", "json"],
        capture_output=True, text=True, check=False
    )
    audits = json.loads(result.stdout or "[]")
    return [f'{a["name"]} {a["version"]} – {a["id"]} ({a["fix_versions"]})'
            for a in audits]
