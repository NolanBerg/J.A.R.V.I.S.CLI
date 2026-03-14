"""AI skill — local LLM assistance via Ollama."""
from __future__ import annotations

import pathlib

from jarvis.core import jarvis_say, jarvis_thinking, register


@register(
    "ask",
    aliases=["ai"],
    description="Ask the local AI assistant. Usage: ask <question> | ai setup | ai status",
)
def handle_ask(raw: str) -> None:
    # Strip the command prefix
    query = raw.strip()
    for prefix in ("ask ", "ai "):
        if query.lower().startswith(prefix):
            query = query[len(prefix):].strip()
            break
    else:
        # Bare "ask" or "ai" with no argument
        query = ""

    lower = query.lower()

    if lower == "setup":
        _handle_setup()
    elif lower == "status":
        _handle_status()
    elif not query:
        jarvis_say(
            "Usage: [bold]ask <question>[/bold]  |  [bold]ai status[/bold]  |  [bold]ai setup[/bold]"
        )
    else:
        _run_chat(query)


def _handle_setup() -> None:
    """Full bootstrap: install Ollama if needed, start daemon, pull model."""
    from jarvis.ai.ollama_client import (
        MODEL,
        install_ollama,
        is_model_available,
        is_ollama_installed,
        is_ollama_running,
        pull_model,
        start_ollama_daemon,
    )

    # Step 1: ensure ollama binary exists
    if not is_ollama_installed():
        jarvis_say("Ollama is not installed. Attempting to install it now...")
        if not install_ollama():
            return  # install_ollama() already printed instructions

    # Step 2: ensure daemon is running
    if not is_ollama_running():
        jarvis_say("Starting Ollama daemon...")
        if not start_ollama_daemon():
            jarvis_say(
                "Could not start the Ollama daemon automatically.\n"
                "Please run [bold]ollama serve[/bold] in a separate terminal, "
                "then try [bold]ai setup[/bold] again."
            )
            return
        jarvis_say("Ollama daemon started.")

    # Step 3: pull model if needed
    if is_model_available():
        jarvis_say("AI is already set up and ready. Try: [bold]ask <your question>[/bold]")
        return

    jarvis_say(f"Pulling [bold]{MODEL}[/bold] — this may take a few minutes...")
    success = pull_model()
    if success:
        from jarvis.ai.context import refresh_cache
        refresh_cache()
        jarvis_say("Model downloaded successfully. AI is ready. Try: [bold]ask <your question>[/bold]")
    else:
        jarvis_say("Pull failed. Check your internet connection and try [bold]ai setup[/bold] again.")


def _handle_status() -> None:
    """Report Ollama + model availability."""
    from jarvis.ai.ollama_client import MODEL, is_model_available, is_ollama_running

    running = is_ollama_running()
    available = is_model_available() if running else False

    daemon_status = "[green]running[/green]" if running else "[red]not running[/red]"
    model_status = "[green]available[/green]" if available else "[yellow]not downloaded[/yellow]"

    jarvis_say(f"Ollama daemon: {daemon_status}")
    jarvis_say(f"Model ({MODEL}): {model_status}")

    if not running:
        jarvis_say("Run [bold]ai setup[/bold] to get started.")
    elif not available:
        jarvis_say("Run [bold]ai setup[/bold] to download the model.")


def _run_chat(query: str) -> None:
    """Send a query to the local LLM and display the response."""
    from jarvis.ai.ollama_client import MODEL, chat, is_model_available, is_ollama_running

    if not is_ollama_running():
        jarvis_say("Ollama is not running. Type [bold]ai setup[/bold] to get started.")
        return

    if not is_model_available():
        jarvis_say(f"{MODEL} is not downloaded yet. Type [bold]ai setup[/bold] to download it.")
        return

    with jarvis_thinking("Processing your query..."):
        response = chat(query)
    if response:
        jarvis_say(response)
    else:
        jarvis_say("I was unable to get a response from the AI. Is Ollama still running?")


# ---------------------------------------------------------------------------
# Clear conversation history
# ---------------------------------------------------------------------------

@register("forget", description="Clear AI conversation history.")
def handle_forget(raw: str) -> None:
    from jarvis.ai.ollama_client import clear_history

    clear_history()
    jarvis_say("Conversation history cleared. Starting fresh.")


# ---------------------------------------------------------------------------
# Summarize file
# ---------------------------------------------------------------------------

MAX_SUMMARIZE_BYTES = 50_000  # ~50 KB cap to avoid overwhelming the LLM


@register(
    "summarize",
    aliases=["sum"],
    description="Summarize a file using AI. Usage: summarize <file>",
)
def handle_summarize(raw: str) -> None:
    query = raw.strip()
    for prefix in ("summarize ", "sum "):
        if query.lower().startswith(prefix):
            query = query[len(prefix):].strip()
            break
    else:
        query = ""

    if not query:
        jarvis_say("Usage: [bold]summarize <file>[/bold]")
        return

    from jarvis.ai.ollama_client import MODEL, chat, is_model_available, is_ollama_running

    if not is_ollama_running():
        jarvis_say("Ollama is not running. Type [bold]ai setup[/bold] to get started.")
        return
    if not is_model_available():
        jarvis_say(f"{MODEL} is not downloaded yet. Type [bold]ai setup[/bold] to download it.")
        return

    path = pathlib.Path(query).expanduser().resolve()
    if not path.exists():
        jarvis_say(f"[red]Not found:[/red] {path}")
        return
    if not path.is_file():
        jarvis_say(f"[red]Not a file:[/red] {path}")
        return

    try:
        size = path.stat().st_size
        if size > MAX_SUMMARIZE_BYTES:
            jarvis_say(
                f"[yellow]File is {size / 1024:.0f} KB — "
                f"truncating to first {MAX_SUMMARIZE_BYTES // 1024} KB for summarization.[/yellow]"
            )
        content = path.read_text(encoding="utf-8", errors="replace")[:MAX_SUMMARIZE_BYTES]
    except (PermissionError, OSError) as e:
        jarvis_say(f"[red]Error reading file:[/red] {e}")
        return

    prompt = (
        f"Summarize the following file ({path.name}). "
        "Give a concise overview of its purpose, key sections, and important details.\n\n"
        f"```\n{content}\n```"
    )

    with jarvis_thinking(f"Summarizing {path.name}..."):
        response = chat(prompt, remember=False)

    if response:
        jarvis_say(response)
    else:
        jarvis_say("I was unable to get a response from the AI. Is Ollama still running?")
