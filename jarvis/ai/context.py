"""Builds and caches ~/.jarvis/commands.json from the live skill registry."""
from __future__ import annotations

import json
import pathlib

JARVIS_DIR = pathlib.Path.home() / ".jarvis"
COMMANDS_FILE = JARVIS_DIR / "commands.json"


def build_context() -> dict:
    """Build the commands context dict from the live registry."""
    from jarvis import __version__
    from jarvis.core import _skills

    return {
        "application": "Jarvis CLI",
        "version": __version__,
        "description": "A Python CLI assistant with a skill-based command registry.",
        "commands": [
            {
                "name": skill.name,
                "aliases": skill.aliases,
                "description": skill.description,
            }
            for skill in _skills
        ],
    }


def get_commands_json() -> str:
    """Return a JSON string of available commands, always built from the live registry."""
    return json.dumps(build_context(), indent=2)


def refresh_cache() -> None:
    """Force-regenerate ~/.jarvis/commands.json from the current registry."""
    JARVIS_DIR.mkdir(parents=True, exist_ok=True)
    _write_cache()


def _write_cache() -> None:
    ctx = build_context()
    COMMANDS_FILE.write_text(json.dumps(ctx, indent=2), encoding="utf-8")
