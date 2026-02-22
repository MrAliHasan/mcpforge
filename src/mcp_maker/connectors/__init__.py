"""
MCP-Maker Connectors — Inspect data sources and generate schemas.

Each connector knows how to connect to a specific data source type,
inspect its structure, and produce a universal MCP-Maker schema.
"""

from .base import BaseConnector
from .sqlite import SQLiteConnector
from .files import FileConnector

# Optional connectors — only import if their dependencies are available
try:
    from .postgres import PostgresConnector
except ImportError:
    PostgresConnector = None  # type: ignore

try:
    from .mysql import MySQLConnector
except ImportError:
    MySQLConnector = None  # type: ignore

__all__ = ["BaseConnector", "SQLiteConnector", "FileConnector"]

if PostgresConnector is not None:
    __all__.append("PostgresConnector")
if MySQLConnector is not None:
    __all__.append("MySQLConnector")
