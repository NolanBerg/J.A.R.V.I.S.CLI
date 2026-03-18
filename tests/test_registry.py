"""Tests for jarvis/core.py — skill registry and dispatch."""
from __future__ import annotations

import jarvis.core
from jarvis.core import dispatch, register


def test_register_adds_to_registry(clean_registry):
    @register("foo", description="Test skill")
    def handle_foo(raw: str) -> None:
        pass

    assert "foo" in jarvis.core._registry
    assert jarvis.core._registry["foo"].name == "foo"
    assert len(jarvis.core._skills) == 1


def test_register_with_aliases(clean_registry):
    @register("bar", aliases=["b", "baz"], description="Aliased skill")
    def handle_bar(raw: str) -> None:
        pass

    assert "bar" in jarvis.core._registry
    assert "b" in jarvis.core._registry
    assert "baz" in jarvis.core._registry
    # All keys point to the same Skill object
    assert jarvis.core._registry["bar"] is jarvis.core._registry["b"] is jarvis.core._registry["baz"]


def test_dispatch_exact_match(clean_registry):
    called_with = []

    @register("greet", description="Say hi")
    def handle_greet(raw: str) -> None:
        called_with.append(raw)

    assert dispatch("greet") is True
    assert called_with == ["greet"]


def test_dispatch_prefix_match(clean_registry):
    called_with = []

    @register("open", description="Open target")
    def handle_open(raw: str) -> None:
        called_with.append(raw)

    assert dispatch("open https://example.com") is True
    assert called_with == ["open https://example.com"]


def test_dispatch_no_match(clean_registry):
    assert dispatch("unknown_command") is False
