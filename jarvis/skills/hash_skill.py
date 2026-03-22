"""Hash / checksum skill for Jarvis CLI.

Commands:
  hash <file>              SHA-256 checksum (default)
  hash md5 <file>          MD5 checksum
  hash sha1 <file>         SHA-1 checksum
  hash sha256 <file>       SHA-256 checksum
  hash sha512 <file>       SHA-512 checksum
"""
from __future__ import annotations

import hashlib
import shlex

from jarvis.core import jarvis_say, register
from jarvis.fs.paths import resolve

_ALGORITHMS = {"md5", "sha1", "sha256", "sha512"}
_DEFAULT = "sha256"


def _tokens(raw: str) -> list[str]:
    parts = raw.strip().split(None, 1)
    text = parts[1] if len(parts) > 1 else ""
    try:
        return shlex.split(text)
    except ValueError:
        return text.split()


@register("hash", aliases=["checksum"], description="File checksum. Usage: hash <file>, hash md5 <file>")
def handle_hash(raw: str) -> None:
    tokens = _tokens(raw)
    if not tokens:
        jarvis_say("Usage: hash [algorithm] <file>  (algorithms: md5, sha1, sha256, sha512)")
        return

    # Determine algorithm and file path
    if tokens[0].lower() in _ALGORITHMS:
        algo = tokens[0].lower()
        if len(tokens) < 2:
            jarvis_say(f"Usage: hash {algo} <file>")
            return
        file_str = tokens[1]
    else:
        algo = _DEFAULT
        file_str = tokens[0]

    try:
        path = resolve(file_str, must_exist=True)
    except FileNotFoundError as e:
        jarvis_say(f"[red]Not found:[/red] {e}")
        return

    if path.is_dir():
        jarvis_say(f"[red]Is a directory:[/red] {path}")
        return

    try:
        h = hashlib.new(algo)
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
    except PermissionError as e:
        jarvis_say(f"[red]Permission denied:[/red] {e}")
        return
    except OSError as e:
        jarvis_say(f"[red]Error:[/red] {e}")
        return

    digest = h.hexdigest()
    jarvis_say(f"[bold]{algo.upper()}:[/bold] [cyan]{digest}[/cyan]  {path.name}")
