"""Pure-stdlib Ollama REST client. Zero external dependencies."""
from __future__ import annotations

import json
import platform
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Optional

OLLAMA_BASE = "http://localhost:11434"
MODEL = "qwen2.5-coder:7b"

SYSTEM_PROMPT_TEMPLATE = """\
You are J.A.R.V.I.S., a helpful command-line assistant embedded in a Python CLI tool called Jarvis.
You have access to the following Jarvis command registry (JSON):

{commands_json}

Your role:
1. Help the user understand what commands are available and how to use them.
2. When the user asks about a task that matches a Jarvis command, tell them exactly what to type.
3. When the user's input does not match any command, acknowledge that and suggest the closest relevant command.
4. Keep answers concise and terminal-friendly — no markdown headers, minimal formatting.
5. You are running locally via Ollama. Never claim to be a cloud service.
"""


def is_ollama_running() -> bool:
    """Return True if the Ollama daemon is reachable at localhost:11434."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def is_model_available() -> bool:
    """Return True if the model is already pulled locally."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=2) as resp:
            data = json.loads(resp.read())
            return any(
                m["name"].startswith(MODEL.split(":")[0])
                for m in data.get("models", [])
            )
    except Exception:
        return False


def is_ollama_installed() -> bool:
    """Return True if the ollama binary is on PATH."""
    return shutil.which("ollama") is not None


def install_ollama() -> bool:
    """Attempt to install Ollama. Returns True if install succeeded."""
    system = platform.system().lower()
    from jarvis.core import jarvis_say

    if system == "darwin":
        if shutil.which("brew"):
            jarvis_say("Installing Ollama via Homebrew...")
            result = subprocess.run(["brew", "install", "ollama"], capture_output=False)
            return result.returncode == 0
        else:
            jarvis_say(
                "Homebrew not found. Please download Ollama manually:\n"
                "  https://ollama.com/download\n"
                "Then run [bold]ai setup[/bold] again."
            )
            return False

    if system == "linux":
        jarvis_say("Installing Ollama via install script...")
        result = subprocess.run(
            "curl -fsSL https://ollama.ai/install.sh | sh",
            shell=True,
        )
        return result.returncode == 0

    # Windows or unknown
    jarvis_say(
        "Automatic Ollama installation is not supported on this platform.\n"
        "Please download and install it from: https://ollama.com/download\n"
        "Then run [bold]ai setup[/bold] again."
    )
    return False


def start_ollama_daemon() -> bool:
    """Start `ollama serve` in the background. Returns True if daemon comes up within 5s."""
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False
    for _ in range(10):
        time.sleep(0.5)
        if is_ollama_running():
            return True
    return False


def pull_model() -> bool:
    """Pull the model, streaming progress. Returns True on success."""
    # Try subprocess first (shows native ollama progress bar)
    try:
        proc = subprocess.Popen(
            ["ollama", "pull", MODEL],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in proc.stdout:
            print(line, end="", flush=True)
        proc.wait()
        return proc.returncode == 0
    except FileNotFoundError:
        pass  # ollama binary not on PATH, try REST API

    # Fallback: POST /api/pull with stream=True
    payload = json.dumps({"model": MODEL, "stream": True}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/pull",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for raw_line in resp:
                line = raw_line.decode().strip()
                if not line:
                    continue
                event = json.loads(line)
                status = event.get("status", "")
                completed = event.get("completed")
                total = event.get("total")
                if total:
                    pct = int(completed / total * 100)
                    print(f"\r  {status}: {pct}%", end="", flush=True)
                else:
                    print(f"  {status}")
        print()
        return True
    except Exception as exc:
        print(f"\n  Pull failed: {exc}")
        return False


def chat(user_message: str) -> Optional[str]:
    """Send a message to the local LLM and return the response text."""
    from jarvis.ai.context import get_commands_json

    try:
        commands_json = get_commands_json()
    except Exception:
        commands_json = "{}"

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(commands_json=commands_json)

    payload = json.dumps({
        "model": MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }).encode()

    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["message"]["content"].strip()
    except Exception:
        return None


def ai_fallback(raw: str) -> None:
    """Called by the REPL when dispatch() returns False."""
    from jarvis.core import jarvis_say

    if not is_ollama_running():
        jarvis_say(
            "That command is not yet in my repertoire. "
            "Type [bold]ai setup[/bold] to enable AI-assisted suggestions, "
            "or [bold]help[/bold] for available commands."
        )
        return

    if not is_model_available():
        jarvis_say(
            "That command is not yet in my repertoire. "
            f"AI is available but {MODEL} is not downloaded yet. "
            "Type [bold]ai setup[/bold] to download it."
        )
        return

    jarvis_say("I don't recognise that command. Let me ask the AI...")
    response = chat(
        f"The user typed: '{raw}'. "
        "This did not match any Jarvis command. "
        "Suggest what they might have meant or which command to use."
    )
    if response:
        jarvis_say(response)
    else:
        jarvis_say(
            "That command is not yet in my repertoire. "
            "Type [bold]help[/bold] for available options."
        )
