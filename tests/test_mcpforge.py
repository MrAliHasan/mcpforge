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

    def test_generate_read_only_by_default(self, sample_db):
        """Verify that by default, write tools are NOT generated."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = generate_server_code(schema)

        assert "def insert_users" not in code
        assert "def update_users" not in code
        assert "def delete_users" not in code

    def test_generate_read_write_mode(self, sample_db):
        """Verify that write tools ARE generated with read_only=False."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = generate_server_code(schema, read_only=False)

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
        code = generate_server_code(schema)

        assert "MCP-Maker" in code
        assert "mcp-maker" in code
        # Should NOT contain old branding
        assert "MCPForge" not in code
        assert "mcpforge" not in code


# ─── PostgreSQL Connector Tests ───


class TestPostgresConnector:
    def test_source_type(self):
        from mcp_maker.connectors.postgres import PostgresConnector
        connector = PostgresConnector("postgres://user:pass@localhost/testdb")
        assert connector.source_type == "postgres"

    def test_get_dsn_normalization(self):
        from mcp_maker.connectors.postgres import PostgresConnector
        connector = PostgresConnector("postgres://user:pass@localhost/testdb")
        dsn = connector._get_dsn()
        assert dsn.startswith("postgresql://")

    def test_get_dsn_postgresql_scheme(self):
        from mcp_maker.connectors.postgres import PostgresConnector
        connector = PostgresConnector("postgresql://user:pass@localhost/testdb")
        dsn = connector._get_dsn()
        assert dsn == "postgresql://user:pass@localhost/testdb"

    def test_parse_schema_default(self):
        from mcp_maker.connectors.postgres import PostgresConnector
        connector = PostgresConnector("postgres://user:pass@localhost/testdb")
        assert connector._parse_schema() == "public"

    def test_parse_schema_custom(self):
        from mcp_maker.connectors.postgres import PostgresConnector
        connector = PostgresConnector("postgres://user:pass@localhost/testdb?schema=myschema")
        assert connector._parse_schema() == "myschema"

    def test_validate_missing_psycopg2(self, monkeypatch):
        """Verify graceful error when psycopg2 is not installed."""
        from mcp_maker.connectors.postgres import PostgresConnector
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "psycopg2":
                raise ImportError("No module named 'psycopg2'")
            return real_import(name, *args, **kwargs)

        connector = PostgresConnector("postgres://user:pass@localhost/testdb")
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="psycopg2"):
            connector.validate()

    def test_registration(self):
        from mcp_maker.connectors.base import _CONNECTOR_REGISTRY
        from mcp_maker.connectors.postgres import PostgresConnector
        assert _CONNECTOR_REGISTRY.get("postgres") == PostgresConnector
        assert _CONNECTOR_REGISTRY.get("postgresql") == PostgresConnector


# ─── MySQL Connector Tests ───


class TestMySQLConnector:
    def test_source_type(self):
        from mcp_maker.connectors.mysql import MySQLConnector
        connector = MySQLConnector("mysql://user:pass@localhost:3306/testdb")
        assert connector.source_type == "mysql"

    def test_parse_uri(self):
        from mcp_maker.connectors.mysql import MySQLConnector
        connector = MySQLConnector("mysql://myuser:mypass@dbhost:3307/mydb")
        params = connector._parse_uri()
        assert params["host"] == "dbhost"
        assert params["port"] == 3307
        assert params["user"] == "myuser"
        assert params["password"] == "mypass"
        assert params["database"] == "mydb"

    def test_parse_uri_defaults(self):
        from mcp_maker.connectors.mysql import MySQLConnector
        connector = MySQLConnector("mysql:///testdb")
        params = connector._parse_uri()
        assert params["host"] == "localhost"
        assert params["port"] == 3306
        assert params["user"] == "root"
        assert params["database"] == "testdb"

    def test_validate_missing_pymysql(self, monkeypatch):
        """Verify graceful error when pymysql is not installed."""
        from mcp_maker.connectors.mysql import MySQLConnector
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pymysql":
                raise ImportError("No module named 'pymysql'")
            return real_import(name, *args, **kwargs)

        connector = MySQLConnector("mysql://user:pass@localhost/testdb")
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="pymysql"):
            connector.validate()

    def test_registration(self):
        from mcp_maker.connectors.base import _CONNECTOR_REGISTRY
        from mcp_maker.connectors.mysql import MySQLConnector
        assert _CONNECTOR_REGISTRY.get("mysql") == MySQLConnector


