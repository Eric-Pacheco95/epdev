"""Cross-platform file locking helpers for serializing concurrent writers.

Two patterns are exposed:

1. `locked_append(path, line)` -- safe append to a JSONL/text file under a
   per-file advisory lock. Use for high-frequency append-only writers like
   hook event logs.

2. `locked_read_modify_write(path, mutator)` -- load a JSON state file,
   apply a mutator function, and persist atomically under an exclusive
   sidecar lock. Use for state files like followon_state.json where
   read-modify-write races otherwise lose updates.

Locking strategy:
  - Windows: msvcrt.locking() byte-range lock on the target file (append)
    or on a sidecar `.lock` file (read-modify-write).
  - POSIX: fcntl.flock() equivalent, with the same sidecar pattern.
  - Fallback (lock unavailable): operation proceeds without serialization
    rather than failing -- callers should treat lock-helper unavailability
    as a soft warning, not a hard error.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Callable


def locked_append(path: Path, line: str, encoding: str = "utf-8") -> None:
    """Append a single line to `path` under an advisory lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not line.endswith("\n"):
        line = line + "\n"
    try:
        import msvcrt
        with path.open("a", encoding=encoding) as fh:
            try:
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
                fh.write(line)
            finally:
                try:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
        return
    except ImportError:
        pass
    except OSError:
        pass
    try:
        import fcntl
        with path.open("a", encoding=encoding) as fh:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                fh.write(line)
            finally:
                try:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
        return
    except (ImportError, OSError):
        pass
    with path.open("a", encoding=encoding) as fh:
        fh.write(line)


def locked_read_modify_write(
    path: Path,
    mutator: Callable[[dict], dict],
    default: dict | None = None,
) -> dict:
    """Load JSON from `path`, apply `mutator(state) -> new_state`, persist atomically.

    Serialized via a sidecar `.lock` file so concurrent callers do not race.
    Returns the new state dict.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.touch(exist_ok=True)

    lock_fh = open(lock_path, "r+b")
    locked = False
    try:
        try:
            import msvcrt
            while True:
                try:
                    msvcrt.locking(lock_fh.fileno(), msvcrt.LK_LOCK, 1)
                    locked = True
                    break
                except OSError:
                    continue
        except ImportError:
            try:
                import fcntl
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
                locked = True
            except (ImportError, OSError):
                pass

        state: dict = default.copy() if default else {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    state = loaded
            except (json.JSONDecodeError, OSError):
                pass

        new_state = mutator(state)
        if not isinstance(new_state, dict):
            raise TypeError(f"mutator must return dict, got {type(new_state).__name__}")

        fd, tmp_name = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_fh:
                json.dump(new_state, tmp_fh, indent=2)
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

        return new_state
    finally:
        if locked:
            try:
                import msvcrt
                msvcrt.locking(lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
            except (ImportError, OSError):
                try:
                    import fcntl
                    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
                except (ImportError, OSError):
                    pass
        lock_fh.close()
