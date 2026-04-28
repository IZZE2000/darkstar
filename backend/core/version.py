import os
import subprocess
from pathlib import Path

import yaml


def get_version() -> str:
    """Get app version from env, VERSION file, git tags, or add-on config."""

    def clean_v(s: str) -> str:
        s = s.strip()
        return s[1:] if s.lower().startswith("v") else s

    env_version = os.getenv("DARKSTAR_VERSION")
    if env_version:
        return clean_v(env_version)

    try:
        version_file = Path("VERSION")
        if version_file.exists():
            return clean_v(version_file.read_text())
    except Exception:
        pass

    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        git_ver = (
            subprocess.check_output(
                ["git", "describe", "--tags", "--abbrev=0"],
                stderr=subprocess.DEVNULL,
                cwd=str(project_root),
            )
            .decode()
            .strip()
        )
        if git_ver:
            return clean_v(git_ver)
    except Exception:
        pass

    try:
        with Path("darkstar/config.yaml").open() as f:
            addon_config = yaml.safe_load(f)
        if addon_config and addon_config.get("version"):
            return clean_v(addon_config["version"])
    except Exception:
        pass

    return "unknown"
