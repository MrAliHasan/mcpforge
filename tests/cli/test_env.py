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
