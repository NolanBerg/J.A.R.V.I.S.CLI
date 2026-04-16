"""Clipboard skill — copy text or file contents, paste clipboard."""
from __future__ import annotations

import platform
import subprocess

from jarvis.core import console, jarvis_say, register
from jarvis.fs.paths import resolve


def _system() -> str:
    return platform.system().lower()


def _copy_to_clipboard(text: str) -> bool:
    """Send text to system clipboard. Returns True on success."""
    sys = _system()
    if sys == "darwin":
        cmd = ["pbcopy"]
        try:
            subprocess.run(cmd, input=text.encode(), check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False
    elif sys == "linux":
        # Try xclip first, fall back to xsel
        for cmd in (
            ["xclip", "-selection", "clipboard"],
            ["xsel", "--clipboard", "--input"],
        ):
            try:
                subprocess.run(cmd, input=text.encode(), check=True)
                return True
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        return False
    elif sys == "windows":
        try:
            # `clip` reads from stdin on Windows
            subprocess.run(["clip"], input=text.encode("utf-16-le"), check=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False
    return False


def _read_clipboard() -> str | None:
    """Read text from system clipboard."""
    sys = _system()
    if sys == "darwin":
        try:
            result = subprocess.run(["pbpaste"], capture_output=True, text=True, check=True)
            return result.stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
    elif sys == "linux":
        for cmd in (
            ["xclip", "-selection", "clipboard", "-o"],
            ["xsel", "--clipboard", "--output"],
        ):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                return result.stdout
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        return None
    elif sys == "windows":
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True, text=True, check=True,
            )
            return result.stdout
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
    return None


@register(
    "copy",
    aliases=["clip"],
    description="Copy text or file contents to clipboard. Usage: copy <file|text>",
)
def handle_copy(raw: str) -> None:
    parts = raw.strip().split(None, 1)
    arg = parts[1] if len(parts) > 1 else ""
    if not arg:
        jarvis_say("Usage: copy <file_path> or copy <text>")
        return

    # Check if arg is a file path
    try:
        path = resolve(arg, must_exist=True)
        if path.is_file():
            from jarvis.fs.ops import fs_cat

            text = fs_cat(path)
            if _copy_to_clipboard(text):
                jarvis_say(
                    f"Copied contents of [bold]{path.name}[/bold] to clipboard."
                )
            else:
                jarvis_say("[red]Clipboard not available on this platform.[/red]")
            return
    except (FileNotFoundError, ValueError, IsADirectoryError):
        pass

    # Treat as literal text
    if _copy_to_clipboard(arg):
        jarvis_say(f"Copied to clipboard. [dim]({len(arg)} chars)[/dim]")
    else:
        jarvis_say("[red]Clipboard not available on this platform.[/red]")


@register("paste", description="Output clipboard contents.")
def handle_paste(raw: str) -> None:
    text = _read_clipboard()
    if text is None:
        jarvis_say("[red]Clipboard not available on this platform.[/red]")
    elif not text:
        jarvis_say("[dim]Clipboard is empty.[/dim]")
    else:
        console.print(text)
