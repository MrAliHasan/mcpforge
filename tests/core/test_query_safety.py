"""Tests for SQL injection prevention and query safety in generated code.

Verifies that consolidated-mode tools whitelist both table AND column names
before interpolating them into SQL, and that batch operations filter inputs
against the known schema.
"""

import os
import tempfile

import pytest

from mcp_maker.core.schema import Column, ColumnType, DataSourceSchema, Table
from mcp_maker.connectors.sqlite import SQLiteConnector
from mcp_maker.core.generator import generate_server_code


class TestConsolidatedColumnWhitelist:
    """Generated consolidated-mode code must validate column names to prevent SQL injection."""

    def _generate_consolidated(self):
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(
                    name="users",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="name", type=ColumnType.STRING),
                        Column(name="email", type=ColumnType.STRING),
                    ],
                    row_count=100,
                ),
                Table(
                    name="orders",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="total", type=ColumnType.FLOAT),
                    ],
                    row_count=50,
                ),
            ],
        )
        _, autogen = generate_server_code(schema, consolidate_threshold=1)
        return autogen

    def test_emits_known_columns_dict(self):
        code = self._generate_consolidated()
        assert "_KNOWN_COLUMNS" in code
        assert '"users":' in code
        assert '"id"' in code
        assert '"name"' in code

    def test_emits_validate_column_function(self):
        code = self._generate_consolidated()
        assert "_validate_column" in code
        assert "def _validate_column(table: str, column: str)" in code

    def test_query_database_calls_validate_column(self):
        code = self._generate_consolidated()
        assert "_validate_column(table_name, k)" in code

    def test_insert_record_calls_validate_column(self):
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(name="items", columns=[
                    Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                    Column(name="name", type=ColumnType.STRING),
                ], row_count=10),
                Table(name="categories", columns=[
                    Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                    Column(name="label", type=ColumnType.STRING),
                ], row_count=5),
            ],
        )
        _, autogen = generate_server_code(
            schema, consolidate_threshold=1, ops=["read", "insert"]
        )
        assert "_validate_column(table_name, k)" in autogen

    def test_consolidated_code_compiles(self):
        code = self._generate_consolidated()
        compile(code, "<test>", "exec")


class TestBatchInputSanitization:
    """Batch insert/delete tools must enforce column whitelists and size limits."""

    def test_batch_insert_filters_by_valid_cols(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, ops=["read", "insert"])
        assert "and c in _valid_cols" in autogen

    def test_batch_insert_enforces_size_limit(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, ops=["read", "insert"])
        assert "_MAX_BATCH_SIZE" in autogen
        assert "exceeds maximum" in autogen

    def test_batch_delete_enforces_size_limit(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, ops=["read", "delete"])
        assert "_MAX_BATCH_SIZE" in autogen

    def test_postgres_batch_enforces_size_limit(self):
        schema = DataSourceSchema(
            source_type="postgres",
            source_uri="postgresql://user:pass@localhost/testdb",
            tables=[
                Table(name="items", columns=[
                    Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                    Column(name="name", type=ColumnType.STRING),
                ], row_count=10),
            ],
        )
        _, autogen = generate_server_code(schema, ops=["read", "insert", "delete"])
        assert "_MAX_BATCH_SIZE = 1000" in autogen
        assert "exceeds maximum" in autogen
