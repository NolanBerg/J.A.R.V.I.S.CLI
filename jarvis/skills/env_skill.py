"""Environment variable skill for Jarvis CLI.

Commands:
  env                Show all environment variables
  env get <name>     Show a specific variable
  env set <K>=<V>    Set a variable for this session
"""
from __future__ import annotations

import os

from rich.console import Console
from rich.table import Table

from jarvis.core import jarvis_say, register

_console = Console()


@register("env", description="View/set environment variables. Usage: env, env get PATH, env set FOO=bar")
def handle_env(raw: str) -> None:
    parts = raw.strip().split(None, 2)
    # "env" alone
    if len(parts) <= 1:
        _show_all()
        return

    sub = parts[1].lower()

    if sub == "get":
        if len(parts) < 3:
            jarvis_say("Usage: env get <NAME>")
            return
        name = parts[2].strip()
        value = os.environ.get(name)
        if value is None:
            jarvis_say(f"[yellow]{name}[/yellow] is not set.")
        else:
            jarvis_say(f"[cyan]{name}[/cyan] = {value}")
        return

    if sub == "set":
        if len(parts) < 3 or "=" not in parts[2]:
            jarvis_say("Usage: env set NAME=VALUE")
            return
        expr = parts[2]
        name, value = expr.split("=", 1)
        name = name.strip()
        value = value.strip()
        os.environ[name] = value
        jarvis_say(f"[green]Set[/green] [cyan]{name}[/cyan] = {value}")
        return

    jarvis_say("Usage: env, env get <NAME>, env set <NAME>=<VALUE>")


def _show_all() -> None:
    table = Table(title="Environment Variables", show_lines=False, box=None, padding=(0, 2))
    table.add_column("Variable", style="cyan", no_wrap=True)
    table.add_column("Value", style="dim", overflow="fold")

    for key in sorted(os.environ):
        table.add_row(key, os.environ[key])

    _console.print(table)
