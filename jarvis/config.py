"""Shared configuration utility for Jarvis CLI.

All skills that need persistent settings should use this module
instead of managing ~/.jarvis/config.json directly.
"""
from __future__ import annotations

import json
import pathlib

CONFIG_FILE = pathlib.Path.home() / ".jarvis" / "config.json"


def load_config() -> dict:
    """Load ~/.jarvis/config.json, return {} on missing/corrupt."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(cfg: dict) -> None:
    """Write config dict to ~/.jarvis/config.json with indent=2."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def get(key: str, default=None):
    """Shorthand: load and return a single key."""
    return load_config().get(key, default)


def set(key: str, value) -> None:
    """Load, update one key, save."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
