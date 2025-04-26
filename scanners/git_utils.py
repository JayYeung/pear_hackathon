# scanners/git_utils.py
from pathlib import Path
from git import Repo
import tempfile

def clone_repo(url: str) -> Path:
    target = Path(tempfile.mkdtemp(prefix="securelaunch_"))
    Repo.clone_from(url, target, depth=1)
    return target
