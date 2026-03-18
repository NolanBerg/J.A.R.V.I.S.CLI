"""Tests for jarvis/fs/paths.py — path resolution utilities."""
from __future__ import annotations

import pathlib

import pytest

from jarvis.fs.paths import resolve, resolve_pair


def test_resolve_expands_tilde():
    result = resolve("~/foo")
    assert result == pathlib.Path.home() / "foo"
    assert result.is_absolute()


def test_resolve_must_exist_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve(str(tmp_path / "nonexistent"), must_exist=True)


def test_resolve_must_exist_ok(tmp_path):
    f = tmp_path / "exists.txt"
    f.write_text("ok")
    result = resolve(str(f), must_exist=True)
    assert result == f


def test_resolve_pair(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    s, d = resolve_pair(str(src), str(tmp_path / "dst.txt"))
    assert s == src
    assert d == tmp_path / "dst.txt"


def test_resolve_pair_src_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_pair(str(tmp_path / "nope"), str(tmp_path / "dst"))
