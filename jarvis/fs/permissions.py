"""Permission checking utilities for Jarvis file system operations."""
from __future__ import annotations

import os
import pathlib


def can_read(path: pathlib.Path) -> bool:
    """Return True if the process has read permission on path."""
    return os.access(path, os.R_OK)


def can_write(path: pathlib.Path) -> bool:
    """Return True if the process has write permission on path or its parent."""
    if path.exists():
        return os.access(path, os.W_OK)
    # For new files/dirs, check parent directory writability
    return os.access(path.parent, os.W_OK)


def assert_readable(path: pathlib.Path) -> None:
    """Raise PermissionError if the process cannot read path."""
    if not can_read(path):
        raise PermissionError(f"Permission denied: cannot read '{path}'")


def assert_writable(path: pathlib.Path) -> None:
    """Raise PermissionError if the process cannot write to path."""
    if not can_write(path):
        raise PermissionError(f"Permission denied: cannot write to '{path}'")
