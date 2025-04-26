# scanners/input_security.py
import subprocess, json, tempfile
from pathlib import Path

def scan_inputs(repo: Path):
    with tempfile.TemporaryDirectory() as t:
        ruleset = "p/ci"      # semgrep managed rules
        cmd = ["semgrep", "scan", "--json", "--config", ruleset, str(repo)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        data = json.loads(result.stdout or "{}")
        return [f'{d["path"]}:{d["start"]["line"]} – {d["check_id"]}'
                for d in data.get("results", [])]
