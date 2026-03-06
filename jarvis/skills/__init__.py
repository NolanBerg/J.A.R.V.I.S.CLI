"""Import all skill modules here so their @register decorators fire on load."""

from jarvis.skills import builtins as builtins  # noqa: F401
from jarvis.skills import ai_skill as ai_skill  # noqa: F401
from jarvis.skills import fs_skill as fs_skill  # noqa: F401
