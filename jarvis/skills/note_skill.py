"""Notes skill — quick-capture scratchpad stored at ~/.jarvis/notes.md."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from jarvis.core import jarvis_say, register

NOTES_FILE = Path.home() / ".jarvis" / "notes.md"
_console = Console()


def _ensure_file() -> None:
    NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not NOTES_FILE.exists():
        NOTES_FILE.touch()


@register(
    "note",
    aliases=["notes"],
    description=(
        "Quick notes. Usage: note <text> | note list | "
        "note search <term> | note clear"
    ),
)
def handle_note(raw: str) -> None:
    parts = raw.strip().split(None, 1)
    arg = parts[1] if len(parts) > 1 else ""
    lower = arg.lower().strip()

    if lower == "list" or not arg:
        _note_list()
    elif lower == "clear":
        _note_clear()
    elif lower.startswith("search "):
        _note_search(arg[7:].strip())
    else:
        _note_add(arg)


def _note_add(text: str) -> None:
    _ensure_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"- [{timestamp}] {text}\n"
    with NOTES_FILE.open("a", encoding="utf-8") as f:
        f.write(entry)
    jarvis_say(f"Note saved. [dim]({timestamp})[/dim]")


def _note_list() -> None:
    _ensure_file()
    content = NOTES_FILE.read_text(encoding="utf-8").strip()
    if not content:
        jarvis_say("[dim]No notes yet. Use [bold]note <text>[/bold] to add one.[/dim]")
        return
    _console.print(content)


def _note_search(term: str) -> None:
    _ensure_file()
    lines = NOTES_FILE.read_text(encoding="utf-8").splitlines()
    matches = [l for l in lines if re.search(re.escape(term), l, re.IGNORECASE)]
    if not matches:
        jarvis_say(f"No notes matching [bold]{term}[/bold].")
        return
    for line in matches:
        _console.print(line)


def _note_clear() -> None:
    _ensure_file()
    if not NOTES_FILE.read_text().strip():
        jarvis_say("[dim]Notes already empty.[/dim]")
        return
    if Confirm.ask("Clear all notes?"):
        NOTES_FILE.write_text("", encoding="utf-8")
        jarvis_say("Notes cleared.")