# ─── Config Command Tests ───


class TestConfigCommand:
    def test_claude_config_path_detection(self):
        """Verify config path detection returns a string."""
        from mcp_maker.cli import _get_claude_config_path
        path = _get_claude_config_path()
        # On macOS/Linux/Windows, should return a path
        assert path is not None
        assert "claude_desktop_config.json" in path


# ─── Airtable Connector Tests ───


class TestAirtableConnector:
    def test_source_type(self):
        from mcp_maker.connectors.airtable import AirtableConnector
        connector = AirtableConnector("airtable://appABC123")
        assert connector.source_type == "airtable"

    def test_get_base_id(self):
        from mcp_maker.connectors.airtable import AirtableConnector
        connector = AirtableConnector("airtable://appXYZ789")
        assert connector._get_base_id() == "appXYZ789"

    def test_get_api_key_missing(self, monkeypatch):
        from mcp_maker.connectors.airtable import AirtableConnector
        monkeypatch.delenv("AIRTABLE_API_KEY", raising=False)
        monkeypatch.delenv("AIRTABLE_TOKEN", raising=False)
        connector = AirtableConnector("airtable://appABC123")
        with pytest.raises(ValueError, match="AIRTABLE_API_KEY"):
            connector._get_api_key()

    def test_get_api_key_from_env(self, monkeypatch):
        from mcp_maker.connectors.airtable import AirtableConnector
        monkeypatch.setenv("AIRTABLE_API_KEY", "pat_test_token")
        connector = AirtableConnector("airtable://appABC123")
        assert connector._get_api_key() == "pat_test_token"

    def test_get_api_key_from_token_env(self, monkeypatch):
        from mcp_maker.connectors.airtable import AirtableConnector
        monkeypatch.delenv("AIRTABLE_API_KEY", raising=False)
        monkeypatch.setenv("AIRTABLE_TOKEN", "pat_fallback_token")
        connector = AirtableConnector("airtable://appABC123")
        assert connector._get_api_key() == "pat_fallback_token"

    def test_sanitize_name(self):
        from mcp_maker.connectors.airtable import _sanitize_name
        assert _sanitize_name("My Table") == "my_table"
        assert _sanitize_name("Contacts & Leads") == "contacts_leads"
        assert _sanitize_name("123_start") == "_123_start"
        assert _sanitize_name("simple") == "simple"
        assert _sanitize_name("Hello  World!!") == "hello_world"
        assert _sanitize_name("  spaces  ") == "spaces"

    def test_validate_missing_pyairtable(self, monkeypatch):
        from mcp_maker.connectors.airtable import AirtableConnector
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pyairtable":
                raise ImportError("No module named 'pyairtable'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setenv("AIRTABLE_API_KEY", "pat_test")
        connector = AirtableConnector("airtable://appABC123")
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="pyairtable"):
            connector.validate()

    def test_registration(self):
        from mcp_maker.connectors.base import _CONNECTOR_REGISTRY
        from mcp_maker.connectors.airtable import AirtableConnector
        assert _CONNECTOR_REGISTRY.get("airtable") == AirtableConnector

    def test_airtable_type_mapping(self):
        from mcp_maker.connectors.airtable import AIRTABLE_TYPE_MAP
        from mcp_maker.core.schema import ColumnType
        assert AIRTABLE_TYPE_MAP["singleLineText"] == ColumnType.STRING
        assert AIRTABLE_TYPE_MAP["number"] == ColumnType.FLOAT
        assert AIRTABLE_TYPE_MAP["checkbox"] == ColumnType.BOOLEAN
        assert AIRTABLE_TYPE_MAP["dateTime"] == ColumnType.DATETIME
        assert AIRTABLE_TYPE_MAP["multipleSelects"] == ColumnType.JSON
        assert AIRTABLE_TYPE_MAP["multipleAttachments"] == ColumnType.JSON
        assert AIRTABLE_TYPE_MAP["createdBy"] == ColumnType.JSON

    def test_airtable_type_map_completeness(self):
        """Verify all common Airtable types are mapped."""
        from mcp_maker.connectors.airtable import AIRTABLE_TYPE_MAP
        essential_types = [
            "singleLineText", "multilineText", "email", "url",
            "number", "currency", "percent", "rating",
            "checkbox", "date", "dateTime",
            "singleSelect", "multipleSelects",
            "multipleRecordLinks", "multipleAttachments",
            "formula", "rollup", "lookup",
        ]
        for t in essential_types:
            assert t in AIRTABLE_TYPE_MAP, f"Missing type: {t}"


