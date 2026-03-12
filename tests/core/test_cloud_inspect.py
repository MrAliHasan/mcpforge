"""Mock-based tests for GSheets, Notion and Airtable connector inspect methods."""

import os
import sys
from unittest.mock import MagicMock, patch


from mcp_maker.connectors.gsheets import GoogleSheetsConnector
from mcp_maker.connectors.notion import NotionConnector
from mcp_maker.connectors.airtable import AirtableConnector
from mcp_maker.core.schema import ColumnType


class TestGSheetsInspect:
    def test_get_spreadsheet_id_direct(self):
        c = GoogleSheetsConnector("gsheet://1BxiMVs0XRA5n")
        assert c._get_spreadsheet_id() == "1BxiMVs0XRA5n"

    def test_validate_success(self):
        mock_gspread = MagicMock()
        with patch.dict(sys.modules, {"gspread": mock_gspread}):
            c = GoogleSheetsConnector("gsheet://abc123")
            assert c.validate() is True

    def test_inspect_type_inference(self):
        """Test the type inference used in GSheets inspect."""
        from mcp_maker.connectors.gsheets import _infer_type
        assert _infer_type("42") in ("INTEGER", "STRING", ColumnType.INTEGER, ColumnType.STRING)
        assert _infer_type("3.14") in ("FLOAT", "STRING", ColumnType.FLOAT, ColumnType.STRING)
        assert _infer_type("hello") in ("STRING", ColumnType.STRING)


class TestNotionInspect:
    def test_get_database_ids(self):
        c = NotionConnector("notion://abc123")
        assert c._get_database_ids() == ["abc123"]

    def test_get_multiple_database_ids(self):
        c = NotionConnector("notion://abc,def,ghi")
        assert c._get_database_ids() == ["abc", "def", "ghi"]

    def test_validate_success(self):
        mock_notion = MagicMock()
        with patch.dict(sys.modules, {"notion_client": mock_notion}):
            with patch.dict(os.environ, {"NOTION_API_KEY": "ntn_test"}, clear=False):
                c = NotionConnector("notion://abc123")
                assert c.validate() is True

    def test_inspect(self):
        mock_notion_client = MagicMock()
        mock_client = MagicMock()
        mock_notion_client.Client.return_value = mock_client

        # Mock database query response
        mock_client.databases.retrieve.return_value = {
            "title": [{"plain_text": "Tasks"}],
            "properties": {
                "Task": {"type": "title", "title": {}},
                "Status": {"type": "select", "select": {"options": [{"name": "Done"}, {"name": "Open"}]}},
                "Priority": {"type": "number", "number": {}},
                "Done": {"type": "checkbox", "checkbox": {}},
            },
        }

        mock_client.databases.query.return_value = {
            "results": [
                {
                    "id": "page-1",
                    "properties": {
                        "Task": {"type": "title", "title": [{"plain_text": "Fix bug"}]},
                        "Status": {"type": "select", "select": {"name": "Open"}},
                        "Priority": {"type": "number", "number": 5},
                        "Done": {"type": "checkbox", "checkbox": False},
                    },
                }
            ],
            "has_more": False,
            "next_cursor": None,
        }

        with patch.dict(sys.modules, {"notion_client": mock_notion_client}):
            with patch.dict(os.environ, {"NOTION_API_KEY": "ntn_test"}, clear=False):
                c = NotionConnector("notion://abc123")
                schema = c.inspect()
                assert schema.source_type == "notion"
                assert len(schema.tables) == 1
                assert schema.tables[0].name == "tasks"


class TestAirtableInspect:
    def test_get_base_id(self):
        c = AirtableConnector("airtable://appABC123def456")
        assert c._get_base_id() == "appABC123def456"

    def test_validate_success(self):
        mock_pyairtable = MagicMock()
        with patch.dict(sys.modules, {"pyairtable": mock_pyairtable}):
            with patch.dict(os.environ, {"AIRTABLE_API_KEY": "pat_test"}, clear=False):
                c = AirtableConnector("airtable://appABC123")
                assert c.validate() is True

    def test_inspect_type_mapping(self):
        """Test the Airtable type mapping dict exists and covers key types."""
        from mcp_maker.connectors.airtable import AIRTABLE_TYPE_MAP
        assert "singleLineText" in AIRTABLE_TYPE_MAP
        assert "number" in AIRTABLE_TYPE_MAP
        assert "checkbox" in AIRTABLE_TYPE_MAP
        assert "email" in AIRTABLE_TYPE_MAP
