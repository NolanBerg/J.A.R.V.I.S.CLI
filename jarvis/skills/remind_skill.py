"""Reminders skill — session-scoped timers using threading.Timer."""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from jarvis.core import console, jarvis_say, register


@dataclass
class Reminder:
    id: int
    message: str
    fire_at: datetime
    timer: threading.Timer = field(repr=False)


_reminders: list[Reminder] = []
_next_id = 1


def _parse_duration(s: str) -> timedelta | None:
    """Parse '15m', '2h', '30s', '1h30m' into timedelta."""
    pattern = r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    m = re.fullmatch(pattern, s.strip())
    if not m or not any(m.groups()):
        return None
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _fire_reminder(reminder: Reminder) -> None:
    """Callback when timer expires."""
    console.print()  # newline to avoid clobbering prompt
    console.print(
        f"\a[bold yellow]\u23f0 REMINDER:[/bold yellow] {reminder.message}"
    )
    if reminder in _reminders:
        _reminders.remove(reminder)


@register(
    "remind",
    aliases=["reminder", "timer"],
    description=(
        "Set a reminder. Usage: remind <duration> <message> | "
        "remind list | remind cancel <id>"
    ),
)
def handle_remind(raw: str) -> None:
    global _next_id
    parts = raw.strip().split(None, 1)
    arg = parts[1] if len(parts) > 1 else ""
    lower = arg.lower().strip()

    if lower == "list" or not arg:
        _remind_list()
        return
    if lower.startswith("cancel "):
        _remind_cancel(arg[7:].strip())
        return

    # Parse: remind <duration> <message>
    tokens = arg.split(None, 1)
    if len(tokens) < 2:
        jarvis_say(
            "Usage: remind <duration> <message>  "
            "(e.g. remind 15m check the build)"
        )
        return

    duration_str, message = tokens
    delta = _parse_duration(duration_str)
    if delta is None or delta.total_seconds() <= 0:
        jarvis_say("Invalid duration. Use format like: 30s, 15m, 2h, 1h30m")
        return

    fire_at = datetime.now() + delta
    rid = _next_id
    _next_id += 1

    # Create reminder before timer so the lambda captures it
    reminder = Reminder(id=rid, message=message, fire_at=fire_at, timer=None)  # type: ignore[arg-type]
    timer = threading.Timer(delta.total_seconds(), lambda r=reminder: _fire_reminder(r))
    timer.daemon = True
    reminder.timer = timer
    _reminders.append(reminder)
    timer.start()

    jarvis_say(
        f"Reminder #{rid} set for {fire_at.strftime('%H:%M:%S')}. "
        f"[dim]({duration_str})[/dim]"
    )


def _remind_list() -> None:
    active = [r for r in _reminders if r.timer.is_alive()]
    if not active:
        jarvis_say("[dim]No pending reminders.[/dim]")
        return
    for r in active:
        remaining = r.fire_at - datetime.now()
        mins = int(remaining.total_seconds() // 60)
        secs = int(remaining.total_seconds() % 60)
        console.print(
            f"  [cyan]#{r.id}[/cyan]  {r.message}  [dim](in {mins}m {secs}s)[/dim]"
        )


def _remind_cancel(id_str: str) -> None:
    try:
        rid = int(id_str)
    except ValueError:
        jarvis_say("Usage: remind cancel <id>  (numeric ID from remind list)")
        return
    for r in _reminders:
        if r.id == rid:
            r.timer.cancel()
            _reminders.remove(r)
            jarvis_say(f"Reminder #{rid} cancelled.")
            return
    jarvis_say(f"No reminder with ID #{rid}.")
