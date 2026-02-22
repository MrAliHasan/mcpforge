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
