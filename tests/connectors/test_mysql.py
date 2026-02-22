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
