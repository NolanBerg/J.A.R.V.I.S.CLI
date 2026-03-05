import platform
import subprocess
from datetime import datetime
from typing import Optional

import pyfiglet
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

app = typer.Typer(add_completion=False)
console = Console()


JARVIS_NAME = "J.A.R.V.I.S."


def render_banner() -> None:
    banner = pyfiglet.figlet_format("JARVIS", font="slant")
    console.print(f"[bold cyan]{banner}[/bold cyan]")
    console.print(
        "[bold cyan]Just A Rather Very Intelligent System[/bold cyan]\n",
    )


def jarvis_say(text: str) -> None:
    console.print(f"[bold blue]{JARVIS_NAME}:[/bold blue] {text}")


def user_say(text: str) -> None:
    console.print(f"[bold magenta]You:[/bold magenta] {text}")


def handle_builtin(command: str) -> bool:
    """
    Return True if handled, False if unknown (so future "skills" can use it).
    """
    cmd = command.strip().lower()

    if cmd in {"exit", "quit", "q"}:
        jarvis_say("Shutting down. It was a pleasure, as always.")
        raise typer.Exit(code=0)

    if cmd in {"time", "date"}:
        now = datetime.now().strftime("%A %B %d, %Y %H:%M:%S")
        jarvis_say(f"The current time is {now}.")
        return True

    if cmd in {"help", "?"}:
        show_help()
        return True

    if cmd.startswith("open "):
        target = command[5:].strip()
        open_target(target)
        return True

    if cmd in {"who are you", "who are you?", "identity"}:
        jarvis_say(
            "I am J.A.R.V.I.S., your personal command‑line assistant. "
            "At your service."
        )
        return True

    return False


def show_help() -> None:
    table = Table(title="Jarvis Capabilities", show_lines=True)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("help", "Show this help panel.")
    table.add_row("time / date", "Tell you the current date and time.")
    table.add_row("open <thing>", "Open an app or URL (macOS friendly).")
    table.add_row("exit / quit / q", "Power down Jarvis.")
    table.add_row("who are you", "Ask Jarvis about itself.")

    console.print(table)


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


def interactive_loop() -> None:
    render_banner()
    jarvis_say("Online and ready. How may I assist you today?")
    console.print(
        "[dim]Type 'help' to see capabilities, 'exit' to quit.[/dim]\n"
    )

    while True:
        try:
            raw = Prompt.ask("[bold magenta]Command[/bold magenta]")
        except (EOFError, KeyboardInterrupt):
            jarvis_say("Emergency shutdown triggered. Goodbye.")
            raise typer.Exit(code=0)

        if not raw.strip():
            continue

        user_say(raw)

        if handle_builtin(raw):
            continue

        # Default fallback: playful Jarvis-style reply
        jarvis_say(
            "That command is not yet in my repertoire. "
            "Perhaps you would like me to learn it next?"
        )


@a
pp.command()
def run(command: Optional[str] = typer.Argument(None)):
    """
    Run Jarvis either interactively (no args) or with a single command.
    """
    if command is None:
        interactive_loop()
        return

    # One‑shot mode for quick commands: `python jarvis.py run "time"`
    if not handle_builtin(command):
        jarvis_say(
            "That command is not yet in my repertoire. "
            "Try 'help' for available options."
        )


def main() -> None:
    app()


if __name__ == "__main__":
    main()

