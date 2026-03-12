"""Tests for credential handling and authentication in generated servers.

Validates that generated code never embeds filesystem paths or secrets,
and that API key authentication actually validates client-provided tokens.
"""

from mcp_maker.connectors.sqlite import SQLiteConnector
from mcp_maker.core.generator import generate_server_code


class TestCredentialHardening:
    """Generated code must never embed sensitive paths or credentials."""

    def test_sqlite_no_hardcoded_path_fallback(self, sample_db):
        """Generated code should raise RuntimeError if DATABASE_URL is unset, not fall back."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)

        assert sample_db not in autogen
        assert "Using hardcoded path" not in autogen
        assert "raise RuntimeError" in autogen
        assert "DATABASE_URL environment variable is not set" in autogen


class TestApiKeyAuthentication:
    """API key auth must validate a client-provided key, not just check server config."""

    def test_generates_api_key_parameter(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, auth_mode="api-key")

        assert "api_key: str" in autogen
        assert "api_key != _MCP_API_KEY" in autogen
        assert 'raise PermissionError("Invalid API key.")' in autogen

    def test_auth_code_compiles(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, auth_mode="api-key")
        compile(autogen, "<test>", "exec")

    def test_documents_decorator_stacking_order(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema, auth_mode="api-key")
        assert "DECORATOR STACKING ORDER" in autogen
