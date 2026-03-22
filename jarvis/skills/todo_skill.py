"""Todo skill for Jarvis CLI.

Commands:
  todo                     List all tasks
  todo add <text>          Add a task (optional: -p high/med/low)
  todo done <id>           Mark task as complete
  todo undo <id>           Mark task as incomplete
  todo rm <id>             Remove a task
  todo clear               Remove all completed tasks
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from jarvis.core import jarvis_say, register

_console = Console()
_TODO_FILE = Path.home() / ".jarvis" / "todos.json"

_PRIORITY_ORDER = {"high": 0, "med": 1, "low": 2}
_PRIORITY_STYLE = {"high": "bold red", "med": "yellow", "low": "dim"}


def _load_todos() -> list[dict]:
    if _TODO_FILE.exists():
        try:
            return json.loads(_TODO_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_todos(todos: list[dict]) -> None:
    _TODO_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TODO_FILE.write_text(json.dumps(todos, indent=2), encoding="utf-8")


def _next_id(todos: list[dict]) -> int:
    if not todos:
        return 1
    return max(t["id"] for t in todos) + 1


@register("todo", aliases=["todos"], description="Task list. Usage: todo, todo add <text> [-p high], todo done/undo/rm <id>")
def handle_todo(raw: str) -> None:
    parts = raw.strip().split(None, 2)
    sub = parts[1].lower() if len(parts) > 1 else "list"
    arg = parts[2] if len(parts) > 2 else ""

    if sub == "list" or sub == "todo" or sub == "todos":
        _list_todos()
    elif sub == "add":
        _add_todo(arg)
    elif sub == "done":
        _set_done(arg, done=True)
    elif sub == "undo":
        _set_done(arg, done=False)
    elif sub == "rm":
        _rm_todo(arg)
    elif sub == "clear":
        _clear_done()
    else:
        # Treat as shorthand for "todo add <text>"
        text = raw.strip().split(None, 1)[1] if len(parts) > 1 else ""
        _add_todo(text)


def _list_todos() -> None:
    todos = _load_todos()
    if not todos:
        jarvis_say("No tasks. Add one with: todo add <text>")
        return

    # Sort: incomplete first, then by priority, then by id
    todos.sort(key=lambda t: (
        t.get("done", False),
        _PRIORITY_ORDER.get(t.get("priority", "med"), 1),
        t["id"],
    ))

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("ID", style="dim", justify="right")
    table.add_column("", width=2)  # checkbox
    table.add_column("Task")
    table.add_column("Priority", justify="center")
    table.add_column("Added", style="dim")

    for t in todos:
        done = t.get("done", False)
        check = "[green]✓[/green]" if done else "○"
        text = f"[strike dim]{t['text']}[/strike dim]" if done else t["text"]
        pri = t.get("priority", "med")
        pri_display = f"[{_PRIORITY_STYLE.get(pri, 'white')}]{pri}[/{_PRIORITY_STYLE.get(pri, 'white')}]"
        added = t.get("added", "")[:10]  # date only
        table.add_row(str(t["id"]), check, text, pri_display, added)

    _console.print(table)


def _add_todo(arg: str) -> None:
    if not arg.strip():
        jarvis_say("Usage: todo add <text> [-p high/med/low]")
        return

    # Parse optional priority flag
    priority = "med"
    tokens = arg.split()
    if "-p" in tokens:
        idx = tokens.index("-p")
        if idx + 1 < len(tokens) and tokens[idx + 1] in _PRIORITY_ORDER:
            priority = tokens[idx + 1]
            tokens = tokens[:idx] + tokens[idx + 2:]
        else:
            tokens = tokens[:idx] + tokens[idx + 1:]

    text = " ".join(tokens).strip()
    if not text:
        jarvis_say("Usage: todo add <text> [-p high/med/low]")
        return

    todos = _load_todos()
    task = {
        "id": _next_id(todos),
        "text": text,
        "priority": priority,
        "done": False,
        "added": datetime.now().isoformat(timespec="seconds"),
    }
    todos.append(task)
    _save_todos(todos)
    jarvis_say(f"[green]Added #{task['id']}:[/green] {text}")


def _set_done(arg: str, done: bool) -> None:
    if not arg.strip().isdigit():
        jarvis_say(f"Usage: todo {'done' if done else 'undo'} <id>")
        return

    task_id = int(arg.strip())
    todos = _load_todos()
    for t in todos:
        if t["id"] == task_id:
            t["done"] = done
            _save_todos(todos)
            label = "completed" if done else "reopened"
            jarvis_say(f"[green]Task #{task_id} {label}.[/green]")
            return

    jarvis_say(f"[yellow]No task with ID {task_id}.[/yellow]")


def _rm_todo(arg: str) -> None:
    if not arg.strip().isdigit():
        jarvis_say("Usage: todo rm <id>")
        return

    task_id = int(arg.strip())
    todos = _load_todos()
    before = len(todos)
    todos = [t for t in todos if t["id"] != task_id]
    if len(todos) == before:
        jarvis_say(f"[yellow]No task with ID {task_id}.[/yellow]")
        return
    _save_todos(todos)
    jarvis_say(f"[green]Removed task #{task_id}.[/green]")


def _clear_done() -> None:
    todos = _load_todos()
    remaining = [t for t in todos if not t.get("done", False)]
    cleared = len(todos) - len(remaining)
    if cleared == 0:
        jarvis_say("No completed tasks to clear.")
        return
    _save_todos(remaining)
    jarvis_say(f"[green]Cleared {cleared} completed task(s).[/green]")
