"""File system skill for Jarvis CLI.

Commands:
  ls [path]              List directory contents
  cat <file>             Read file contents
  stat <path>            Show file/directory info and permissions
  mkdir <path>           Create directory (with parents)
  touch <file>           Create empty file or update modification time
  rm <path> [-r]         Delete file or directory
  mv <src> <dst>         Move or rename
  cp <src> <dst>         Copy file or directory
  find [root] <pattern>  Search for files/directories by name
  grep [-r] <pat> <path> Search for text inside files
"""
from __future__ import annotations

import os
import pathlib
import re
import shlex

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text

from jarvis.core import jarvis_say, register
from jarvis.fs.ops import (
    CAT_SIZE_LIMIT,
    fs_cat,
    fs_cp,
    fs_find,
    fs_grep,
    fs_ls,
    fs_mkdir,
    fs_mv,
    fs_rm,
    fs_stat,
    fs_touch,
)
from jarvis.fs.paths import resolve, resolve_pair

_console = Console()


def _tokens(raw: str) -> list[str]:
    """Strip the first word (command name) and return remaining tokens."""
    parts = raw.strip().split(None, 1)
    text = parts[1] if len(parts) > 1 else ""
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


# ---------------------------------------------------------------------------
# Top-level command registrations
# ---------------------------------------------------------------------------

@register("ls", description="List directory contents.")
def handle_ls(raw: str) -> None:
    _cmd_ls(_tokens(raw))


@register("cat", description="Read file contents.")
def handle_cat(raw: str) -> None:
    _cmd_cat(_tokens(raw))


@register("stat", description="Show file/directory info and permissions.")
def handle_stat(raw: str) -> None:
    _cmd_stat(_tokens(raw))


@register("mkdir", description="Create directory (with parents).")
def handle_mkdir(raw: str) -> None:
    _cmd_mkdir(_tokens(raw))


@register("touch", description="Create empty file or update modification time.")
def handle_touch(raw: str) -> None:
    _cmd_touch(_tokens(raw))


@register("rm", description="Delete file or directory (use -r for directories).")
def handle_rm(raw: str) -> None:
    _cmd_rm(_tokens(raw))


@register("mv", description="Move or rename a file or directory.")
def handle_mv(raw: str) -> None:
    _cmd_mv(_tokens(raw))


@register("cp", description="Copy file or directory.")
def handle_cp(raw: str) -> None:
    _cmd_cp(_tokens(raw))


@register("find", aliases=["search"], description="Search for files or directories by name (supports globs).")
def handle_find(raw: str) -> None:
    _cmd_find(_tokens(raw))


@register("grep", description="Search for text inside files (supports regex).")
def handle_grep(raw: str) -> None:
    _cmd_grep(_tokens(raw))


@register("pwd", description="Print current working directory.")
def handle_pwd(raw: str) -> None:
    jarvis_say(str(pathlib.Path.cwd()))


