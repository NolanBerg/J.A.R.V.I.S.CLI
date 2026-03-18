"""Tests for jarvis/fs/ops.py — pure file system operations."""
from __future__ import annotations

import pathlib

import pytest

from jarvis.fs.ops import (
    CAT_SIZE_LIMIT,
    fs_cat,
    fs_cp,
    fs_find,
    fs_grep,
    fs_ls,
    fs_mkdir,
    fs_mv,
    fs_rm,
    fs_stat,
    fs_touch,
)


# ---------------------------------------------------------------------------
# fs_ls
# ---------------------------------------------------------------------------

def test_fs_ls_returns_entries(tmp_tree):
    entries = fs_ls(tmp_tree)
    names = [e.name for e in entries]
    assert "subdir" in names
    assert "hello.txt" in names
    # Dirs should come first
    assert entries[0].kind == "d"


def test_fs_ls_nonexistent(tmp_path):
    with pytest.raises((FileNotFoundError, PermissionError)):
        fs_ls(tmp_path / "nope")


# ---------------------------------------------------------------------------
# fs_cat
# ---------------------------------------------------------------------------

def test_fs_cat_reads_content(tmp_tree):
    content = fs_cat(tmp_tree / "hello.txt")
    assert content == "hello world"


def test_fs_cat_too_large(tmp_path):
    big = tmp_path / "big.bin"
    big.write_bytes(b"x" * (CAT_SIZE_LIMIT + 1))
    with pytest.raises(ValueError, match="exceeds"):
        fs_cat(big)


def test_fs_cat_directory(tmp_tree):
    with pytest.raises(IsADirectoryError):
        fs_cat(tmp_tree / "subdir")


# ---------------------------------------------------------------------------
# fs_stat
# ---------------------------------------------------------------------------

def test_fs_stat_returns_metadata(tmp_tree):
    info = fs_stat(tmp_tree / "hello.txt")
    assert "path" in info
    assert info["type"] == "file"
    assert "size" in info
    assert "permissions" in info
    assert "modified" in info
    assert "created" in info
    assert "owner" in info


# ---------------------------------------------------------------------------
# fs_mkdir / fs_touch
# ---------------------------------------------------------------------------

def test_fs_mkdir_creates_nested(tmp_path):
    # Single level — parent exists and is writable
    target = tmp_path / "newdir"
    fs_mkdir(target)
    assert target.is_dir()


def test_fs_touch_creates_file(tmp_path):
    target = tmp_path / "new.txt"
    fs_touch(target)
    assert target.exists()
    assert target.stat().st_size == 0


# ---------------------------------------------------------------------------
# fs_rm
# ---------------------------------------------------------------------------

def test_fs_rm_file(tmp_tree):
    target = tmp_tree / "hello.txt"
    fs_rm(target)
    assert not target.exists()


def test_fs_rm_dir_without_recursive(tmp_tree):
    with pytest.raises(IsADirectoryError):
        fs_rm(tmp_tree / "subdir")


def test_fs_rm_dir_recursive(tmp_tree):
    target = tmp_tree / "subdir"
    fs_rm(target, recursive=True)
    assert not target.exists()


# ---------------------------------------------------------------------------
# fs_mv / fs_cp
# ---------------------------------------------------------------------------

def test_fs_mv(tmp_tree):
    src = tmp_tree / "hello.txt"
    dst = tmp_tree / "renamed.txt"
    fs_mv(src, dst)
    assert not src.exists()
    assert dst.read_text() == "hello world"


def test_fs_cp(tmp_tree):
    src = tmp_tree / "hello.txt"
    dst = tmp_tree / "copy.txt"
    fs_cp(src, dst)
    assert src.exists()
    assert dst.read_text() == "hello world"


# ---------------------------------------------------------------------------
# fs_find
# ---------------------------------------------------------------------------

def test_fs_find_glob(tmp_tree):
    results = fs_find(tmp_tree, "*.py")
    names = [p.name for p in results]
    assert "nested.py" in names


def test_fs_find_substring(tmp_tree):
    results = fs_find(tmp_tree, "hello")
    names = [p.name for p in results]
    assert "hello.txt" in names


# ---------------------------------------------------------------------------
# fs_grep
# ---------------------------------------------------------------------------

def test_fs_grep_match(tmp_tree):
    matches = fs_grep("hello", tmp_tree / "hello.txt")
    assert len(matches) == 1
    assert matches[0].lineno == 1
    assert "hello" in matches[0].line


def test_fs_grep_no_match(tmp_tree):
    matches = fs_grep("xyz", tmp_tree / "hello.txt")
    assert matches == []
