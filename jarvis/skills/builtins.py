from datetime import datetime

import typer

from jarvis.core import jarvis_say, open_target, register, show_help


@register("exit", aliases=["quit", "q"], description="Shut Jarvis down.")
def handle_exit(raw: str) -> None:
    jarvis_say("Shutting down. It was a pleasure, as always.")
    raise typer.Exit(code=0)


@register("time", aliases=["date"], description="Show the current date and time.")
def handle_time(raw: str) -> None:
    now = datetime.now().strftime("%A %B %d, %Y %H:%M:%S")
    jarvis_say(f"The current time is {now}.")


@register("help", aliases=["?"], description="Show this help panel.")
def handle_help(raw: str) -> None:
    show_help()


@register(
    "open",
    aliases=[],
    description="Open an app or URL. Usage: open <target>",
)
def handle_open(raw: str) -> None:
    target = raw.strip()[len("open"):].strip()
    if not target:
        jarvis_say("Please specify what to open. Usage: open <app or URL>")
        return
    open_target(target)


@register(
    "who are you",
    aliases=["identity"],
    description="Ask Jarvis about itself.",
)
def handle_identity(raw: str) -> None:
    jarvis_say(
        "I am J.A.R.V.I.S., your personal command-line assistant. "
        "At your service."
    )


@register("clear", aliases=["cls"], description="Clear the terminal screen.")
def handle_clear(raw: str) -> None:
    import os
    os.system("clear")


@register("history", description="Show or search command history. Usage: history [search <term>]")
def handle_history(raw: str) -> None:
    import readline
    parts = raw.strip().split(None, 2)
    sub = parts[1].lower() if len(parts) > 1 else ""
    term = parts[2] if len(parts) > 2 else ""

    n = readline.get_current_history_length()
    if n == 0:
        jarvis_say("No history yet.")
        return

    if sub == "search":
        if not term:
            jarvis_say("Usage: history search <term>")
            return
        lower_term = term.lower()
        matches = []
        for i in range(n):
            item = readline.get_history_item(i + 1)
            if item and lower_term in item.lower():
                matches.append(f"  {i + 1:>4}  {item}")
        if not matches:
            jarvis_say(f"[dim]No history matching '{term}'.[/dim]")
        else:
            jarvis_say(f"{len(matches)} match(es) for '{term}':\n" + "\n".join(matches))
        return

    lines = [f"  {i + 1:>4}  {readline.get_history_item(i + 1)}" for i in range(n)]
    jarvis_say("Command history:\n" + "\n".join(lines))
