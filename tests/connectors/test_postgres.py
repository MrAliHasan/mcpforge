
import pytest

from mcp_maker.connectors.postgres import PostgresConnector


class TestPostgresConnector:
    def test_source_type(self):
        connector = PostgresConnector("postgres://user:pass@localhost/testdb")
        assert connector.source_type == "postgres"

    def test_get_dsn_normalization(self):
        connector = PostgresConnector("postgres://user:pass@localhost/testdb")
        dsn = connector._get_dsn()
        assert dsn.startswith("postgresql://")

    def test_get_dsn_postgresql_scheme(self):
        connector = PostgresConnector("postgresql://user:pass@localhost/testdb")
        dsn = connector._get_dsn()
        assert dsn == "postgresql://user:pass@localhost/testdb"

    def test_parse_schema_default(self):
        connector = PostgresConnector("postgres://user:pass@localhost/testdb")
        assert connector._parse_schema() == "public"

    def test_parse_schema_custom(self):
        connector = PostgresConnector("postgres://user:pass@localhost/testdb?schema=myschema")
        assert connector._parse_schema() == "myschema"

    def test_validate_missing_psycopg2(self, monkeypatch):
        """Verify graceful error when psycopg2 is not installed."""
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
        assert _CONNECTOR_REGISTRY.get("postgres") == PostgresConnector
        assert _CONNECTOR_REGISTRY.get("postgresql") == PostgresConnector
