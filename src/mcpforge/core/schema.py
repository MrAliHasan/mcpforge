"""
MCPForge Schema — Universal data source representation.

This module defines the schema types that all connectors produce.
The generator then uses these schemas to create MCP server code.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ColumnType(str, Enum):
    """Universal column type mappings."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    BLOB = "blob"
    UNKNOWN = "unknown"


# Map common SQL types to universal types
SQL_TYPE_MAP: Dict[str, ColumnType] = {
    # String types
    "text": ColumnType.STRING,
    "varchar": ColumnType.STRING,
    "char": ColumnType.STRING,
    "nvarchar": ColumnType.STRING,
    "nchar": ColumnType.STRING,
    "clob": ColumnType.STRING,
    "character varying": ColumnType.STRING,
    # Integer types
    "integer": ColumnType.INTEGER,
    "int": ColumnType.INTEGER,
    "smallint": ColumnType.INTEGER,
    "bigint": ColumnType.INTEGER,
    "tinyint": ColumnType.INTEGER,
    "serial": ColumnType.INTEGER,
    "bigserial": ColumnType.INTEGER,
    # Float types
    "real": ColumnType.FLOAT,
    "float": ColumnType.FLOAT,
    "double": ColumnType.FLOAT,
    "decimal": ColumnType.FLOAT,
    "numeric": ColumnType.FLOAT,
    "double precision": ColumnType.FLOAT,
    # Boolean
    "boolean": ColumnType.BOOLEAN,
    "bool": ColumnType.BOOLEAN,
    # Date/time
    "date": ColumnType.DATE,
    "datetime": ColumnType.DATETIME,
    "timestamp": ColumnType.DATETIME,
    "timestamp without time zone": ColumnType.DATETIME,
    "timestamp with time zone": ColumnType.DATETIME,
    # JSON
    "json": ColumnType.JSON,
    "jsonb": ColumnType.JSON,
    # Binary
    "blob": ColumnType.BLOB,
    "bytea": ColumnType.BLOB,
}


def map_sql_type(sql_type: str) -> ColumnType:
    """Map a SQL type string to a universal ColumnType."""
    normalized = sql_type.lower().strip()
    # Try exact match first
    if normalized in SQL_TYPE_MAP:
        return SQL_TYPE_MAP[normalized]
    # Try prefix match (e.g., "varchar(255)" → "varchar")
    for key, value in SQL_TYPE_MAP.items():
        if normalized.startswith(key):
            return value
    return ColumnType.UNKNOWN


@dataclass
class Column:
    """A column/field in a table or data structure."""

    name: str
    type: ColumnType
    nullable: bool = True
    primary_key: bool = False
    description: Optional[str] = None


@dataclass
class Table:
    """A table or collection in the data source."""

    name: str
    columns: List[Column] = field(default_factory=list)
    row_count: Optional[int] = None
    description: Optional[str] = None

    @property
    def primary_key_columns(self) -> List[Column]:
        return [c for c in self.columns if c.primary_key]

    @property
    def searchable_columns(self) -> List[Column]:
        return [
            c for c in self.columns
            if c.type in (ColumnType.STRING, ColumnType.INTEGER)
        ]


@dataclass
class Resource:
    """A read-only resource (file, static data, etc.)."""

    name: str
    uri: str
    mime_type: str = "text/plain"
    description: Optional[str] = None


@dataclass
class DataSourceSchema:
    """Complete schema of an inspected data source.

    This is the universal output that all connectors produce
    and that the generator consumes to create MCP server code.
    """

    source_type: str
    """Type of data source (e.g., 'sqlite', 'postgres', 'files')."""

    source_uri: str
    """Connection string or path to the data source."""

    tables: List[Table] = field(default_factory=list)
    """Tables/collections discovered in the data source."""

    resources: List[Resource] = field(default_factory=list)
    """Static resources (files, etc.) discovered."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the data source."""

    @property
    def summary(self) -> str:
        parts = [f"Source: {self.source_type} ({self.source_uri})"]
        if self.tables:
            parts.append(f"Tables: {len(self.tables)}")
            for t in self.tables:
                cols = ", ".join(c.name for c in t.columns[:5])
                suffix = "..." if len(t.columns) > 5 else ""
                row_info = f" ({t.row_count} rows)" if t.row_count else ""
                parts.append(f"  • {t.name}{row_info}: {cols}{suffix}")
        if self.resources:
            parts.append(f"Resources: {len(self.resources)}")
            for r in self.resources:
                parts.append(f"  • {r.name} [{r.mime_type}]")
        return "\n".join(parts)
