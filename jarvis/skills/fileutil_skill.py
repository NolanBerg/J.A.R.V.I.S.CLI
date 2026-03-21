"""File utility skills for Jarvis CLI.

Commands:
  head [N] <file>           Show first N lines (default 10)
  tail [N] <file>           Show last N lines (default 10)
  wc <file>                 Line, word, and character counts
  diff <file1> <file2>      Unified diff between two files
  du [path]                 Directory size summary
"""
from __future__ import annotations

import difflib
import os
import pathlib
import shlex

from rich.console import Console
from rich.table import Table
from rich.text import Text

from jarvis.core import jarvis_say, register
from jarvis.fs.paths import resolve

_console = Console()


def _tokens(raw: str) -> list[str]:
    parts = raw.strip().split(None, 1)
    text = parts[1] if len(parts) > 1 else ""
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


# ---------------------------------------------------------------------------
# head
# ---------------------------------------------------------------------------

@register("head", description="Show first N lines of a file. Usage: head [N] <file>")
def handle_head(raw: str) -> None:
    tokens = _tokens(raw)
    if not tokens:
        jarvis_say("Usage: head [N] <file>")
        return

    # Parse optional line count
    n = 10
    if tokens[0].isdigit():
        n = int(tokens[0])
        tokens = tokens[1:]
    elif tokens[0].startswith("-") and tokens[0][1:].isdigit():
        n = int(tokens[0][1:])
        tokens = tokens[1:]

    if not tokens:
        jarvis_say("Usage: head [N] <file>")
        return

    try:
        path = resolve(tokens[0], must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if path.is_dir():
        jarvis_say(f"[red]Is a directory:[/red] {path}")
        return

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = []
            for i, line in enumerate(f):
                if i >= n:
                    break
                lines.append(line)
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
        return
    except OSError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    jarvis_say(f"[dim]First {len(lines)} line(s) of {path.name}[/dim]")
    _console.print("".join(lines), highlight=False, end="")
    _console.print()


# ---------------------------------------------------------------------------
# tail
# ---------------------------------------------------------------------------

@register("tail", description="Show last N lines of a file. Usage: tail [N] <file>")
def handle_tail(raw: str) -> None:
    tokens = _tokens(raw)
    if not tokens:
        jarvis_say("Usage: tail [N] <file>")
        return

    n = 10
    if tokens[0].isdigit():
        n = int(tokens[0])
        tokens = tokens[1:]
    elif tokens[0].startswith("-") and tokens[0][1:].isdigit():
        n = int(tokens[0][1:])
        tokens = tokens[1:]

    if not tokens:
        jarvis_say("Usage: tail [N] <file>")
        return

    try:
        path = resolve(tokens[0], must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if path.is_dir():
        jarvis_say(f"[red]Is a directory:[/red] {path}")
        return

    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
        return
    except OSError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    tail_lines = all_lines[-n:] if len(all_lines) > n else all_lines
    jarvis_say(f"[dim]Last {len(tail_lines)} line(s) of {path.name}[/dim]")
    _console.print("".join(tail_lines), highlight=False, end="")
    _console.print()


# ---------------------------------------------------------------------------
# wc
# ---------------------------------------------------------------------------

@register("wc", description="Count lines, words, and characters. Usage: wc <file>")
def handle_wc(raw: str) -> None:
    tokens = _tokens(raw)
    if not tokens:
        jarvis_say("Usage: wc <file>")
        return

    try:
        path = resolve(tokens[0], must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if path.is_dir():
        jarvis_say(f"[red]Is a directory:[/red] {path}")
        return

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
        return
    except OSError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    lines = content.count("\n")
    words = len(content.split())
    chars = len(content)

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Lines", justify="right", style="cyan")
    table.add_column("Words", justify="right", style="cyan")
    table.add_column("Chars", justify="right", style="cyan")
    table.add_column("File", style="dim")
    table.add_row(str(lines), str(words), str(chars), str(path.name))

    _console.print(table)


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------

@register("diff", description="Compare two files. Usage: diff <file1> <file2>")
def handle_diff(raw: str) -> None:
    tokens = _tokens(raw)
    if len(tokens) < 2:
        jarvis_say("Usage: diff <file1> <file2>")
        return

    try:
        path1 = resolve(tokens[0], must_exist=True)
        path2 = resolve(tokens[1], must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    for p in (path1, path2):
        if p.is_dir():
            jarvis_say(f"[red]Is a directory:[/red] {p}")
            return

    try:
        text1 = path1.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        text2 = path2.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
        return
    except OSError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    diff_lines = list(difflib.unified_diff(
        text1, text2,
        fromfile=str(path1.name),
        tofile=str(path2.name),
    ))

    if not diff_lines:
        jarvis_say("[green]Files are identical.[/green]")
        return

    for line in diff_lines:
        line = line.rstrip("\n")
        if line.startswith("+++") or line.startswith("---"):
            _console.print(f"[bold]{line}[/bold]")
        elif line.startswith("@@"):
            _console.print(f"[cyan]{line}[/cyan]")
        elif line.startswith("+"):
            _console.print(f"[green]{line}[/green]")
        elif line.startswith("-"):
            _console.print(f"[red]{line}[/red]")
        else:
            _console.print(line, highlight=False)


# ---------------------------------------------------------------------------
# du
# ---------------------------------------------------------------------------

@register("du", description="Show directory size summary. Usage: du [path]")
def handle_du(raw: str) -> None:
    tokens = _tokens(raw)
    path_str = tokens[0] if tokens else "."

    try:
        path = resolve(path_str, must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if not path.is_dir():
        # Single file — just show its size
        size = path.stat().st_size
        jarvis_say(f"{_human_size(size)}  {path.name}")
        return

    # Collect sizes per top-level child
    entries: list[tuple[str, int]] = []
    total = 0

    try:
        for child in sorted(path.iterdir(), key=lambda p: p.name.lower()):
            if child.is_symlink():
                size = 0
            elif child.is_file():
                size = child.stat().st_size
            elif child.is_dir():
                size = _dir_size(child)
            else:
                size = 0
            entries.append((child.name, size))
            total += size
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
        return

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("Size", justify="right", style="cyan")
    table.add_column("Name")

    for name, size in sorted(entries, key=lambda e: e[1], reverse=True):
        table.add_row(_human_size(size), name)

    table.add_row("─" * 8, "─" * 20, style="dim")
    table.add_row(f"[bold]{_human_size(total)}[/bold]", f"[bold]{path.name}/ (total)[/bold]")

    _console.print(table)


def _dir_size(path: pathlib.Path) -> int:
    """Recursively compute total size of a directory."""
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_symlink():
                continue
            if entry.is_file(follow_symlinks=False):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total += _dir_size(pathlib.Path(entry.path))
    except PermissionError:
        pass
    return total


def _human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    return f"{size_bytes / 1024 ** 3:.1f} GB"
