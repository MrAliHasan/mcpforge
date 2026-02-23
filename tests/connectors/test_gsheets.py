
import pytest

from mcp_maker.core.schema import (
    ColumnType,
)
from mcp_maker.connectors.gsheets import GoogleSheetsConnector


class TestGoogleSheetsConnector:
    def test_source_type(self):
        connector = GoogleSheetsConnector("gsheet://abc123def")
        assert connector.source_type == "gsheet"

    def test_get_spreadsheet_id_from_uri(self):
        connector = GoogleSheetsConnector("gsheet://1BxiMVs0XRA5nFMdKvBdBZji")
        assert connector._get_spreadsheet_id() == "1BxiMVs0XRA5nFMdKvBdBZji"

    def test_get_spreadsheet_id_from_url(self):
        url = "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5/edit"
        connector = GoogleSheetsConnector(url)
        assert connector._get_spreadsheet_id() == "1BxiMVs0XRA5"

    def test_validate_missing_gspread(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "gspread":
                raise ImportError("No module named 'gspread'")
            return real_import(name, *args, **kwargs)

        connector = GoogleSheetsConnector("gsheet://abc123")
        monkeypatch.setattr(builtins, "__import__", mock_import)
        with pytest.raises(ImportError, match="gspread"):
            connector.validate()

    def test_sanitize_name(self):
        from mcp_maker.connectors.gsheets import _sanitize_name
        assert _sanitize_name("Sheet 1") == "sheet_1"
        assert _sanitize_name("My Data!") == "my_data"
        assert _sanitize_name("2024 Q1 Revenue") == "_2024_q1_revenue"

    def test_infer_type(self):
        from mcp_maker.connectors.gsheets import _infer_type
        assert _infer_type(["hello", "world"]) == ColumnType.STRING
        assert _infer_type([1, 2, 3]) == ColumnType.INTEGER
        assert _infer_type([1.5, 2.3]) == ColumnType.FLOAT
        assert _infer_type(["true", "false"]) == ColumnType.BOOLEAN
        assert _infer_type([]) == ColumnType.STRING

    def test_registration(self):
        from mcp_maker.connectors.base import _CONNECTOR_REGISTRY
        assert _CONNECTOR_REGISTRY.get("gsheet") == GoogleSheetsConnector
