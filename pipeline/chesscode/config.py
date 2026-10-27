from pathlib import Path

import yaml

from .context import REPO_ROOT


def load(name: str, root: Path = REPO_ROOT) -> dict:
    path = root / "config" / (name if name.endswith(".yaml") else f"{name}.yaml")
    if not path.is_file():
        raise KeyError(f"Missing config file: {path}")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
