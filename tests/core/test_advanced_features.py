"""Tests for advanced features: FK detection, pagination, fields, date filters,
batch ops, export, webhooks, multi-source merge."""

import os
import sqlite3
import tempfile

import pytest

from mcp_maker.core.schema import Column, ColumnType, DataSourceSchema, ForeignKey, Table
from mcp_maker.connectors.sqlite import SQLiteConnector
from mcp_maker.core.generator import generate_server_code


@pytest.fixture
def fk_db():
    """SQLite DB with FK relationships and date columns."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE authors (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("""
        CREATE TABLE books (
            id INTEGER PRIMARY KEY,
            author_id INTEGER REFERENCES authors(id),
            title TEXT,
            published_date DATE
        )
    """)
    conn.execute("INSERT INTO authors VALUES (1, 'Alice')")
    conn.execute("INSERT INTO books VALUES (1, 1, 'Book One', '2024-01-15')")
    conn.execute("INSERT INTO books VALUES (2, 1, 'Book Two', '2024-06-20')")
    conn.commit()
    conn.close()
    yield db_path
    os.unlink(db_path)


class TestForeignKeyDiscovery:
    def test_sqlite_detects_fks(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        assert len(schema.foreign_keys) >= 1
        fk = schema.foreign_keys[0]
        assert fk.from_table == "books"
        assert fk.from_column == "author_id"
        assert fk.to_table == "authors"
        assert fk.to_column == "id"

    def test_fk_generates_join_tool(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        assert "join_books_with_authors" in autogen
        compile(autogen, "<test>", "exec")


class TestPaginationHelpers:
    def test_list_returns_pagination_metadata(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        # The generated list_ should return dict with results, total, etc.
        assert "\"results\":" in autogen or "'results':" in autogen
        assert "\"total\":" in autogen or "'total':" in autogen
        assert "\"has_more\":" in autogen or "'has_more':" in autogen
        assert "\"next_offset\":" in autogen or "'next_offset':" in autogen

    def test_list_has_sort_params(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        assert "sort_field" in autogen
        assert "sort_direction" in autogen


class TestColumnSelection:
    def test_list_has_fields_param(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        assert "fields: str | None = None" in autogen

    def test_fields_whitelist(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        assert "select_clause" in autogen


class TestDateRangeFilters:
    def test_date_columns_get_filters(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        # books.published_date is a DATE column
        assert "published_date_from" in autogen
        assert "published_date_to" in autogen


class TestBatchOperations:
    def test_batch_insert_generated(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, ops=["read", "insert", "delete"])
        assert "batch_insert_authors" in autogen
        assert "batch_insert_books" in autogen
        compile(autogen, "<test>", "exec")

    def test_batch_delete_generated(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, ops=["read", "insert", "delete"])
        assert "batch_delete_authors" in autogen
        assert "batch_delete_books" in autogen


class TestExportTools:
    def test_export_csv_generated(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        assert "export_authors_csv" in autogen
        assert "export_books_csv" in autogen

    def test_export_json_generated(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        assert "export_authors_json" in autogen
        assert "export_books_json" in autogen


class TestWebhookSupport:
    def test_webhooks_not_generated_by_default(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)
        assert "webhook_register" not in autogen

    def test_webhooks_generated_with_flag(self, fk_db):
        connector = SQLiteConnector(f"sqlite:///{fk_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, webhooks=True)
        assert "webhook_register" in autogen
        assert "webhook_list" in autogen
        assert "webhook_remove" in autogen
        assert "_fire_webhooks" in autogen
        compile(autogen, "<test>", "exec")


class TestMultiSourceSchema:
    def test_merge_schemas(self):
        schema1 = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///a.db",
            tables=[Table(name="users", columns=[Column(name="id", type=ColumnType.INTEGER, primary_key=True)])],
        )
        schema2 = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///b.db",
            tables=[Table(name="orders", columns=[Column(name="id", type=ColumnType.INTEGER, primary_key=True)])],
        )
        # Merge
        merged = DataSourceSchema(
            source_type=schema1.source_type,
            source_uri=f"{schema1.source_uri} + {schema2.source_uri}",
            tables=schema1.tables + schema2.tables,
        )
        assert len(merged.tables) == 2
        assert merged.tables[0].name == "users"
        assert merged.tables[1].name == "orders"

    def test_merged_generates_all_tools(self):
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="merged",
            tables=[
                Table(name="users", columns=[Column(name="id", type=ColumnType.INTEGER, primary_key=True), Column(name="name", type=ColumnType.STRING)]),
                Table(name="orders", columns=[Column(name="id", type=ColumnType.INTEGER, primary_key=True), Column(name="total", type=ColumnType.FLOAT)]),
            ],
        )
        _, autogen = generate_server_code(schema)
        assert "list_users" in autogen
        assert "list_orders" in autogen
        assert "export_users_csv" in autogen
        assert "export_orders_csv" in autogen
        compile(autogen, "<test>", "exec")


class TestForeignKeyDataclass:
    def test_fk_creation(self):
        fk = ForeignKey(from_table="books", from_column="author_id", to_table="authors", to_column="id")
        assert fk.from_table == "books"
        assert fk.to_column == "id"

    def test_fk_in_schema(self):
        fk = ForeignKey(from_table="orders", from_column="user_id", to_table="users", to_column="id")
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="test",
            tables=[],
            foreign_keys=[fk],
        )
        assert len(schema.foreign_keys) == 1
        assert schema.foreign_keys[0].from_table == "orders"
