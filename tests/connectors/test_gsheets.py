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
