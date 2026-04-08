"""jarvis_config.py -- Shared Jarvis constants.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

from pathlib import Path

# Filenames (not paths) that NO automated tool may modify or delete.
PROTECTED_FILES: set[str] = {
    "TELOS.md",
    "constitutional-rules.md",
    "CLAUDE.md",
}

# Relative path prefixes (from repo root) whose contents are also protected.
PROTECTED_DIR_PREFIXES: set[str] = {
    "memory/work/telos/",
}


def is_protected(path: Path, repo_root: Path) -> bool:
    """Return True if path is a protected file or lives under a protected directory.

    Checks:
      1. Filename is in PROTECTED_FILES.
      2. Path relative to repo_root starts with any prefix in PROTECTED_DIR_PREFIXES.
    """
    if path.name in PROTECTED_FILES:
        return True
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
        rel_str = rel.as_posix() + ("/" if path.is_dir() else "")
        for prefix in PROTECTED_DIR_PREFIXES:
            if rel_str.startswith(prefix):
                return True
    except ValueError:
        pass
    return False
