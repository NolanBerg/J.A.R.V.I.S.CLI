# J.A.R.V.I.S.

Just A Rather Very Intelligent System — an extensible command-line assistant based on J.A.R.V.I.S from Iron Man.

## Prerequisites

- Python 3.11+
- [pipx](https://pipx.pypa.io) (recommended) or pip

## Install

### macOS / Linux

```bash
# Option A — pipx (globally available, isolated)
pipx install .

# Option B — editable install in a venv (for development)
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Windows

```powershell
# Install Python 3.11+ from https://python.org first, then:
pipx install .

# Or with a venv:
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

## First run

```bash
jarvis
```

## Enable AI (optional)

Jarvis can use a local LLM via [Ollama](https://ollama.com) with context via JSON file to help with commands. One command handles everything:

```bash
jarvis "ai setup"
```

This will:
1. Install Ollama if it's not already installed
2. Start the Ollama daemon
3. Download the AI model (`qwen2.5-coder:7b`)

Check status anytime:

```bash
jarvis "ai status"
```

## Commands

| Command | Description |
|---------|-------------|
| `help` / `?` | Show all capabilities |
| `time` / `date` | Current date and time |
| `open <app or URL>` | Open an application or URL |
| `who are you` / `identity` | Ask Jarvis about itself |
| `ask <question>` | Ask the local AI a question |
| `ai setup` | Install Ollama + download model |
| `ai status` | Check Ollama and model status |
| `exit` / `quit` / `q` | Shut down |

## One-shot mode

```bash
jarvis "time"
jarvis "open https://github.com"
jarvis "ask what commands do you have?"
```

## Adding a skill

1. Create `jarvis/skills/myskill.py`
2. Add one line to `jarvis/skills/__init__.py`

```python
# jarvis/skills/myskill.py
from jarvis.core import jarvis_say, register

@register("greet", aliases=["hello"], description="Say hello.")
def handle_greet(raw: str) -> None:
    jarvis_say("Hello!")
```

```python
# jarvis/skills/__init__.py — add:
from jarvis.skills import myskill as myskill  # noqa: F401
```

## Project structure

```
jarvis/
├── core.py              # registry, REPL, CLI
├── skills/
│   ├── __init__.py      # imports all skill modules
│   ├── builtins.py      # built-in commands
│   └── ai_skill.py      # ask / ai commands
└── ai/
    ├── ollama_client.py # Ollama REST client (stdlib only)
    └── context.py       # commands context for the AI
pyproject.toml
```
