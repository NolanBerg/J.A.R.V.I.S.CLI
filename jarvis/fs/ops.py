"""CRUD file system operations for Jarvis.

All functions raise standard stdlib exceptions on failure:
  - FileNotFoundError: path does not exist
  - PermissionError: insufficient access
  - IsADirectoryError: expected file, got directory (or vice versa)
  - ValueError: invalid operation (e.g. file too large to read)
  - OSError: other OS-level errors

No jarvis_say calls here — this module is a pure logic layer.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import stat as stat_module
import time
from datetime import datetime
from typing import NamedTuple

from jarvis.fs.permissions import assert_readable, assert_writable

CAT_SIZE_LIMIT = 50 * 1024  # 50 KB


class DirEntry(NamedTuple):
    name: str
    kind: str  # 'd', 'f', 'l', '?'
    size: int  # bytes; 0 for directories


def fs_ls(path: pathlib.Path) -> list[DirEntry]:
    """List directory contents sorted dirs-first, then files (alphabetical).

    Returns:
        List of DirEntry namedtuples.
    """
    assert_readable(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file or directory: '{path}'")
    if not path.is_dir():
        raise NotADirectoryError(f"Not a directory: '{path}'")

    entries: list[DirEntry] = []
    for item in path.iterdir():
        if item.is_symlink():
            kind = "l"
            size = 0
        elif item.is_dir():
            kind = "d"
            size = 0
        elif item.is_file():
            kind = "f"
            size = item.stat().st_size
        else:
            kind = "?"
            size = 0
        entries.append(DirEntry(name=item.name, kind=kind, size=size))

    entries.sort(key=lambda e: (0 if e.kind == "d" else 1, e.name.lower()))
    return entries


def fs_cat(path: pathlib.Path) -> str:
    """Return file text content.

    Raises:
        FileNotFoundError: path does not exist
        IsADirectoryError: path is a directory
        ValueError: file exceeds CAT_SIZE_LIMIT
        PermissionError: insufficient read access
    """
    assert_readable(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file or directory: '{path}'")
    if path.is_dir():
        raise IsADirectoryError(f"Is a directory: '{path}'")

    file_size = path.stat().st_size
    if file_size > CAT_SIZE_LIMIT:
        raise ValueError(
            f"File is {file_size // 1024} KB — exceeds the {CAT_SIZE_LIMIT // 1024} KB "
            "read limit. Use a text editor for large files."
        )

    return path.read_text(encoding="utf-8", errors="replace")


def fs_stat(path: pathlib.Path) -> dict[str, str]:
    """Return a dict of file/directory metadata.

    Keys: type, size, permissions, modified, created, owner
    """
    assert_readable(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file or directory: '{path}'")

    st = path.stat()

    # Determine type
    if path.is_symlink():
        ftype = f"symlink → {os.readlink(path)}"
    elif path.is_dir():
        ftype = "directory"
    elif path.is_file():
        ftype = "file"
    else:
        ftype = "other"

    # Human-readable size
    size_bytes = st.st_size
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        size_str = f"{size_bytes / 1024:.1f} KB"
    else:
        size_str = f"{size_bytes / 1024 ** 2:.1f} MB"

    # Permissions string (e.g. rwxr-xr--)
    mode = st.st_mode
    perms = stat_module.filemode(mode)

    # Timestamps
    modified = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    created = datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S")

    # Owner
    try:
        import pwd
        owner = pwd.getpwuid(st.st_uid).pw_name
    except (ImportError, KeyError):
        owner = str(st.st_uid)

    return {
        "path": str(path),
        "type": ftype,
        "size": size_str,
        "permissions": perms,
        "modified": modified,
        "created": created,
        "owner": owner,
    }


def fs_mkdir(path: pathlib.Path) -> None:
    """Create directory and all parents. No-op if already exists."""
    assert_writable(path)
    path.mkdir(parents=True, exist_ok=True)


def fs_touch(path: pathlib.Path) -> None:
    """Create empty file or update mtime. Creates parent dirs if needed."""
    assert_writable(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def fs_rm(path: pathlib.Path, recursive: bool = False) -> None:
    """Delete file or directory.

    Raises:
        FileNotFoundError: path does not exist
        IsADirectoryError: path is a directory and recursive=False
        PermissionError: write access denied
    """
    if not path.exists() and not path.is_symlink():
        raise FileNotFoundError(f"No such file or directory: '{path}'")
    assert_writable(path)

    if path.is_dir() and not path.is_symlink():
        if not recursive:
            raise IsADirectoryError(
                f"'{path}' is a directory. Use --recursive / -r to delete it."
            )
        shutil.rmtree(path)
    else:
        path.unlink()


def fs_mv(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Move/rename src to dst. Uses shutil.move for cross-device safety."""
    assert_readable(src)
    assert_writable(src)
    assert_writable(dst)
    shutil.move(str(src), str(dst))


def fs_cp(src: pathlib.Path, dst: pathlib.Path) -> None:
    """Copy file or directory tree.

    Uses shutil.copy2 for files (preserves metadata),
    shutil.copytree for directories.
    """
    assert_readable(src)
    assert_writable(dst)
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)
