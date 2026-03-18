"""Tests for jarvis/ai/context.py — command context builder."""
from __future__ import annotations

from jarvis.ai.context import build_context
from jarvis.core import register


def test_build_context_structure(clean_registry):
    @register("test_cmd", aliases=["tc"], description="A test command")
    def handle_test(raw: str) -> None:
        pass

    ctx = build_context()
    assert ctx["application"] == "Jarvis CLI"
    assert "version" in ctx
    assert isinstance(ctx["commands"], list)
    assert len(ctx["commands"]) == 1
    assert ctx["commands"][0]["name"] == "test_cmd"
    assert ctx["commands"][0]["aliases"] == ["tc"]
    assert ctx["commands"][0]["description"] == "A test command"
