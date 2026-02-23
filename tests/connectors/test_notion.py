
import pytest

from mcp_maker.core.schema import (
    ColumnType,
)
from mcp_maker.connectors.notion import NotionConnector


class TestNotionConnector:
    def test_source_type(self):
        connector = NotionConnector("notion://abc123def456")
        assert connector.source_type == "notion"

    def test_get_database_ids(self):
        connector = NotionConnector("notion://abc123")
        assert connector._get_database_ids() == ["abc123"]

    def test_get_multiple_database_ids(self):
        connector = NotionConnector("notion://abc123,def456")
        ids = connector._get_database_ids()
        assert len(ids) == 2
        assert "abc123" in ids
        assert "def456" in ids

    def test_get_api_key_missing(self, monkeypatch):
        monkeypatch.delenv("NOTION_API_KEY", raising=False)
        monkeypatch.delenv("NOTION_TOKEN", raising=False)
        connector = NotionConnector("notion://abc123")
        with pytest.raises(ValueError, match="NOTION_API_KEY"):
            connector._get_api_key()

    def test_get_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("NOTION_API_KEY", "ntn_test_token")
        connector = NotionConnector("notion://abc123")
        assert connector._get_api_key() == "ntn_test_token"

    def test_validate_missing_notion_client(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "notion_client":
                raise ImportError("No module named 'notion_client'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setenv("NOTION_API_KEY", "ntn_test")
        connector = NotionConnector("notion://abc123")
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="notion-client"):
            connector.validate()

    def test_notion_type_mapping(self):
        from mcp_maker.connectors.notion import NOTION_TYPE_MAP
        assert NOTION_TYPE_MAP["title"] == ColumnType.STRING
        assert NOTION_TYPE_MAP["number"] == ColumnType.FLOAT
        assert NOTION_TYPE_MAP["checkbox"] == ColumnType.BOOLEAN
        assert NOTION_TYPE_MAP["date"] == ColumnType.DATETIME
        assert NOTION_TYPE_MAP["multi_select"] == ColumnType.JSON
        assert NOTION_TYPE_MAP["select"] == ColumnType.STRING
        assert NOTION_TYPE_MAP["relation"] == ColumnType.JSON

    def test_sanitize_name(self):
        from mcp_maker.connectors.notion import _sanitize_name
        assert _sanitize_name("Task Name") == "task_name"
        assert _sanitize_name("Status (Current)") == "status_current"
        assert _sanitize_name("123 Items") == "_123_items"

    def test_extract_property_title(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {"type": "title", "title": [{"plain_text": "Hello"}]}
        assert _extract_property_value(prop) == "Hello"

    def test_extract_property_number(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {"type": "number", "number": 42}
        assert _extract_property_value(prop) == 42

    def test_extract_property_checkbox(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {"type": "checkbox", "checkbox": True}
        assert _extract_property_value(prop) is True

    def test_extract_property_select(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {"type": "select", "select": {"name": "Active"}}
        assert _extract_property_value(prop) == "Active"

    def test_extract_property_multi_select(self):
        from mcp_maker.connectors.notion import _extract_property_value
        prop = {
            "type": "multi_select",
            "multi_select": [{"name": "A"}, {"name": "B"}],
        }
        assert _extract_property_value(prop) == ["A", "B"]

    def test_registration(self):
        from mcp_maker.connectors.base import _CONNECTOR_REGISTRY
        assert _CONNECTOR_REGISTRY.get("notion") == NotionConnector
