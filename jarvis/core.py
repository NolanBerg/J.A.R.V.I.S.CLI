from __future__ import annotations

import glob as _glob
import os
import platform
import readline
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import pyfiglet
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

app = typer.Typer(add_completion=False)
console = Console()

JARVIS_NAME = "J.A.R.V.I.S."


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def jarvis_say(text: str) -> None:
    console.print(f"[bold blue]{JARVIS_NAME}:[/bold blue] {text}")


def user_say(text: str) -> None:
    console.print(f"[bold magenta]You:[/bold magenta] {text}")


@contextmanager
def jarvis_thinking(message: str = "Thinking..."):
    with console.status(
        f"[bold blue]{JARVIS_NAME}:[/bold blue] [cyan]{message}[/cyan]",
        spinner="dots",
        spinner_style="bold cyan",
    ):
        yield


def render_banner() -> None:
    banner = pyfiglet.figlet_format("JARVIS", font="slant")
    console.print(Text(banner, style="bold cyan"))
    console.print("[bold cyan]Just A Rather Very Intelligent System[/bold cyan]\n")


# ---------------------------------------------------------------------------
# System helpers (used by skills)
# ---------------------------------------------------------------------------

def open_target(target: str) -> None:
    system = platform.system().lower()
    try:
        if system == "darwin":
            subprocess.Popen(["open", target])
        elif system == "windows":
            subprocess.Popen(["start", "", target], shell=True)
        else:
            subprocess.Popen(["xdg-open", target])
        jarvis_say(f"Opening `{target}`.")
    except Exception as exc:  # noqa: BLE001
        jarvis_say(f"I am afraid I could not open `{target}`: {exc}")


# ---------------------------------------------------------------------------
# Command Registry
# ---------------------------------------------------------------------------

@dataclass
class Skill:
    name: str
    aliases: list[str]
    description: str
    handler: Callable[[str], None]
    # Keys this skill is registered under (name + aliases), populated by register()
    _keys: list[str] = field(default_factory=list, init=False, repr=False)


# Maps every key (name + each alias) -> Skill
_registry: dict[str, Skill] = {}
# Ordered list of unique skills for help display
_skills: list[Skill] = []


def register(
    name: str,
    *,
    aliases: list[str] | None = None,
    description: str = "",
) -> Callable[[Callable[[str], None]], Callable[[str], None]]:
    """Decorator that registers a function as a Jarvis skill.

    Usage::

        @register("greet", aliases=["hello", "hi"], description="Say hello.")
        def handle_greet(raw: str) -> None:
            jarvis_say("Hello!")
    """
    def decorator(fn: Callable[[str], None]) -> Callable[[str], None]:
        all_aliases = aliases or []
        skill = Skill(name=name, aliases=all_aliases, description=description, handler=fn)
        keys = [name, *all_aliases]
        skill._keys = keys
        for key in keys:
            _registry[key] = skill
        _skills.append(skill)
        return fn
    return decorator


def dispatch(raw: str) -> bool:
    """Try to handle *raw* with a registered skill.

    Returns True if a skill handled the command, False otherwise.
    Exact match is tried first, then prefix match for commands like ``open <target>``.
    """
    cmd = raw.strip().lower()

    # Exact match
    if cmd in _registry:
        _registry[cmd].handler(raw)
        return True

    # Prefix match (e.g. "open https://...")
    for key, skill in _registry.items():
        if cmd.startswith(key + " "):
            skill.handler(raw)
            return True

    return False


def show_help() -> None:
    """Auto-generate the help table from registered skills."""
    table = Table(title="Jarvis Capabilities", show_lines=True)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    seen: set[int] = set()
    for skill in _skills:
        if id(skill) in seen:
            continue
        seen.add(id(skill))
        label = skill.name
        if skill.aliases:
            label += " / " + " / ".join(skill.aliases)
        table.add_row(label, skill.description)

    console.print(table)


# ---------------------------------------------------------------------------
# Tab completion
# ---------------------------------------------------------------------------

def _completer(text: str, state: int):
    line = readline.get_line_buffer()
    if " " not in line.lstrip():
        # Completing a command name
        options = [k for k in _registry if k.startswith(text)]
    else:
        # Completing a filesystem path argument
        pattern = (text or ".") + "*"
        matches = _glob.glob(os.path.expanduser(pattern))
        options = [m + ("/" if os.path.isdir(m) else " ") for m in matches]
    try:
        return options[state]
    except IndexError:
        return None


# ---------------------------------------------------------------------------
# REPL
# ---------------------------------------------------------------------------

def interactive_loop() -> None:
    import datetime

    # Import skills so they self-register before the loop starts
    import jarvis.skills  # noqa: F401

    render_banner()

    now = datetime.datetime.now()
    hour = now.strftime("%I").lstrip("0")
    ampm = now.strftime("%p")
    hour_int = now.hour
    if hour_int < 12:
        greeting = "Good morning"
    elif hour_int < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    jarvis_say(f"{greeting}. It's {hour} {ampm}. How may I assist you today?")
    console.print("[dim]Type 'help' to see capabilities, 'exit' to quit.[/dim]\n")

    _history_file = Path.home() / ".jarvis" / "history"
    _history_file.parent.mkdir(parents=True, exist_ok=True)
    try:
        readline.read_history_file(str(_history_file))
    except FileNotFoundError:
        pass
    readline.set_history_length(1000)

    readline.set_completer(_completer)
    readline.set_completer_delims(" \t\n")
    if "libedit" in (readline.__doc__ or ""):
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")

    while True:
        try:
            raw = input("\033[1;35mCommand\033[0m: ")
        except (EOFError, KeyboardInterrupt):
            readline.write_history_file(str(_history_file))
            jarvis_say("Emergency shutdown triggered. Goodbye.")
            raise typer.Exit(code=0)

        if not raw.strip():
            continue

        if dispatch(raw):
            continue

        from jarvis.ai.ollama_client import ai_fallback  # lazy import
        ai_fallback(raw)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@app.command()
def run(command: Optional[str] = typer.Argument(None)) -> None:
    """Run Jarvis interactively (no args) or execute a single command."""
    import jarvis.skills  # noqa: F401

    if command is None:
        interactive_loop()
        return

    if not dispatch(command):
        jarvis_say(
            "That command is not yet in my repertoire. "
            "Try 'help' for available options."
        )


def main() -> None:
    app()
