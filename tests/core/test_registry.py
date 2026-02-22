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
            get_connector("ftp://localhost/test")