# ─── Google Sheets Connector Tests ───


class TestGoogleSheetsConnector:
    def test_source_type(self):
        from mcp_maker.connectors.gsheets import GoogleSheetsConnector
        connector = GoogleSheetsConnector("gsheet://abc123def")
        assert connector.source_type == "gsheet"

    def test_get_spreadsheet_id_from_uri(self):
        from mcp_maker.connectors.gsheets import GoogleSheetsConnector
        connector = GoogleSheetsConnector("gsheet://1BxiMVs0XRA5nFMdKvBdBZji")
        assert connector._get_spreadsheet_id() == "1BxiMVs0XRA5nFMdKvBdBZji"

    def test_get_spreadsheet_id_from_url(self):
        from mcp_maker.connectors.gsheets import GoogleSheetsConnector
        url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5/edit"
        connector = GoogleSheetsConnector(url)
        assert connector._get_spreadsheet_id() == "1BxiMVs0XRA5"

    def test_validate_missing_gspread(self, monkeypatch):
        from mcp_maker.connectors.gsheets import GoogleSheetsConnector
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "gspread":
                raise ImportError("No module named 'gspread'")
            return real_import(name, *args, **kwargs)

        connector = GoogleSheetsConnector("gsheet://abc123")
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="gspread"):
            connector.validate()

    def test_sanitize_name(self):
        from mcp_maker.connectors.gsheets import _sanitize_name
        assert _sanitize_name("Sheet 1") == "sheet_1"
        assert _sanitize_name("My Data!") == "my_data"
        assert _sanitize_name("2024 Q1 Revenue") == "_2024_q1_revenue"

    def test_infer_type(self):
        from mcp_maker.connectors.gsheets import _infer_type
        from mcp_maker.core.schema import ColumnType
        assert _infer_type(["hello", "world"]) == ColumnType.STRING
        assert _infer_type([1, 2, 3]) == ColumnType.INTEGER
        assert _infer_type([1.5, 2.3]) == ColumnType.FLOAT
        assert _infer_type(["true", "false"]) == ColumnType.BOOLEAN
        assert _infer_type([]) == ColumnType.STRING

    def test_registration(self):
        from mcp_maker.connectors.base import _CONNECTOR_REGISTRY
        from mcp_maker.connectors.gsheets import GoogleSheetsConnector
        assert _CONNECTOR_REGISTRY.get("gsheet") == GoogleSheetsConnector


# ─── Notion Connector Tests ───


