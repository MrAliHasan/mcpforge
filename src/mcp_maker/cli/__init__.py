"""MCP-Maker CLI — Command-line interface for auto-generating MCP servers."""

from .main import app, console
from . import generator
from . import server
from . import environment
from . import deploy

# Internal helpers re-exported for backwards compatibility with tests
from .server import _get_claude_config_path
from .environment import _env_read, _env_write, _mask_value, _env_set, _env_list, _env_show, _env_delete

__all__ = [
    "app", "console",
    "generator", "server", "environment", "deploy",
    "_get_claude_config_path",
    "_env_read", "_env_write", "_mask_value", "_env_set", "_env_list", "_env_show", "_env_delete",
]

