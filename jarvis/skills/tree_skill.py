"""Tree skill for Jarvis CLI.

Commands:
  tree [path] [depth]      Visual directory tree (default depth 3)
"""
from __future__ import annotations

import shlex
from pathlib import Path

from rich.console import Console

from jarvis.core import jarvis_say, register
from jarvis.fs.paths import resolve

_console = Console()

_MAX_ENTRIES = 500  # safety cap


@register("tree", description="Visual directory tree. Usage: tree [path] [depth]")
def handle_tree(raw: str) -> None:
    parts = raw.strip().split(None, 1)
    text = parts[1] if len(parts) > 1 else ""
    try:
        tokens = shlex.split(text)
    except ValueError:
        tokens = text.split()

    # Parse path and depth
    path_str = "."
    max_depth = 3

    for tok in tokens:
        if tok.isdigit():
            max_depth = int(tok)
        else:
            path_str = tok

    try:
        root = resolve(path_str, must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if not root.is_dir():
        jarvis_say(f"[red]Not a directory:[/red] {root}")
        return

    _console.print(f"[bold blue]{root.name}/[/bold blue]")
    count = _print_tree(root, max_depth, prefix="", count=0)
    _console.print(f"\n[dim]{count} entries[/dim]")


def _print_tree(directory: Path, max_depth: int, prefix: str, depth: int = 0, count: int = 0) -> int:
    if depth >= max_depth:
        return count

    try:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        _console.print(f"{prefix}[red][permission denied][/red]")
        return count

    total = len(entries)
    for i, entry in enumerate(entries):
        if count >= _MAX_ENTRIES:
            _console.print(f"{prefix}[dim]... truncated at {_MAX_ENTRIES} entries[/dim]")
            return count

        is_last = i == total - 1
        connector = "└── " if is_last else "├── "
        extension = "    " if is_last else "│   "

        if entry.is_symlink():
            try:
                target = entry.resolve()
                _console.print(f"{prefix}{connector}[cyan]{entry.name}[/cyan] → {target}")
            except OSError:
                _console.print(f"{prefix}{connector}[cyan]{entry.name}[/cyan] → [red]?[/red]")
            count += 1
        elif entry.is_dir():
            _console.print(f"{prefix}{connector}[bold blue]{entry.name}/[/bold blue]")
            count += 1
            count = _print_tree(entry, max_depth, prefix + extension, depth + 1, count)
        else:
            size = _compact_size(entry.stat().st_size)
            _console.print(f"{prefix}{connector}{entry.name}  [dim]{size}[/dim]")
            count += 1

    return count


def _compact_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.0f}K"
    return f"{size_bytes / 1024 ** 2:.1f}M"
