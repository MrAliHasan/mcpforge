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
