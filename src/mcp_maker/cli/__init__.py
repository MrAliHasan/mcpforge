"""MCP-Maker CLI — Command-line interface for auto-generating MCP servers."""

from . import chat, deploy, environment, generator, server
from .environment import _env_delete, _env_list, _env_read, _env_set, _env_show, _env_write, _mask_value
from .main import app, console

# Internal helpers re-exported for backwards compatibility with tests
from .server import _get_claude_config_path

__all__ = [
    "app", "console",
    "chat", "generator", "server", "environment", "deploy",
    "_get_claude_config_path",
    "_env_read", "_env_write", "_mask_value", "_env_set", "_env_list", "_env_show", "_env_delete",
]

