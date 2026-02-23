"""
MCP-Maker MySQL Connector — Inspect MySQL databases.
"""

from urllib.parse import urlparse

from .base import BaseConnector, register_connector
from ..core.schema import (
    Column,
    DataSourceSchema,
    ForeignKey,
    Table,
    map_sql_type,
)


class MySQLConnector(BaseConnector):
    """Connector for MySQL databases.

    Inspects all tables, columns, types, primary keys, and row counts
    from a MySQL database.

    URI format: mysql://user:pass@host:port/dbname
    """

    @property
    def source_type(self) -> str:
        return "mysql"

    def _parse_uri(self) -> dict:
        """Parse MySQL URI into connection parameters."""
        parsed = urlparse(self.uri)
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": parsed.username or "root",
            "password": parsed.password or "",
            "database": parsed.path.lstrip("/"),
        }

    def validate(self) -> bool:
        """Check that the MySQL database is accessible."""
        try:
            import pymysql
        except ImportError:
            raise ImportError(
                "MySQL support requires pymysql.\n"
                "Install it with: pip install mcp-maker[mysql]"
            )

        params = self._parse_uri()
        try:
            conn = pymysql.connect(**params)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            raise ConnectionError(f"Cannot connect to MySQL: {e}")

    def inspect(self) -> DataSourceSchema:
        """Inspect the MySQL database and return its schema."""
        import pymysql
        import pymysql.cursors

        params = self._parse_uri()
        db_name = params["database"]
        conn = pymysql.connect(
            **params,
            cursorclass=pymysql.cursors.DictCursor,
        )
        cursor = conn.cursor()

        tables = []

        # Get all tables
        cursor.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = %s
              AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """,
            (db_name,),
        )
        table_names = [row["TABLE_NAME"] for row in cursor.fetchall()]

        for table_name in table_names:
            # Get columns with primary key info
            cursor.execute(
                """
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_KEY,
                    COLUMN_DEFAULT
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                  AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (db_name, table_name),
            )

            columns = []
            for col in cursor.fetchall():
                columns.append(Column(
                    name=col["COLUMN_NAME"],
                    type=map_sql_type(col["DATA_TYPE"]),
                    nullable=col["IS_NULLABLE"] == "YES",
                    primary_key=col["COLUMN_KEY"] == "PRI",
                ))

            # Get row count
            try:
                cursor.execute(
                    f"SELECT COUNT(*) as cnt FROM `{table_name}`"
                )
                row_count = cursor.fetchone()["cnt"]
            except Exception:
                row_count = None

            tables.append(Table(
                name=table_name,
                columns=columns,
                row_count=row_count,
            ))

        # Discover foreign key relationships
        foreign_keys = []
        try:
            cursor.execute(
                """
                SELECT
                    TABLE_NAME AS from_table,
                    COLUMN_NAME AS from_column,
                    REFERENCED_TABLE_NAME AS to_table,
                    REFERENCED_COLUMN_NAME AS to_column
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s
                  AND REFERENCED_TABLE_NAME IS NOT NULL
                """,
                (db_name,),
            )
            for row in cursor.fetchall():
                foreign_keys.append(ForeignKey(
                    from_table=row["from_table"],
                    from_column=row["from_column"],
                    to_table=row["to_table"],
                    to_column=row["to_column"],
                ))
        except Exception:
            pass

        cursor.close()
        conn.close()

        return DataSourceSchema(
            source_type="mysql",
            source_uri=self.uri,
            tables=tables,
            foreign_keys=foreign_keys,
            metadata={
                "database": db_name,
                "host": params["host"],
                "port": params["port"],
            },
        )


# Register this connector
register_connector("mysql", MySQLConnector)
