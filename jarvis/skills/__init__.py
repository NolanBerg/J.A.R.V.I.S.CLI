"""Import all skill modules here so their @register decorators fire on load."""

from jarvis.skills import builtins as builtins  # noqa: F401
from jarvis.skills import ai_skill as ai_skill  # noqa: F401
from jarvis.skills import fs_skill as fs_skill  # noqa: F401
from jarvis.skills import sysnet_skill as sysnet_skill  # noqa: F401
from jarvis.skills import weather_skill as weather_skill  # noqa: F401
from jarvis.skills import clipboard_skill as clipboard_skill  # noqa: F401
from jarvis.skills import note_skill as note_skill  # noqa: F401
from jarvis.skills import remind_skill as remind_skill  # noqa: F401
from jarvis.skills import plugin_skill as plugin_skill  # noqa: F401
from jarvis.skills import alias_skill as alias_skill  # noqa: F401
from jarvis.skills import env_skill as env_skill  # noqa: F401
from jarvis.skills import calc_skill as calc_skill  # noqa: F401
from jarvis.skills import fileutil_skill as fileutil_skill  # noqa: F401
from jarvis.skills import todo_skill as todo_skill  # noqa: F401
from jarvis.skills import json_skill as json_skill  # noqa: F401
from jarvis.skills import ip_skill as ip_skill  # noqa: F401
from jarvis.skills import process_skill as process_skill  # noqa: F401
from jarvis.skills import replace_skill as replace_skill  # noqa: F401
from jarvis.skills import hash_skill as hash_skill  # noqa: F401
from jarvis.skills import tree_skill as tree_skill  # noqa: F401
from jarvis.skills import cron_skill as cron_skill  # noqa: F401
