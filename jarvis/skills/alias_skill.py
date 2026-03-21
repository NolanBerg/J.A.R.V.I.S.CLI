"""Alias skill for Jarvis CLI.

Commands:
  alias <name>=<command>   Create a shorthand alias
  alias list               Show all aliases
  alias rm <name>          Remove an alias
"""
from __future__ import annotations

from jarvis import config
from jarvis.core import dispatch, jarvis_say, register

_CONFIG_KEY = "aliases"


def _load_aliases() -> dict[str, str]:
    return config.get(_CONFIG_KEY, {})


def _save_aliases(aliases: dict[str, str]) -> None:
    config.set(_CONFIG_KEY, aliases)


@register("alias", description="Manage aliases. Usage: alias <name>=<cmd>, alias list, alias rm <name>")
def handle_alias(raw: str) -> None:
    text = raw.strip().split(None, 1)
    arg = text[1].strip() if len(text) > 1 else ""

    if not arg or arg == "list":
        aliases = _load_aliases()
        if not aliases:
            jarvis_say("No aliases defined. Create one with: alias ll=ls -la")
            return
        lines = [f"  [cyan]{name}[/cyan] → {cmd}" for name, cmd in sorted(aliases.items())]
        jarvis_say("Aliases:\n" + "\n".join(lines))
        return

    if arg.startswith("rm "):
        name = arg[3:].strip()
        aliases = _load_aliases()
        if name not in aliases:
            jarvis_say(f"[yellow]No alias named '{name}'.[/yellow]")
            return
        del aliases[name]
        _save_aliases(aliases)
        jarvis_say(f"[green]Removed alias[/green] '{name}'.")
        return

    # Create alias: alias name=command
    if "=" not in arg:
        jarvis_say("Usage: alias <name>=<command>  (e.g. alias ll=ls -la)")
        return

    name, cmd = arg.split("=", 1)
    name = name.strip()
    cmd = cmd.strip()

    if not name or not cmd:
        jarvis_say("Usage: alias <name>=<command>")
        return

    aliases = _load_aliases()
    aliases[name] = cmd
    _save_aliases(aliases)
    jarvis_say(f"[green]Alias set:[/green] [cyan]{name}[/cyan] → {cmd}")


def try_alias(raw: str) -> bool:
    """Try to expand and dispatch an alias. Called from the REPL before AI fallback.

    Returns True if an alias matched and was dispatched.
    """
    cmd = raw.strip().lower()
    aliases = _load_aliases()

    for alias_name, alias_cmd in aliases.items():
        if cmd == alias_name.lower():
            # Exact match — run the alias command
            return dispatch(alias_cmd)
        if cmd.startswith(alias_name.lower() + " "):
            # Prefix match — append remaining args
            rest = raw.strip()[len(alias_name):].strip()
            return dispatch(f"{alias_cmd} {rest}")

    return False
