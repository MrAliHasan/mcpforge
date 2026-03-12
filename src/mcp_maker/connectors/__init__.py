"""
MCP-Maker Connectors — Inspect data sources and generate schemas.

Each connector knows how to connect to a specific data source type,
inspect its structure, and produce a universal MCP-Maker schema.
"""

from .base import BaseConnector
from .files import FileConnector
from .sqlite import SQLiteConnector

# Optional connectors — only import if their dependencies are available
try:
    from .postgres import PostgresConnector
except ImportError:
    PostgresConnector = None  # type: ignore

try:
    from .mysql import MySQLConnector
except ImportError:
    MySQLConnector = None  # type: ignore

try:
    from .airtable import AirtableConnector
except ImportError:
    AirtableConnector = None  # type: ignore

try:
    from .gsheets import GoogleSheetsConnector
except ImportError:
    GoogleSheetsConnector = None  # type: ignore

try:
    from .notion import NotionConnector
except ImportError:
    NotionConnector = None  # type: ignore

try:
    from .hubspot import HubSpotConnector
except ImportError:
    HubSpotConnector = None  # type: ignore

try:
    from .excel import ExcelConnector
except ImportError:
    ExcelConnector = None  # type: ignore

try:
    from .mongodb import MongoDBConnector
except ImportError:
    MongoDBConnector = None  # type: ignore

try:
    from .supabase_connector import SupabaseConnector
except (ImportError, AttributeError):
    try:
        from .supabase import SupabaseConnector  # type: ignore
    except ImportError:
        SupabaseConnector = None  # type: ignore

try:
    from .openapi import OpenAPIConnector
except ImportError:
    OpenAPIConnector = None  # type: ignore

try:
    from .redis import RedisConnector
except ImportError:
    RedisConnector = None  # type: ignore

__all__ = ["BaseConnector", "SQLiteConnector", "FileConnector"]

if PostgresConnector is not None:
    __all__.append("PostgresConnector")
if MySQLConnector is not None:
    __all__.append("MySQLConnector")
if AirtableConnector is not None:
    __all__.append("AirtableConnector")
if GoogleSheetsConnector is not None:
    __all__.append("GoogleSheetsConnector")
if NotionConnector is not None:
    __all__.append("NotionConnector")
if HubSpotConnector is not None:
    __all__.append("HubSpotConnector")
if ExcelConnector is not None:
    __all__.append("ExcelConnector")
if MongoDBConnector is not None:
    __all__.append("MongoDBConnector")
if SupabaseConnector is not None:
    __all__.append("SupabaseConnector")
if OpenAPIConnector is not None:
    __all__.append("OpenAPIConnector")
if RedisConnector is not None:
    __all__.append("RedisConnector")
