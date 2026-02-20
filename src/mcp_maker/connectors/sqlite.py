"""
MCP-Maker SQLite Connector — Inspect SQLite databases.
"""

import os
import sqlite3

from .base import BaseConnector, register_connector
from ..core.schema import (
    Column,
    ColumnType,
    DataSourceSchema,
    Table,
    map_sql_type,
)


class SQLiteConnector(BaseConnector):
    """Connector for SQLite databases.

    Inspects all tables, columns, types, primary keys, and row counts.

    URI format: sqlite:///path/to/database.db
    """

    @property
    def source_type(self) -> str:
        return "sqlite"

    def _get_db_path(self) -> str:
        """Extract the file path from the SQLite URI."""
        path = self.uri
        if path.startswith("sqlite:///"):
            path = path[len("sqlite:///"):]
        elif path.startswith("sqlite://"):
            path = path[len("sqlite://"):]
        return os.path.expanduser(path)

    def validate(self) -> bool:
        """Check that the SQLite database file exists and is readable."""
        db_path = self._get_db_path()
        if not os.path.isfile(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
        # Try opening the database
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("SELECT 1")
            conn.close()
            return True
        except sqlite3.Error as e:
            raise ConnectionError(f"Cannot open database: {e}")

    def inspect(self) -> DataSourceSchema:
        """Inspect the SQLite database and return its schema."""
        db_path = self._get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        tables = []

        # Get all tables (exclude SQLite internal tables)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        table_names = [row["name"] for row in cursor.fetchall()]

        for table_name in table_names:
            # Get column info
            col_cursor = conn.execute(f"PRAGMA table_info('{table_name}')")
            columns = []
            for col in col_cursor.fetchall():
                columns.append(Column(
                    name=col["name"],
                    type=map_sql_type(col["type"] or "text"),
                    nullable=not col["notnull"],
                    primary_key=bool(col["pk"]),
                ))

            # Get row count
            try:
                count_cursor = conn.execute(
                    f"SELECT COUNT(*) as cnt FROM '{table_name}'"
                )
                row_count = count_cursor.fetchone()["cnt"]
            except sqlite3.Error:
                row_count = None

            tables.append(Table(
                name=table_name,
                columns=columns,
                row_count=row_count,
            ))

        conn.close()

        return DataSourceSchema(
            source_type="sqlite",
            source_uri=self.uri,
            tables=tables,
            metadata={
                "db_path": db_path,
                "file_size_bytes": os.path.getsize(db_path),
            },
        )


# Register this connector
register_connector("sqlite", SQLiteConnector)
