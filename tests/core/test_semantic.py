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
        code = generate_server_code(schema, ops=["read"], semantic=False)
        assert "chromadb" not in code
        assert "def semantic_search" not in code

        # With semantic — should contain chromadb and semantic tools
        code = generate_server_code(schema, ops=["read"], semantic=True)
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
        code = generate_server_code(schema, ops=["read", "insert", "update", "delete"], semantic=True)
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
