"""JSON skill for Jarvis CLI.

Commands:
  json <file>              Pretty-print a JSON file
  json <file> <query>      Extract a value by dotted key path (supports array indices)
"""
from __future__ import annotations

import json
import shlex

from rich.console import Console
from rich.syntax import Syntax

from jarvis.core import jarvis_say, register
from jarvis.fs.paths import resolve

_console = Console()

_MAX_SIZE = 2 * 1024 * 1024  # 2 MB


def _tokens(raw: str) -> list[str]:
    parts = raw.strip().split(None, 1)
    text = parts[1] if len(parts) > 1 else ""
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


def _query(data, path: str):
    """Walk a dotted path like 'users[0].name' into nested data."""
    if not path or path == ".":
        return data

    # Normalise: "users[0].name" → ["users", "0", "name"]
    import re
    keys = re.split(r'\.|\[|\]', path)
    keys = [k for k in keys if k]  # drop empties

    current = data
    for key in keys:
        if isinstance(current, dict):
            if key not in current:
                raise KeyError(f"Key '{key}' not found. Available: {', '.join(current.keys())}")
            current = current[key]
        elif isinstance(current, list):
            try:
                idx = int(key)
            except ValueError:
                raise KeyError(f"Expected integer index for list, got '{key}'")
            if idx < 0 or idx >= len(current):
                raise IndexError(f"Index {idx} out of range (length {len(current)})")
            current = current[idx]
        else:
            raise KeyError(f"Cannot index into {type(current).__name__} with '{key}'")
    return current


@register("json", description="Pretty-print or query JSON files. Usage: json <file> [query]")
def handle_json(raw: str) -> None:
    tokens = _tokens(raw)
    if not tokens:
        jarvis_say("Usage: json <file> [query]")
        return

    try:
        path = resolve(tokens[0], must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if path.is_dir():
        jarvis_say(f"[red]Is a directory:[/red] {path}")
        return

    file_size = path.stat().st_size
    if file_size > _MAX_SIZE:
        jarvis_say(f"[yellow]File is {file_size // 1024} KB — exceeds 2 MB limit.[/yellow]")
        return

    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
        return
    except OSError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        jarvis_say(f"[red]Invalid JSON:[/red] {e}")
        return

    # If a query path is provided, extract that value
    if len(tokens) > 1:
        query_path = tokens[1]
        try:
            result = _query(data, query_path)
        except (KeyError, IndexError) as e:
            jarvis_say(f"[red]Query error:[/red] {e}")
            return

        # Pretty-print the result
        if isinstance(result, (dict, list)):
            formatted = json.dumps(result, indent=2, ensure_ascii=False)
            _console.print(Syntax(formatted, "json", theme="monokai", word_wrap=True))
        else:
            jarvis_say(str(result))
        return

    # Full pretty-print
    formatted = json.dumps(data, indent=2, ensure_ascii=False)
    _console.print(Syntax(formatted, "json", theme="monokai", word_wrap=True))
