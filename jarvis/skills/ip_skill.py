"""IP address skill for Jarvis CLI.

Commands:
  ip          Show local and public IP addresses
"""
from __future__ import annotations

import socket
import urllib.request

from rich.console import Console
from rich.table import Table

from jarvis.core import jarvis_say, register

_console = Console()


def _get_local_ip() -> str:
    """Get the local LAN IP by opening a dummy UDP socket."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "unavailable"


def _get_public_ip() -> str:
    """Get the public IP from an external service."""
    try:
        req = urllib.request.Request(
            "https://api.ipify.org",
            headers={"User-Agent": "Jarvis-CLI/0.1"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.read().decode("utf-8").strip()
    except Exception:
        return "unavailable"


@register("ip", description="Show local and public IP addresses.")
def handle_ip(raw: str) -> None:
    local = _get_local_ip()
    public = _get_public_ip()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Label", style="bold")
    table.add_column("Address", style="cyan")

    table.add_row("Local IP", local)
    table.add_row("Public IP", public)

    try:
        hostname = socket.gethostname()
        table.add_row("Hostname", hostname)
    except OSError:
        pass

    _console.print(table)
