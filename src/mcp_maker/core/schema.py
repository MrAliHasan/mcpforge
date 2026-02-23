"""
MCP-Maker Schema — Universal data source representation.

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
class ForeignKey:
    """A foreign key relationship between tables."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str

    @property
    def join_name(self) -> str:
        """Generate a descriptive join tool name."""
        return f"join_{self.from_table}_with_{self.to_table}"


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

    foreign_keys: List[ForeignKey] = field(default_factory=list)
    """Foreign key relationships between tables."""

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

    @property
    def schema_hash(self) -> str:
        """Compute a stable SHA-256 fingerprint of the schema structure.

        The hash covers table names, column names, column types, and primary keys
        so that any structural change to the schema produces a different hash.
        """
        import hashlib
        import json

        canonical = []
        for t in sorted(self.tables, key=lambda t: t.name):
            cols = []
            for c in sorted(t.columns, key=lambda c: c.name):
                cols.append({
                    "name": c.name,
                    "type": c.type.value,
                    "pk": c.primary_key,
                })
            canonical.append({"table": t.name, "columns": cols})

        blob = json.dumps(canonical, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    @property
    def table_names(self) -> list[str]:
        """Return sorted list of table names."""
        return sorted(t.name for t in self.tables)

    @staticmethod
    def schema_diff(old_tables: list[str], new_tables: list[str],
                    old_columns: dict | None = None,
                    new_columns: dict | None = None) -> dict:
        """Compute added, removed tables and column-level changes.

        Args:
            old_tables: Previous table names.
            new_tables: Current table names.
            old_columns: Optional dict of {table: {col: type}} from old lock.
            new_columns: Optional dict of {table: {col: type}} from new schema.
        """
        old_set = set(old_tables)
        new_set = set(new_tables)
        result = {
            "added": sorted(new_set - old_set),
            "removed": sorted(old_set - new_set),
            "column_changes": {},
        }
        # Column-level diff for tables that exist in both
        if old_columns and new_columns:
            for table in sorted(old_set & new_set):
                old_cols = old_columns.get(table, {})
                new_cols = new_columns.get(table, {})
                changes = {}
                added_cols = sorted(set(new_cols) - set(old_cols))
                removed_cols = sorted(set(old_cols) - set(new_cols))
                type_changed = sorted(
                    c for c in set(old_cols) & set(new_cols)
                    if old_cols[c] != new_cols[c]
                )
                if added_cols:
                    changes["added"] = added_cols
                if removed_cols:
                    changes["removed"] = removed_cols
                if type_changed:
                    changes["type_changed"] = type_changed
                if changes:
                    result["column_changes"][table] = changes
        return result

    @property
    def column_fingerprint(self) -> dict[str, dict[str, str]]:
        """Return {table: {col: type}} for lock file storage."""
        return {
            t.name: {c.name: c.type.value for c in t.columns}
            for t in self.tables
        }

