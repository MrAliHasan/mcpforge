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
