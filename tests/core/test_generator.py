import csv
import json
import os
import sqlite3
import tempfile

import pytest

from mcp_maker.core.schema import (
    Column,
    ColumnType,
    DataSourceSchema,
    Table,
    map_sql_type,
)
from mcp_maker.connectors.base import get_connector, register_connector
from mcp_maker.connectors.sqlite import SQLiteConnector
from mcp_maker.connectors.postgres import PostgresConnector
from mcp_maker.connectors.mysql import MySQLConnector
from mcp_maker.connectors.airtable import AirtableConnector
from mcp_maker.connectors.gsheets import GoogleSheetsConnector
from mcp_maker.connectors.notion import NotionConnector
from mcp_maker.connectors.files import FileConnector
from mcp_maker.core.generator import generate_server_code
from mcp_maker.cli import app
from typer.testing import CliRunner


class TestCodeGenerator:
    def test_generate_sqlite_server(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        # Should be valid Python
        compile(code, "<generated>", "exec")

        # Should contain expected tools
        assert "def list_users" in code
        assert "def list_posts" in code
        assert "def get_users_by_id" in code
        assert "def search_users" in code
        assert "def count_users" in code
        assert "def schema_users" in code

        # Should use FastMCP
        assert "from mcp.server.fastmcp import FastMCP" in code

    def test_generate_file_server(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        # Should be valid Python
        compile(code, "<generated>", "exec")

        # Should contain tools for products
        assert "def list_products" in code
        assert "def search_products" in code

        # Should contain resource for readme
        assert "read_readme" in code

    def test_generated_code_has_main(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        assert 'if __name__ == "__main__":' in code
        assert "mcp.run()" in code

    def test_generate_read_only_by_default(self, sample_db):
        """Verify that by default, write tools are NOT generated."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, ops=["read"]))

        assert "def insert_users" not in code
        assert "def update_users_by_id" not in code
        assert "def delete_users_by_id" not in code
        assert "def insert_posts" not in code

    def test_generate_read_write_mode(self, sample_db):
        """Verify that write tools ARE generated with read_only=False."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, ops=["read", "insert", "update", "delete"]))

        # Should be valid Python
        compile(code, "<generated>", "exec")

        # Should contain write tools
        assert "def insert_users" in code
        assert "def update_users_by_id" in code
        assert "def delete_users_by_id" in code

        # Should still have read tools
        assert "def list_users" in code
        assert "def get_users_by_id" in code
        assert "def search_users" in code

    def test_branding_in_generated_code(self, sample_db):
        """Verify template uses MCP-Maker branding, not MCPForge."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        assert "MCP-Maker" in code
        assert "mcp-maker" in code
        # Should NOT contain old branding
        assert "MCPForge" not in code
        assert "mcpforge" not in code


class TestGeneratedCodePatterns:
    """Tests to verify that generated code follows correct patterns."""

    def test_sqlite_uses_raise_on_error(self, sample_db):
        """Generated SQLite tools should raise RuntimeError, not return error dicts."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        assert 'raise RuntimeError' in code
        assert 'return {"error"' not in code

    def test_sqlite_write_has_rollback(self, sample_db):
        """Generated SQLite write tools should call conn.rollback() on error."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, ops=["read", "insert", "update", "delete"]))

        assert "conn.rollback()" in code
        assert 'raise RuntimeError(f"insert_' in code
        assert 'raise RuntimeError(f"update_' in code
        assert 'raise RuntimeError(f"delete_' in code

    def test_postgres_has_connection_pool(self):
        """Generated Postgres code should use a ThreadedConnectionPool."""
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="postgres",
            source_uri="postgresql://user:pass@localhost/testdb",
            tables=[
                Table(
                    name="items",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="name", type=ColumnType.STRING),
                    ],
                    row_count=10,
                )
            ],
        )
        code = "\n\n".join(generate_server_code(schema))

        assert "ThreadedConnectionPool" in code
        assert "_put_connection" in code
        assert "raise RuntimeError" in code
        assert 'return {"error"' not in code

    def test_mysql_has_connection_pool(self):
        """Generated MySQL code should use a queue-based connection pool."""
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="mysql",
            source_uri="mysql://user:pass@localhost/testdb",
            tables=[
                Table(
                    name="orders",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="total", type=ColumnType.FLOAT),
                    ],
                    row_count=5,
                )
            ],
            metadata={"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "testdb"},
        )
        code = "\n\n".join(generate_server_code(schema))

        assert "_mysql_pool" in code
        assert "_put_connection" in code
        assert "ping(reconnect=True)" in code
        assert "raise RuntimeError" in code
        assert 'return {"error"' not in code

    def test_large_schema_cli_warning(self):
        """CLI should warn when schema has >20 tables."""
        from typer.testing import CliRunner
        from mcp_maker.cli import app

        runner = CliRunner()

        # Create a SQLite DB with 25 tables
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            for i in range(25):
                conn.execute(f"CREATE TABLE table_{i} (id INTEGER PRIMARY KEY, name TEXT)")
                conn.execute(f"INSERT INTO table_{i} (name) VALUES ('test')")
            conn.commit()
            conn.close()

            result = runner.invoke(app, ["init", f"sqlite:///{db_path}"])
            assert "Large schema detected" in result.output
            assert "25 tables" in result.output
        finally:
            os.unlink(db_path)
            # Clean up generated file if it exists
            if os.path.isfile("mcp_server.py"):
                os.unlink("mcp_server.py")
