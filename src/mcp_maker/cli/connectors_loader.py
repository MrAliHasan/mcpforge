"""Lazy loading of optional connectors.

Imports all built-in and optional connectors to trigger their
registration with the connector registry. Missing third-party
dependencies are silently skipped.
"""

import importlib
import logging

logger = logging.getLogger(__name__)

# Built-in connectors (always available)
_BUILTIN = ("sqlite", "files")

# Optional connectors (skip if dependencies missing)
_OPTIONAL = (
    "postgres",
    "mysql",
    "airtable",
    "gsheets",
    "notion",
    "excel",
    "mongodb",
    "supabase",
    "openapi",
    "redis",
    "hubspot",
)


def _try_load(name: str) -> None:
    """Attempt to import a connector module, suppressing missing dependency errors."""
    try:
        importlib.import_module(f"mcp_maker.connectors.{name}")
    except ModuleNotFoundError as e:
        missing = getattr(e, "name", "") or ""
        # Connector module itself doesn't exist — skip
        if missing == f"mcp_maker.connectors.{name}":
            return
        # Third-party dependency missing (e.g. psycopg2) — skip
        if not missing.startswith("mcp_maker"):
            return
        # Internal import error — warn
        logger.warning("Connector '%s' has an internal import error: %s", name, e)
    except Exception as e:
        logger.warning("Failed to load connector '%s': %s", name, e)


def load_all_connectors() -> None:
    """Import all connectors to trigger registration."""
    for name in _BUILTIN:
        importlib.import_module(f"mcp_maker.connectors.{name}")
    for name in _OPTIONAL:
        _try_load(name)
