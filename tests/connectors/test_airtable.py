
import pytest

from mcp_maker.core.schema import (
    ColumnType,
)
from mcp_maker.connectors.airtable import AirtableConnector


class TestAirtableConnector:
    def test_source_type(self):
        connector = AirtableConnector("airtable://appABC123")
        assert connector.source_type == "airtable"

    def test_get_base_id(self):
        connector = AirtableConnector("airtable://appXYZ789")
        assert connector._get_base_id() == "appXYZ789"

    def test_get_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("AIRTABLE_API_KEY", raising=False)
        monkeypatch.delenv("AIRTABLE_TOKEN", raising=False)
        connector = AirtableConnector("airtable://appABC123")
        with pytest.raises(ValueError, match="AIRTABLE_API_KEY"):
            connector._get_api_key()

    def test_get_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("AIRTABLE_API_KEY", "pat_test_token")
        connector = AirtableConnector("airtable://appABC123")
        assert connector._get_api_key() == "pat_test_token"

    def test_get_api_key_from_token_env(self, monkeypatch):
        monkeypatch.delenv("AIRTABLE_API_KEY", raising=False)
        monkeypatch.setenv("AIRTABLE_TOKEN", "pat_fallback_token")
        connector = AirtableConnector("airtable://appABC123")
        assert connector._get_api_key() == "pat_fallback_token"

    def test_sanitize_name(self):
        from mcp_maker.connectors.airtable import _sanitize_name
        assert _sanitize_name("My Table") == "my_table"
        assert _sanitize_name("Contacts & Leads") == "contacts_leads"
        assert _sanitize_name("123_start") == "_123_start"
        assert _sanitize_name("simple") == "simple"
        assert _sanitize_name("Hello  World!!") == "hello_world"
        assert _sanitize_name("  spaces  ") == "spaces"

    def test_validate_missing_pyairtable(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pyairtable":
                raise ImportError("No module named 'pyairtable'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setenv("AIRTABLE_API_KEY", "pat_test")
        connector = AirtableConnector("airtable://appABC123")
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="pyairtable"):
            connector.validate()

    def test_registration(self):
        from mcp_maker.connectors.base import _CONNECTOR_REGISTRY
        assert _CONNECTOR_REGISTRY.get("airtable") == AirtableConnector

    def test_airtable_type_mapping(self):
        from mcp_maker.connectors.airtable import AIRTABLE_TYPE_MAP
        assert AIRTABLE_TYPE_MAP["singleLineText"] == ColumnType.STRING
        assert AIRTABLE_TYPE_MAP["number"] == ColumnType.FLOAT
        assert AIRTABLE_TYPE_MAP["checkbox"] == ColumnType.BOOLEAN
        assert AIRTABLE_TYPE_MAP["dateTime"] == ColumnType.DATETIME
        assert AIRTABLE_TYPE_MAP["multipleSelects"] == ColumnType.JSON
        assert AIRTABLE_TYPE_MAP["multipleAttachments"] == ColumnType.JSON
        assert AIRTABLE_TYPE_MAP["createdBy"] == ColumnType.JSON

    def test_airtable_type_map_completeness(self):
        """Verify all common Airtable types are mapped."""
        from mcp_maker.connectors.airtable import AIRTABLE_TYPE_MAP
        essential_types = [
            "singleLineText", "multilineText", "email", "url",
            "number", "currency", "percent", "rating",
            "checkbox", "date", "dateTime",
            "singleSelect", "multipleSelects",
            "multipleRecordLinks", "multipleAttachments",
            "formula", "rollup", "lookup",
        ]
        for t in essential_types:
            assert t in AIRTABLE_TYPE_MAP, f"Missing type: {t}"
