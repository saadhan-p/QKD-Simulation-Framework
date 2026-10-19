"""
experiments/scripts/sweep_metadata.py
=====================================
Utility to record run metadata (interpreter, package versions, git commit, seed)
next to every sweep output file.
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def save_sweep_metadata(
    output_file: Path | str,
    seed: int,
    extra: dict | None = None,
) -> Path:
    """Save metadata JSON next to output_file.

    File is named: <output_file>.metadata.json
    """
    output_path = Path(output_file)

    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=output_path.parent,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        git_hash = "unknown"

    packages = {}
    for pkg in [
        "numpy",
        "fastapi",
        "uvicorn",
        "pytest",
        "pydantic",
        "PyQt5",
        "pyqtgraph",
        "matplotlib",
    ]:
        try:
            import importlib.metadata
            packages[pkg] = importlib.metadata.version(pkg)
        except Exception:
            pass

    meta = {
        "timestamp": datetime.now().isoformat(),
        "seed": seed,
        "interpreter": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "git_commit": git_hash,
        "packages": packages,
    }
    if extra:
        meta.update(extra)

    meta_path = output_path.with_name(f"{output_path.stem}.metadata.json")
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return meta_path
