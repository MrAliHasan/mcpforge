"""
MCPForge Connectors — Inspect data sources and generate schemas.

Each connector knows how to connect to a specific data source type,
inspect its structure, and produce a universal MCPForge schema.
"""

from .base import BaseConnector
from .sqlite import SQLiteConnector
from .files import FileConnector

__all__ = ["BaseConnector", "SQLiteConnector", "FileConnector"]