@register("cd", description="Change current working directory (defaults to home).")
def handle_cd(raw: str) -> None:
    tokens = _tokens(raw)
    target = tokens[0] if tokens else "~"
    try:
        path = resolve(target, must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return
    if not path.is_dir():
        jarvis_say(f"[red]Not a directory:[/red] {path}")
        return
    try:
        os.chdir(path)
        jarvis_say(f"[dim]{path}[/dim]")
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")


# ---------------------------------------------------------------------------
# Centralized error handler
# ---------------------------------------------------------------------------

def _run(fn, *args, **kwargs) -> bool:
    """Call fn(*args, **kwargs), translate stdlib exceptions to jarvis_say messages.

    Returns True on success, False on error.
    """
    try:
        fn(*args, **kwargs)
        return True
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
    except (IsADirectoryError, NotADirectoryError) as e:
        jarvis_say(f"[red]Wrong type:[/red] {e}")
    except ValueError as e:
        jarvis_say(f"[yellow]Warning:[/yellow] {e}")
    except OSError as e:
        jarvis_say(f"[red]OS error:[/red] {e}")
    return False


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def _cmd_ls(tokens: list[str]) -> None:
    path_str = tokens[0] if tokens else "."
    try:
        path = resolve(path_str, must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    try:
        entries = fs_ls(path)
    except (FileNotFoundError, NotADirectoryError, PermissionError, OSError) as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    if not entries:
        jarvis_say(f"[dim]{path}[/dim] is empty.")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Name")
    table.add_column("Size", justify="right", style="dim")
    table.add_column("Type", style="dim")

    type_labels = {"d": "dir", "f": "file", "l": "link", "?": "other"}

    for entry in entries:
        if entry.kind == "d":
            name_fmt = f"[bold blue]{entry.name}/[/bold blue]"
            size_str = "-"
        elif entry.kind == "l":
            name_fmt = f"[cyan]{entry.name}[/cyan]"
            size_str = "-"
        else:
            name_fmt = entry.name
            size_str = _human_size(entry.size)

        table.add_row(name_fmt, size_str, type_labels.get(entry.kind, "?"))

    jarvis_say(f"[dim]{path}[/dim]")
    _console.print(table)


def _cmd_cat(tokens: list[str]) -> None:
    if not tokens:
        jarvis_say("Usage: cat <file>")
        return

    try:
        path = resolve(tokens[0], must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    try:
        content = fs_cat(path)
    except (FileNotFoundError, IsADirectoryError, PermissionError, ValueError, OSError) as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    # Print raw content without Jarvis prefix — it's the user's file
    _console.print(content, highlight=False)


def _cmd_stat(tokens: list[str]) -> None:
    if not tokens:
        jarvis_say("Usage: stat <path>")
        return

    try:
        path = resolve(tokens[0], must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    try:
        info = fs_stat(path)
    except (FileNotFoundError, PermissionError, OSError) as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold")
    table.add_column("Value")

    labels = [
        ("path", "Path"),
        ("type", "Type"),
        ("size", "Size"),
        ("permissions", "Permissions"),
        ("modified", "Modified"),
        ("created", "Created"),
        ("owner", "Owner"),
    ]
    for key, label in labels:
        table.add_row(label, info[key])

    _console.print(table)


def _cmd_mkdir(tokens: list[str]) -> None:
    if not tokens:
        jarvis_say("Usage: mkdir <path>")
        return

    try:
        path = resolve(tokens[0])
    except Exception as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    if _run(fs_mkdir, path):
        jarvis_say(f"[green]Created[/green] [dim]{path}[/dim]")


def _cmd_touch(tokens: list[str]) -> None:
    if not tokens:
        jarvis_say("Usage: touch <file>")
        return

    try:
        path = resolve(tokens[0])
    except Exception as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    existed = path.exists()
    if _run(fs_touch, path):
        action = "Updated" if existed else "Created"
        jarvis_say(f"[green]{action}[/green] [dim]{path}[/dim]")


def _cmd_rm(tokens: list[str]) -> None:
    flags = {t for t in tokens if t.startswith("-")}
    positional = [t for t in tokens if not t.startswith("-")]
    recursive = "--recursive" in flags or "-r" in flags

    if not positional:
        jarvis_say("Usage: rm <path> [--recursive / -r]")
        return

    try:
        path = resolve(positional[0], must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    # Safety: always confirm before deletion
    if path.is_dir() and not path.is_symlink():
        label = f"'{path}' and all its contents"
    else:
        label = f"'{path}'"

    confirmed = Confirm.ask(f"[yellow]Delete {label}?[/yellow]", default=False)
    if not confirmed:
        jarvis_say("Aborted.")
        return

    if _run(fs_rm, path, recursive=recursive):
        jarvis_say(f"[green]Deleted[/green] [dim]{path}[/dim]")


def _cmd_mv(tokens: list[str]) -> None:
    positional = [t for t in tokens if not t.startswith("-")]
    if len(positional) != 2:
        jarvis_say("Usage: mv <src> <dst>")
        return

    try:
        src, dst = resolve_pair(positional[0], positional[1])
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if _run(fs_mv, src, dst):
        jarvis_say(f"[green]Moved[/green] [dim]{src}[/dim] → [dim]{dst}[/dim]")


def _cmd_cp(tokens: list[str]) -> None:
    positional = [t for t in tokens if not t.startswith("-")]
    if len(positional) != 2:
        jarvis_say("Usage: cp <src> <dst>")
        return

    try:
        src, dst = resolve_pair(positional[0], positional[1])
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if _run(fs_cp, src, dst):
        jarvis_say(f"[green]Copied[/green] [dim]{src}[/dim] → [dim]{dst}[/dim]")


def _cmd_find(tokens: list[str]) -> None:
    if not tokens:
        jarvis_say("Usage: find [root] <pattern>")
        return

    # If two non-flag args: first is root, second is pattern. Otherwise cwd + pattern.
    if len(tokens) >= 2:
        root_str, pattern = tokens[0], tokens[1]
    else:
        root_str, pattern = ".", tokens[0]

    try:
        root = resolve(root_str, must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    try:
        results = fs_find(root, pattern)
    except (FileNotFoundError, PermissionError, OSError) as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    if not results:
        jarvis_say(f"[dim]No matches for[/dim] [bold]{pattern}[/bold] [dim]in[/dim] [dim]{root}[/dim]")
        return

    jarvis_say(f"[dim]{len(results)} match(es) in {root}[/dim]")
    for p in results:
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = p
        if p.is_dir():
            _console.print(f"  [bold blue]{rel}/[/bold blue]")
        else:
            _console.print(f"  {rel}")


def _cmd_grep(tokens: list[str]) -> None:
    flags = {t for t in tokens if t.startswith("-")}
    positional = [t for t in tokens if not t.startswith("-")]
    recursive = "-r" in flags or "--recursive" in flags

    if len(positional) < 2:
        jarvis_say("Usage: grep [-r] <pattern> <path>")
        return

    pattern, path_str = positional[0], positional[1]

    try:
        path = resolve(path_str, must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    try:
        matches = fs_grep(pattern, path, recursive=recursive)
    except IsADirectoryError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return
    except re.error as e:
        jarvis_say(f"[red]Invalid pattern:[/red] {e}")
        return
    except (FileNotFoundError, PermissionError, OSError) as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    if not matches:
        jarvis_say(f"[dim]No matches for[/dim] [bold]{pattern}[/bold]")
        return

    regex = re.compile(pattern)
    current_file = None
    for m in matches:
        if m.path != current_file:
            current_file = m.path
            _console.print(f"\n[bold cyan]{m.path}[/bold cyan]")

        # Highlight matched portions
        line_text = Text()
        last = 0
        for hit in regex.finditer(m.line):
            line_text.append(m.line[last:hit.start()])
            line_text.append(m.line[hit.start():hit.end()], style="bold yellow")
            last = hit.end()
        line_text.append(m.line[last:])

        prefix = Text(f"  {m.lineno}: ", style="dim")
        _console.print(prefix + line_text)

    _console.print()
    jarvis_say(f"[dim]{len(matches)} match(es)[/dim]")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / 1024 ** 2:.1f} MB"