class TestNotionConnector:
    def test_source_type(self):
        from mcp_maker.connectors.notion import NotionConnector
        connector = NotionConnector("notion://abc123def456")
        assert connector.source_type == "notion"

    def test_get_database_ids(self):
        from mcp_maker.connectors.notion import NotionConnector
        connector = NotionConnector("notion://abc123")
        assert connector._get_database_ids() == ["abc123"]

    def test_get_multiple_database_ids(self):
        from mcp_maker.connectors.notion import NotionConnector
        connector = NotionConnector("notion://abc123,def456")
        ids = connector._get_database_ids()
        assert len(ids) == 2
        assert "abc123" in ids
        assert "def456" in ids

    def test_get_api_key_missing(self, monkeypatch):
        from mcp_maker.connectors.notion import NotionConnector
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        connector = NotionConnector("notion://abc123")
        with pytest.raises(ValueError, match="NOTION_API_KEY"):
            connector._get_api_key()

    def test_get_api_key_from_env(self, monkeypatch):
        from mcp_maker.connectors.notion import NotionConnector
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_token")
        connector = NotionConnector("notion://abc123")
        assert connector._get_api_key() == "ntn_test_token"

    def test_validate_missing_notion_client(self, monkeypatch):
        from mcp_maker.connectors.notion import NotionConnector
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "notion_client":
                raise ImportError("No module named 'notion_client'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setenv("NOTION_API_KEY", "ntn_test")
        connector = NotionConnector("notion://abc123")
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="notion-client"):
            connector.validate()

    def test_notion_type_mapping(self):
        from mcp_maker.connectors.notion import NOTION_TYPE_MAP
        from mcp_maker.core.schema import ColumnType
        assert NOTION_TYPE_MAP["title"] == ColumnType.STRING
        assert NOTION_TYPE_MAP["number"] == ColumnType.FLOAT
        assert NOTION_TYPE_MAP["checkbox"] == ColumnType.BOOLEAN
        assert NOTION_TYPE_MAP["date"] == ColumnType.DATETIME
        assert NOTION_TYPE_MAP["multi_select"] == ColumnType.JSON
        assert NOTION_TYPE_MAP["select"] == ColumnType.STRING
        assert NOTION_TYPE_MAP["relation"] == ColumnType.JSON

    def test_sanitize_name(self):
        from mcp_maker.connectors.notion import _sanitize_name
        assert _sanitize_name("Task Name") == "task_name"
        assert _sanitize_name("Status (Current)") == "status_current"
        assert _sanitize_name("123 Items") == "_123_items"

    def test_extract_property_title(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {"type": "title", "title": [{"plain_text": "Hello"}]}
        assert _extract_property_value(prop) == "Hello"

    def test_extract_property_number(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {"type": "number", "number": 42}
        assert _extract_property_value(prop) == 42

    def test_extract_property_checkbox(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {"type": "checkbox", "checkbox": True}
        assert _extract_property_value(prop) is True

    def test_extract_property_select(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {"type": "select", "select": {"name": "Active"}}
        assert _extract_property_value(prop) == "Active"

    def test_extract_property_multi_select(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {
            "type": "multi_select",
            "multi_select": [{"name": "A"}, {"name": "B"}],
        }
        assert _extract_property_value(prop) == ["A", "B"]

    def test_registration(self):
        from mcp_maker.connectors.base import _CONNECTOR_REGISTRY
        from mcp_maker.connectors.notion import NotionConnector
        assert _CONNECTOR_REGISTRY.get("notion") == NotionConnector


# ─── Schema Filtering Tests ───


class TestSchemaFiltering:
    def test_filter_tables_by_name(self):
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="test",
            tables=[
                Table(name="users", columns=[Column(name="id", type=ColumnType.INTEGER)]),
                Table(name="orders", columns=[Column(name="id", type=ColumnType.INTEGER)]),
                Table(name="products", columns=[Column(name="id", type=ColumnType.INTEGER)]),
                Table(name="reviews", columns=[Column(name="id", type=ColumnType.INTEGER)]),
            ]
        )

        # Simulate --tables filtering
        wanted = {"users", "orders"}
        schema.tables = [t for t in schema.tables if t.name.lower() in wanted]

        assert len(schema.tables) == 2
        assert schema.tables[0].name == "users"
        assert schema.tables[1].name == "orders"

    def test_filter_tables_case_insensitive(self):
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="test",
            tables=[
                Table(name="Users", columns=[Column(name="id", type=ColumnType.INTEGER)]),
                Table(name="ORDERS", columns=[Column(name="id", type=ColumnType.INTEGER)]),
            ]
        )

        wanted = {t.strip().lower() for t in "users,orders".split(",")}
        schema.tables = [t for t in schema.tables if t.name.lower() in wanted]
        assert len(schema.tables) == 2


# ─── Env Command Tests ───


class TestEnvCommand:
    def test_env_read_write(self, tmp_path):
        from mcp_maker.cli import _env_read, _env_write

        env_file = str(tmp_path / ".env")
        env_vars = {"KEY1": "value1", "KEY2": "value2"}
        _env_write(env_file, env_vars)

        result = _env_read(env_file)
        assert result["KEY1"] == "value1"
        assert result["KEY2"] == "value2"

    def test_env_read_nonexistent(self, tmp_path):
        from mcp_maker.cli import _env_read

        result = _env_read(str(tmp_path / "nope.env"))
        assert result == {}

    def test_env_read_with_quotes(self, tmp_path):
        from mcp_maker.cli import _env_read

        env_file = str(tmp_path / ".env")
        with open(env_file, "w") as f:
            f.write('KEY1="quoted value"\n')
            f.write("KEY2='single quoted'\n")
            f.write("# comment line\n")
            f.write("KEY3=plain\n")

        result = _env_read(env_file)
        assert result["KEY1"] == "quoted value"
        assert result["KEY2"] == "single quoted"
        assert result["KEY3"] == "plain"

    def test_mask_value(self):
        from mcp_maker.cli import _mask_value

        assert _mask_value("short") == "****"
        assert _mask_value("pat_xxxxxxxxxxxxxxxxxxxx") == "pat_xx...xxxx"
        assert "..." in _mask_value("ntn_xxxxxxxxxxxx")

    def test_env_set_and_delete(self, tmp_path):
        from mcp_maker.cli import _env_read, _env_set, _env_delete

        env_file = str(tmp_path / ".env")
        _env_set(env_file, "TEST_KEY", "test_value")

        result = _env_read(env_file)
        assert result["TEST_KEY"] == "test_value"

        _env_delete(env_file, "TEST_KEY")
        result = _env_read(env_file)
        assert "TEST_KEY" not in result


# ─── Semantic Search Tests ───


class TestSemanticSearch:
    def test_generator_accepts_semantic_flag(self):
        from mcp_maker.core.generator import generate_server_code
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(
                    name="contacts",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="name", type=ColumnType.STRING),
                    ],
                    row_count=5,
                )
            ],
        )

        # Without semantic — should NOT contain chromadb
        code = generate_server_code(schema, read_only=True, semantic=False)
        assert "chromadb" not in code
        assert "def semantic_search" not in code

        # With semantic — should contain chromadb and semantic tools
        code = generate_server_code(schema, read_only=True, semantic=True)
        assert "import chromadb" in code
        assert "semantic_search_contacts" in code
        assert "rebuild_index_contacts" in code
        assert "similarity_score" in code

    def test_semantic_generates_per_table(self):
        from mcp_maker.core.generator import generate_server_code
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(name="users", columns=[Column(name="id", type=ColumnType.INTEGER)]),
                Table(name="orders", columns=[Column(name="id", type=ColumnType.INTEGER)]),
            ],
        )

        code = generate_server_code(schema, semantic=True)
        assert "semantic_search_users" in code
        assert "semantic_search_orders" in code
        assert "rebuild_index_users" in code
        assert "rebuild_index_orders" in code
        assert "_build_index_users" in code
        assert "_build_index_orders" in code

    def test_semantic_with_read_write(self):
        from mcp_maker.core.generator import generate_server_code
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(
                    name="contacts",
                    columns=[Column(name="id", type=ColumnType.INTEGER, primary_key=True)],
                )
            ],
        )

        # Both flags together
        code = generate_server_code(schema, read_only=False, semantic=True)
        assert "semantic_search_contacts" in code
        assert "insert_contacts" in code  # write tools
        assert "import chromadb" in code

    def test_semantic_not_in_default(self):
        from mcp_maker.core.generator import generate_server_code
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(name="contacts", columns=[Column(name="id", type=ColumnType.INTEGER)]),
            ],
        )

        # Default — no semantic
        code = generate_server_code(schema)
        assert "chromadb" not in code
