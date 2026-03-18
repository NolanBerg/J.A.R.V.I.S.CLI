"""Shared fixtures for Jarvis tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def tmp_tree(tmp_path):
    """Create a small file tree for FS tests."""
    (tmp_path / "hello.txt").write_text("hello world")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.py").write_text("print('hi')")
    return tmp_path


@pytest.fixture
def clean_registry(monkeypatch):
    """Isolate the skill registry for each test."""
    monkeypatch.setattr("jarvis.core._registry", {})
    monkeypatch.setattr("jarvis.core._skills", [])
