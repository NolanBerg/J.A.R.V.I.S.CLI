"""Path resolution utilities for Jarvis file system operations."""
from __future__ import annotations

import pathlib


def resolve(raw: str, must_exist: bool = False) -> pathlib.Path:
    """Expand ~, resolve . and .., return absolute Path.

    Args:
        raw: Raw path string from user input.
        must_exist: If True, raises FileNotFoundError when path is absent.

    Returns:
        Resolved absolute pathlib.Path.
    """
    path = pathlib.Path(raw).expanduser().resolve()
    if must_exist and not path.exists():
        raise FileNotFoundError(f"No such file or directory: '{path}'")
    return path


def resolve_pair(
    raw_src: str, raw_dst: str
) -> tuple[pathlib.Path, pathlib.Path]:
    """Resolve source (must exist) and destination (need not exist) for mv/cp.

    Args:
        raw_src: Source path string.
        raw_dst: Destination path string.

    Returns:
        Tuple of (src, dst) as resolved absolute paths.
    """
    src = resolve(raw_src, must_exist=True)
    dst = resolve(raw_dst, must_exist=False)
    return src, dst
