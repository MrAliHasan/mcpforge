"""
MCP-Maker PostgreSQL Connector — Inspect PostgreSQL databases.
"""

import re
from urllib.parse import urlparse

from .base import BaseConnector, register_connector
from ..core.schema import (
    Column,
    DataSourceSchema,
    Table,
    map_sql_type,
)


class PostgresConnector(BaseConnector):
    """Connector for PostgreSQL databases.

    Inspects all tables, columns, types, primary keys, and row counts
    from a PostgreSQL database.

    URI format: postgres://user:pass@host:port/dbname
                postgresql://user:pass@host:port/dbname
    """

    @property
    def source_type(self) -> str:
        return "postgres"

    def _get_dsn(self) -> str:
        """Return a psycopg2-compatible DSN from the URI."""
        uri = self.uri
        # Normalize scheme for psycopg2
        if uri.startswith("postgres://"):
            uri = "postgresql://" + uri[len("postgres://"):]
        return uri

    def _parse_schema(self) -> str:
        """Extract the schema name from the URI query string, default 'public'."""
        parsed = urlparse(self._get_dsn())
        # Check for ?schema=xxx in query params
        if parsed.query:
            params = dict(p.split("=", 1) for p in parsed.query.split("&") if "=" in p)
            return params.get("schema", "public")
        return "public"

    def validate(self) -> bool:
        """Check that the PostgreSQL database is accessible."""
        try:
            import psycopg2
        except ImportError:
            raise ImportError(
                "PostgreSQL support requires psycopg2.\n"
                "Install it with: pip install mcp-maker[postgres]"
            )

        try:
            conn = psycopg2.connect(self._get_dsn())
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            raise ConnectionError(f"Cannot connect to PostgreSQL: {e}")

    def inspect(self) -> DataSourceSchema:
        """Inspect the PostgreSQL database and return its schema."""
        import psycopg2
        import psycopg2.extras

        dsn = self._get_dsn()
        schema_name = self._parse_schema()
        conn = psycopg2.connect(dsn)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        tables = []

        # Get all tables in the schema
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """,
            (schema_name,),
        )
        table_names = [row["table_name"] for row in cursor.fetchall()]

        # Get primary keys for all tables at once
        cursor.execute(
            """
            SELECT
                kcu.table_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = %s
            """,
            (schema_name,),
        )
        pk_map: dict[str, set[str]] = {}
        for row in cursor.fetchall():
            pk_map.setdefault(row["table_name"], set()).add(row["column_name"])

        for table_name in table_names:
            # Get columns
            cursor.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = %s
                ORDER BY ordinal_position
                """,
                (schema_name, table_name),
            )

            pk_columns = pk_map.get(table_name, set())
            columns = []
            for col in cursor.fetchall():
                columns.append(Column(
                    name=col["column_name"],
                    type=map_sql_type(col["data_type"]),
                    nullable=col["is_nullable"] == "YES",
                    primary_key=col["column_name"] in pk_columns,
                ))

            # Get row count
            try:
                cursor.execute(
                    f'SELECT COUNT(*) as cnt FROM "{schema_name}"."{table_name}"'
                )
                row_count = cursor.fetchone()["cnt"]
            except Exception:
                row_count = None
                conn.rollback()

            tables.append(Table(
                name=table_name,
                columns=columns,
                row_count=row_count,
            ))

        cursor.close()
        conn.close()

        # Extract database name for metadata
        parsed = urlparse(dsn)
        db_name = parsed.path.lstrip("/") if parsed.path else "unknown"

        return DataSourceSchema(
            source_type="postgres",
            source_uri=self.uri,
            tables=tables,
            metadata={
                "database": db_name,
                "schema": schema_name,
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 5432,
            },
        )


# Register this connector for both schemes
register_connector("postgres", PostgresConnector)
register_connector("postgresql", PostgresConnector)
