"""Process management skill for Jarvis CLI.

Commands:
  ps                       List running processes (top by CPU)
  ps <name>                Filter processes by name
  kill <pid>               Kill a process by PID
  kill <name>              Kill processes by name (with confirmation)
"""
from __future__ import annotations

import csv
import io
import os
import platform
import signal
import subprocess

from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from jarvis.core import jarvis_say, register

_console = Console()
_SYSTEM = platform.system().lower()


def _parse_ps() -> list[dict]:
    """Return process list as dicts with keys: user, pid, cpu, mem, command."""
    if _SYSTEM == "windows":
        return _parse_ps_windows()
    return _parse_ps_unix()


def _parse_ps_unix() -> list[dict]:
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []

    lines = result.stdout.strip().splitlines()
    if len(lines) < 2:
        return []

    processes = []
    for line in lines[1:]:
        parts = line.split(None, 10)
        if len(parts) < 11:
            continue
        processes.append({
            "user": parts[0],
            "pid": parts[1],
            "cpu": parts[2],
            "mem": parts[3],
            "command": parts[10],
        })
    return processes


def _parse_ps_windows() -> list[dict]:
    """Use tasklist /FO CSV to get process list on Windows."""
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []

    processes = []
    reader = csv.reader(io.StringIO(result.stdout))
    for row in reader:
        if len(row) < 2:
            continue
        # tasklist CSV: Image Name, PID, Session Name, Session#, Mem Usage
        name = row[0].strip()
        pid = row[1].strip()
        mem_str = row[4].strip().replace(",", "").replace(" K", "") if len(row) > 4 else "0"
        try:
            mem_kb = int(mem_str)
        except ValueError:
            mem_kb = 0
        processes.append({
            "user": "N/A",
            "pid": pid,
            "cpu": "N/A",
            "mem": f"{mem_kb // 1024} MB",
            "command": name,
        })
    return processes


@register("ps", description="List or filter running processes. Usage: ps [name]")
def handle_ps(raw: str) -> None:
    parts = raw.strip().split(None, 1)
    filter_name = parts[1].strip().lower() if len(parts) > 1 else None

    processes = _parse_ps()
    if not processes:
        jarvis_say("[yellow]Could not retrieve process list.[/yellow]")
        return

    if filter_name:
        processes = [p for p in processes if filter_name in p["command"].lower()]
        if not processes:
            jarvis_say(f"[dim]No processes matching '{filter_name}'.[/dim]")
            return

    # Sort by CPU descending, show top 25
    processes.sort(key=lambda p: float(p["cpu"]), reverse=True)
    show = processes[:25]

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("PID", style="cyan", justify="right")
    table.add_column("CPU%", justify="right")
    table.add_column("MEM%", justify="right")
    table.add_column("User", style="dim")
    table.add_column("Command", overflow="fold")

    for p in show:
        cpu_style = "bold red" if float(p["cpu"]) > 50 else ("yellow" if float(p["cpu"]) > 10 else "")
        table.add_row(
            p["pid"],
            f"[{cpu_style}]{p['cpu']}[/{cpu_style}]" if cpu_style else p["cpu"],
            p["mem"],
            p["user"],
            p["command"][:80],
        )

    total_label = f"  [dim]Showing top {len(show)} of {len(processes)}"
    if filter_name:
        total_label += f" matching '{filter_name}'"
    total_label += "[/dim]"

    _console.print(table)
    _console.print(total_label)


@register("kill", description="Kill a process by PID or name. Usage: kill <pid|name>")
def handle_kill(raw: str) -> None:
    parts = raw.strip().split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        jarvis_say("Usage: kill <pid> or kill <name>")
        return

    target = parts[1].strip()

    # If target is numeric, kill by PID directly
    if target.isdigit():
        pid = int(target)
        if _SYSTEM == "windows":
            _kill_pid_windows(pid)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                jarvis_say(f"[green]Sent SIGTERM to PID {pid}.[/green]")
            except ProcessLookupError:
                jarvis_say(f"[yellow]No process with PID {pid}.[/yellow]")
            except PermissionError:
                jarvis_say(f"[red]Permission denied for PID {pid}.[/red]")
        return

    # Kill by name — find matching processes first
    processes = _parse_ps()
    matches = [p for p in processes if target.lower() in p["command"].lower()]

    # Filter out our own process
    matches = [p for p in matches if p["pid"] != str(os.getpid())]

    if not matches:
        jarvis_say(f"[dim]No processes matching '{target}'.[/dim]")
        return

    jarvis_say(f"Found {len(matches)} process(es) matching '{target}':")
    for p in matches:
        _console.print(f"  PID [cyan]{p['pid']}[/cyan]  {p['command'][:60]}")

    confirmed = Confirm.ask(f"[yellow]Kill {len(matches)} process(es)?[/yellow]", default=False)
    if not confirmed:
        jarvis_say("Aborted.")
        return

    killed = 0
    for p in matches:
        try:
            if _SYSTEM == "windows":
                result = subprocess.run(
                    ["taskkill", "/PID", p["pid"], "/F"],
                    capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    killed += 1
            else:
                os.kill(int(p["pid"]), signal.SIGTERM)
                killed += 1
        except (ProcessLookupError, PermissionError, OSError):
            pass

    jarvis_say(f"[green]Killed {killed} of {len(matches)} process(es).[/green]")


def _kill_pid_windows(pid: int) -> None:
    try:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            jarvis_say(f"[green]Terminated PID {pid}.[/green]")
        else:
            jarvis_say(f"[red]Failed to terminate PID {pid}:[/red] {result.stderr.strip()}")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        jarvis_say(f"[red]Error:[/red] {e}")
