"""Tests for connector registration and environment parsing utilities."""

import os
import tempfile

from mcp_maker.core.schema import Column, ColumnType, DataSourceSchema, Table
from mcp_maker.core.generator import generate_server_code


class TestConnectorRegistration:
    """All optional connectors should be importable from the connectors package."""

    def test_base_connectors_always_available(self):
        from mcp_maker.connectors import BaseConnector, SQLiteConnector, FileConnector
        assert BaseConnector is not None
        assert SQLiteConnector is not None
        assert FileConnector is not None

    def test_all_list_exports_base_classes(self):
        from mcp_maker import connectors
        assert "BaseConnector" in connectors.__all__
        assert "SQLiteConnector" in connectors.__all__
        assert "FileConnector" in connectors.__all__


class TestHubSpotUriSanitization:
    """HubSpot connector must never leak API tokens in error messages."""

    def test_redacts_pat_token(self):
        from mcp_maker.connectors.hubspot import HubSpotConnector
        connector = HubSpotConnector("hubspot://pat=secret-token-12345")
        sanitized = connector._sanitize_uri()
        assert "secret-token-12345" not in sanitized
        assert "REDACTED" in sanitized

    def test_redacts_query_params(self):
        from mcp_maker.connectors.hubspot import HubSpotConnector
        connector = HubSpotConnector("hubspot://host?pat=secret")
        sanitized = connector._sanitize_uri()
        assert "secret" not in sanitized


class TestEnvFileParser:
    """The .env parser must handle real-world .env file patterns."""

    def test_handles_export_prefix(self):
        from mcp_maker.cli.environment import _env_read
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("export API_KEY=abc123\n")
            f.write("NORMAL_KEY=value\n")
            env_file = f.name
        try:
            result = _env_read(env_file)
            assert result["API_KEY"] == "abc123"
            assert result["NORMAL_KEY"] == "value"
        finally:
            os.unlink(env_file)

    def test_strips_inline_comments(self):
        from mcp_maker.cli.environment import _env_read
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("DB_HOST=localhost # this is a comment\n")
            f.write('QUOTED="has # in it"\n')
            env_file = f.name
        try:
            result = _env_read(env_file)
            assert result["DB_HOST"] == "localhost"
            assert result["QUOTED"] == "has # in it"
        finally:
            os.unlink(env_file)


class TestMixedSourceMerge:
    """Multi-source schema merge should produce valid generated code."""

    def test_merged_schema_generates_all_tools(self):
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="merged",
            tables=[
                Table(name="sql_users", columns=[
                    Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                    Column(name="name", type=ColumnType.STRING),
                ]),
                Table(name="api_items", columns=[
                    Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                    Column(name="title", type=ColumnType.STRING),
                ]),
            ],
        )
        _, autogen = generate_server_code(schema)
        assert "list_sql_users" in autogen
        assert "list_api_items" in autogen
        compile(autogen, "<test>", "exec")
