"""Plugin management skill — list loaded external plugins."""
from __future__ import annotations

from rich.console import Console

from jarvis.core import jarvis_say, register

_console = Console()


@register(
    "plugin",
    aliases=["plugins"],
    description="List loaded plugins. Usage: plugin list",
)
def handle_plugin(raw: str) -> None:
    from jarvis.core import _loaded_plugins

    if not _loaded_plugins:
        jarvis_say(
            "No plugins loaded. Drop [bold].py[/bold] files in "
            "[bold]~/.jarvis/plugins/[/bold] to extend Jarvis."
        )
        return

    jarvis_say(f"{len(_loaded_plugins)} plugin(s) loaded:")
    for name in _loaded_plugins:
        _console.print(f"  [cyan]\u2022[/cyan] {name}")
