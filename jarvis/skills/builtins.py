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
