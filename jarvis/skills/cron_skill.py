"""Cron / schedule skill for Jarvis CLI.

Persistent scheduled tasks that survive session restarts.
Uses the system crontab (crontab -l / crontab -e equivalent).

Commands:
  cron list                          Show all Jarvis-managed cron jobs
  cron add <schedule> <command>      Add a cron job
  cron rm <id>                       Remove a cron job by ID
  cron run <command>                 Preview what a command would do

Schedule shortcuts:
  @hourly, @daily, @weekly, @monthly, @reboot
  Or standard cron: "0 9 * * *" (quote it)

Examples:
  cron add @daily "jarvis sysinfo"
  cron add "*/5 * * * *" "jarvis weather"
  cron add @hourly "echo hello >> ~/log.txt"
"""
from __future__ import annotations

import platform
import re
import shlex
import subprocess

from rich.console import Console
from rich.table import Table

from jarvis.core import jarvis_say, register

_SYSTEM = platform.system().lower()

_console = Console()

_MARKER = "# jarvis-managed"

_SHORTCUTS = {"@hourly", "@daily", "@weekly", "@monthly", "@yearly", "@annually", "@reboot"}


def _get_crontab() -> str:
    """Read current user crontab."""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return ""
        return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def _set_crontab(content: str) -> bool:
    """Write new crontab content."""
    try:
        result = subprocess.run(
            ["crontab", "-"],
            input=content, capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _parse_jarvis_jobs(crontab: str) -> list[dict]:
    """Extract Jarvis-managed jobs with their IDs."""
    jobs = []
    for line in crontab.splitlines():
        line = line.strip()
        if not line.endswith(_MARKER):
            continue

        # Strip the marker
        job_line = line[: line.rfind(_MARKER)].strip()

        # Extract ID if present: # id=N at end before marker
        job_id = None
        id_match = re.search(r"#\s*id=(\d+)\s*$", job_line)
        if id_match:
            job_id = int(id_match.group(1))
            job_line = job_line[: id_match.start()].strip()

        # Split schedule from command
        if job_line.startswith("@"):
            parts = job_line.split(None, 1)
            schedule = parts[0]
            command = parts[1] if len(parts) > 1 else ""
        else:
            parts = job_line.split(None, 5)
            if len(parts) >= 6:
                schedule = " ".join(parts[:5])
                command = parts[5]
            else:
                schedule = job_line
                command = ""

        jobs.append({"id": job_id, "schedule": schedule, "command": command, "raw": line})

    return jobs


def _next_id(jobs: list[dict]) -> int:
    ids = [j["id"] for j in jobs if j["id"] is not None]
    return max(ids, default=0) + 1


@register("cron", aliases=["schedule"], description="Persistent scheduled tasks. Usage: cron list/add/rm")
def handle_cron(raw: str) -> None:
    if _SYSTEM == "windows":
        jarvis_say(
            "Cron uses [bold]Windows Task Scheduler[/bold] on this platform.\n"
            "To manage scheduled tasks, use [cyan]Task Scheduler[/cyan] (taskschd.msc) "
            "or the [cyan]schtasks[/cyan] command.\n"
            "Example: [dim]schtasks /create /SC DAILY /TN \"JarvisDaily\" /TR \"jarvis sysinfo\" /ST 09:00[/dim]"
        )
        return

    parts = raw.strip().split(None, 1)
    arg = parts[1].strip() if len(parts) > 1 else ""
    lower = arg.lower()

    if not arg or lower == "list":
        _cron_list()
    elif lower.startswith("add "):
        _cron_add(arg[4:].strip())
    elif lower.startswith("rm "):
        _cron_rm(arg[3:].strip())
    elif lower.startswith("run "):
        _cron_run(arg[4:].strip())
    else:
        jarvis_say("Usage: cron list | cron add <schedule> <command> | cron rm <id>")


def _cron_list() -> None:
    crontab = _get_crontab()
    jobs = _parse_jarvis_jobs(crontab)

    if not jobs:
        jarvis_say("No Jarvis-managed cron jobs. Add one with: cron add @daily \"jarvis sysinfo\"")
        return

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Schedule", style="bold")
    table.add_column("Command")

    for j in jobs:
        table.add_row(str(j["id"] or "?"), j["schedule"], j["command"])

    _console.print(table)


def _cron_add(arg: str) -> None:
    if not arg:
        jarvis_say(
            "Usage: cron add <schedule> <command>\n"
            "  Shortcuts: @hourly, @daily, @weekly, @monthly, @reboot\n"
            "  Standard:  cron add \"0 9 * * *\" \"jarvis weather\""
        )
        return

    # Parse: schedule might be a shortcut or a quoted "* * * * *"
    try:
        tokens = shlex.split(arg)
    except ValueError:
        tokens = arg.split()

    if not tokens:
        jarvis_say("Usage: cron add <schedule> <command>")
        return

    if tokens[0] in _SHORTCUTS:
        schedule = tokens[0]
        command = " ".join(tokens[1:])
    else:
        # Check if first token looks like a 5-field cron expression
        # It might be quoted as one token: "0 9 * * *"
        first = tokens[0]
        if " " in first and len(first.split()) == 5:
            schedule = first
            command = " ".join(tokens[1:])
        elif len(tokens) >= 6:
            # Unquoted: 0 9 * * * command args...
            schedule = " ".join(tokens[:5])
            command = " ".join(tokens[5:])
        else:
            jarvis_say(
                "[yellow]Could not parse schedule.[/yellow] "
                "Use a shortcut (@daily) or quote the schedule: \"0 9 * * *\""
            )
            return

    if not command:
        jarvis_say("Missing command. Usage: cron add @daily \"jarvis sysinfo\"")
        return

    # Add to crontab
    crontab = _get_crontab()
    jobs = _parse_jarvis_jobs(crontab)
    new_id = _next_id(jobs)

    new_line = f"{schedule} {command} # id={new_id} {_MARKER}"

    # Ensure trailing newline
    if crontab and not crontab.endswith("\n"):
        crontab += "\n"
    crontab += new_line + "\n"

    if _set_crontab(crontab):
        jarvis_say(f"[green]Added cron job #{new_id}:[/green] {schedule}  {command}")
    else:
        jarvis_say("[red]Failed to update crontab.[/red]")


def _cron_rm(arg: str) -> None:
    if not arg.strip().isdigit():
        jarvis_say("Usage: cron rm <id>")
        return

    target_id = int(arg.strip())
    crontab = _get_crontab()
    jobs = _parse_jarvis_jobs(crontab)

    found = any(j["id"] == target_id for j in jobs)
    if not found:
        jarvis_say(f"[yellow]No cron job with ID {target_id}.[/yellow]")
        return

    # Remove the matching line
    lines = crontab.splitlines()
    new_lines = []
    for line in lines:
        if line.strip().endswith(_MARKER) and f"# id={target_id} " in line:
            continue
        new_lines.append(line)

    new_crontab = "\n".join(new_lines)
    if new_crontab and not new_crontab.endswith("\n"):
        new_crontab += "\n"

    if _set_crontab(new_crontab):
        jarvis_say(f"[green]Removed cron job #{target_id}.[/green]")
    else:
        jarvis_say("[red]Failed to update crontab.[/red]")


def _cron_run(arg: str) -> None:
    """Preview/test a command without scheduling it."""
    if not arg:
        jarvis_say("Usage: cron run <command>")
        return

    jarvis_say(f"[dim]Running:[/dim] {arg}")
    try:
        result = subprocess.run(
            arg, shell=True,
            capture_output=True, text=True, timeout=30,
        )
        if result.stdout.strip():
            _console.print(result.stdout.strip())
        if result.stderr.strip():
            _console.print(f"[yellow]{result.stderr.strip()}[/yellow]")
        if result.returncode != 0:
            jarvis_say(f"[yellow]Exit code: {result.returncode}[/yellow]")
    except subprocess.TimeoutExpired:
        jarvis_say("[yellow]Command timed out (30s limit).[/yellow]")
    except OSError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
