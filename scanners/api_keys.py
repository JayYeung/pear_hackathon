# scanners/api_keys.py
import subprocess, json, re, tempfile, shutil
from pathlib import Path

# quick-n-dirty secrets scan with trufflehog
def scan_api_keys(repo: Path):
    with tempfile.TemporaryDirectory() as t:
        out_file = Path(t, "results.json")
        subprocess.run(
            ["trufflehog", "filesystem", str(repo), "--json", "--output", out_file],
            check=False,
            capture_output=True,
        )
        if not out_file.exists():
            return []
        findings = json.loads(out_file.read_text())
        return [f'{i["Line"]}: {i["SourceType"]}' for i in findings]
