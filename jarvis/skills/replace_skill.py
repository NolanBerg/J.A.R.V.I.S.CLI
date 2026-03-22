"""Replace skill for Jarvis CLI.

Commands:
  replace <old> <new> <file>       Replace all occurrences in a file
  replace -n <old> <new> <file>    Dry run — show changes without writing
"""
from __future__ import annotations

import shlex

from rich.console import Console

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


@register("replace", aliases=["sub"], description="Find and replace in files. Usage: replace <old> <new> <file> [-n for dry run]")
def handle_replace(raw: str) -> None:
    tokens = _tokens(raw)

    # Parse flags
    dry_run = False
    positional = []
    for t in tokens:
        if t in ("-n", "--dry-run"):
            dry_run = True
        else:
            positional.append(t)

    if len(positional) < 3:
        jarvis_say("Usage: replace <old> <new> <file> [-n for dry run]")
        return

    old, new, file_str = positional[0], positional[1], positional[2]

    try:
        path = resolve(file_str, must_exist=True)
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

    count = content.count(old)
    if count == 0:
        jarvis_say(f"[dim]No occurrences of '{old}' in {path.name}.[/dim]")
        return

    # Show preview of changes
    lines = content.splitlines(keepends=True)
    shown = 0
    for i, line in enumerate(lines, 1):
        if old in line:
            before_display = line.rstrip("\n").replace(old, f"[red]{old}[/red]")
            after_display = line.rstrip("\n").replace(old, f"[green]{new}[/green]")
            _console.print(f"  [dim]L{i}:[/dim] {before_display}")
            _console.print(f"  [dim]  →[/dim] {after_display}")
            shown += 1
            if shown >= 10:
                remaining = count - shown
                if remaining > 0:
                    _console.print(f"  [dim]... and {remaining} more occurrence(s)[/dim]")
                break

    if dry_run:
        jarvis_say(f"[yellow]Dry run:[/yellow] {count} occurrence(s) would be replaced.")
        return

    # Apply replacement
    new_content = content.replace(old, new)
    try:
        path.write_text(new_content, encoding="utf-8")
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
        return
    except OSError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    jarvis_say(f"[green]Replaced {count} occurrence(s)[/green] in {path.name}.")
