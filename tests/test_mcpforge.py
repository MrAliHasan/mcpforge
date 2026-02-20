"""
Tests for MCP-Maker core functionality.
"""

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
from mcp_maker.connectors.files import FileConnector
from mcp_maker.core.generator import generate_server_code


# ─── Schema Tests ───


class TestSchema:
    def test_map_sql_type_exact(self):
        assert map_sql_type("integer") == ColumnType.INTEGER
        assert map_sql_type("TEXT") == ColumnType.STRING
        assert map_sql_type("boolean") == ColumnType.BOOLEAN
        assert map_sql_type("timestamp") == ColumnType.DATETIME

    def test_map_sql_type_prefix(self):
        assert map_sql_type("varchar(255)") == ColumnType.STRING
        assert map_sql_type("decimal(10,2)") == ColumnType.FLOAT

    def test_map_sql_type_unknown(self):
        assert map_sql_type("custom_type_xyz") == ColumnType.UNKNOWN

    def test_table_primary_keys(self):
        table = Table(
            name="users",
            columns=[
                Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                Column(name="name", type=ColumnType.STRING),
            ],
        )
        assert len(table.primary_key_columns) == 1
        assert table.primary_key_columns[0].name == "id"

    def test_table_searchable_columns(self):
        table = Table(
            name="users",
            columns=[
                Column(name="id", type=ColumnType.INTEGER),
                Column(name="name", type=ColumnType.STRING),
                Column(name="created_at", type=ColumnType.DATETIME),
            ],
        )
        searchable = table.searchable_columns
        assert len(searchable) == 2
        assert searchable[0].name == "id"
        assert searchable[1].name == "name"

    def test_schema_summary(self):
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(
                    name="users",
                    columns=[Column(name="id", type=ColumnType.INTEGER)],
                    row_count=42,
                )
            ],
        )
        summary = schema.summary
        assert "sqlite" in summary
        assert "users" in summary
        assert "42" in summary


# ─── SQLite Connector Tests ───


@pytest.fixture
def sample_db():
    """Create a temporary SQLite database with sample data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            age INTEGER,
            active BOOLEAN DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            title TEXT,
            content TEXT,
            created_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        ("Alice", "alice@example.com", 30),
    )
    conn.execute(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        ("Bob", "bob@example.com", 25),
    )
    conn.execute(
        "INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
        (1, "Hello World", "First post content"),
    )
    conn.commit()
    conn.close()

    yield db_path
    os.unlink(db_path)


class TestSQLiteConnector:
    def test_validate_valid_db(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        assert connector.validate() is True

    def test_validate_missing_file(self):
        connector = SQLiteConnector("sqlite:///nonexistent.db")
        with pytest.raises(FileNotFoundError):
            connector.validate()

    def test_inspect_tables(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()

        assert schema.source_type == "sqlite"
        assert len(schema.tables) == 2

        # Check table names
        table_names = [t.name for t in schema.tables]
        assert "users" in table_names
        assert "posts" in table_names

    def test_inspect_columns(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()

        users = next(t for t in schema.tables if t.name == "users")
        col_names = [c.name for c in users.columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert "age" in col_names

    def test_inspect_primary_key(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()

        users = next(t for t in schema.tables if t.name == "users")
        pk_cols = users.primary_key_columns
        assert len(pk_cols) == 1
        assert pk_cols[0].name == "id"

    def test_inspect_row_count(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()

        users = next(t for t in schema.tables if t.name == "users")
        assert users.row_count == 2

        posts = next(t for t in schema.tables if t.name == "posts")
        assert posts.row_count == 1


# ─── File Connector Tests ───


@pytest.fixture
def sample_data_dir():
    """Create a temporary directory with sample data files."""
    with tempfile.TemporaryDirectory() as dir_path:
        # Create CSV file
        csv_path = os.path.join(dir_path, "products.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "price", "in_stock"])
            writer.writerow([1, "Widget", 9.99, "true"])
            writer.writerow([2, "Gadget", 24.99, "false"])
            writer.writerow([3, "Doohickey", 4.50, "true"])

        # Create JSON file
        json_path = os.path.join(dir_path, "config.json")
        with open(json_path, "w") as f:
            json.dump(
                [
                    {"key": "api_url", "value": "https://api.example.com"},
                    {"key": "timeout", "value": 30},
                ],
                f,
            )

        # Create text file
        txt_path = os.path.join(dir_path, "readme.txt")
        with open(txt_path, "w") as f:
            f.write("This is a readme file.")

        yield dir_path


class TestFileConnector:
    def test_validate_valid_dir(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        assert connector.validate() is True

    def test_validate_missing_dir(self):
        connector = FileConnector("/nonexistent/path")
        with pytest.raises(FileNotFoundError):
            connector.validate()

    def test_inspect_csv(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        schema = connector.inspect()

        products = next(
            (t for t in schema.tables if t.name == "products"), None
        )
        assert products is not None
        assert products.row_count == 3
        col_names = [c.name for c in products.columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "price" in col_names

    def test_inspect_json(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        schema = connector.inspect()

        config = next(
            (t for t in schema.tables if t.name == "config"), None
        )
        assert config is not None
        assert config.row_count == 2

    def test_inspect_text_as_resource(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        schema = connector.inspect()

        assert len(schema.resources) >= 1
        readme = next(
            (r for r in schema.resources if r.name == "readme"), None
        )
        assert readme is not None
        assert readme.mime_type == "text/plain"


# ─── Connector Registry Tests ───


class TestConnectorRegistry:
    def test_get_connector_sqlite(self, sample_db):
        connector = get_connector(f"sqlite:///{sample_db}")
        assert isinstance(connector, SQLiteConnector)

    def test_get_connector_directory(self, sample_data_dir):
        connector = get_connector(sample_data_dir)
        assert isinstance(connector, FileConnector)

    def test_get_connector_db_file(self, sample_db):
        connector = get_connector(sample_db)
        assert isinstance(connector, SQLiteConnector)

    def test_get_connector_unknown(self):
        with pytest.raises(ValueError, match="No connector found"):
            get_connector("mongodb://localhost/test")


# ─── Code Generator Tests ───


class TestCodeGenerator:
    def test_generate_sqlite_server(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = generate_server_code(schema)

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
        code = generate_server_code(schema)

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
        code = generate_server_code(schema)

        assert 'if __name__ == "__main__":' in code
        assert "mcp.run()" in code
