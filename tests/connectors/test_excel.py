"""Tests for the Excel connector with mocked openpyxl."""

import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from mcp_maker.connectors.excel import ExcelConnector, _infer_column_type
from mcp_maker.core.schema import ColumnType


class TestExcelConnector:
    def test_source_type(self):
        c = ExcelConnector("excel:///test.xlsx")
        assert c.source_type == "excel"

    def test_get_file_path_with_scheme(self):
        c = ExcelConnector("excel:///path/to/data.xlsx")
        # excel:/// strips to path/to/data.xlsx (no leading /)
        assert c._get_file_path() == "path/to/data.xlsx"

    def test_get_file_path_without_scheme(self):
        c = ExcelConnector("./data.xlsx")
        assert c._get_file_path() == "./data.xlsx"

    def test_get_file_path_double_slash(self):
        c = ExcelConnector("excel://relative.xlsx")
        assert c._get_file_path() == "relative.xlsx"

    def test_validate_missing_file(self):
        """Even with openpyxl mocked, should fail on missing file."""
        mock_openpyxl = MagicMock()
        with patch.dict(sys.modules, {"openpyxl": mock_openpyxl}):
            c = ExcelConnector("excel:///nonexistent.xlsx")
            with pytest.raises(FileNotFoundError, match="not found"):
                c.validate()

    def test_validate_wrong_extension(self):
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            path = f.name
        try:
            mock_openpyxl = MagicMock()
            with patch.dict(sys.modules, {"openpyxl": mock_openpyxl}):
                c = ExcelConnector(path)
                with pytest.raises(ValueError, match="Unsupported file format"):
                    c.validate()
        finally:
            os.unlink(path)

    def test_validate_success(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            mock_openpyxl = MagicMock()
            with patch.dict(sys.modules, {"openpyxl": mock_openpyxl}):
                c = ExcelConnector(path)
                assert c.validate() is True
        finally:
            os.unlink(path)

    def test_inspect_returns_schema(self):
        # Create mock workbook
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = [
            ("id", "name", "price"),
            (1, "Widget", 9.99),
            (2, "Gadget", 24.99),
        ]
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Products"]
        mock_wb.__getitem__ = lambda self, key: mock_ws
        mock_wb.close = MagicMock()

        mock_openpyxl = MagicMock()
        mock_openpyxl.load_workbook.return_value = mock_wb

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            with patch.dict(sys.modules, {"openpyxl": mock_openpyxl}):
                c = ExcelConnector(path)
                schema = c.inspect()
                assert schema.source_type == "excel"
                assert len(schema.tables) == 1
                assert schema.tables[0].name == "products"
                assert len(schema.tables[0].columns) == 3
                assert schema.metadata["sheet_count"] == 1
        finally:
            os.unlink(path)

    def test_inspect_skips_empty_sheets(self):
        mock_ws = MagicMock()
        mock_ws.iter_rows.return_value = []  # Empty sheet
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Empty"]
        mock_wb.__getitem__ = lambda self, key: mock_ws
        mock_wb.close = MagicMock()

        mock_openpyxl = MagicMock()
        mock_openpyxl.load_workbook.return_value = mock_wb

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            path = f.name
        try:
            with patch.dict(sys.modules, {"openpyxl": mock_openpyxl}):
                c = ExcelConnector(path)
                schema = c.inspect()
                assert len(schema.tables) == 0
        finally:
            os.unlink(path)


class TestInferColumnType:
    def test_infer_integer(self):
        assert _infer_column_type([1, 2, 3]) == ColumnType.INTEGER

    def test_infer_float(self):
        assert _infer_column_type([1.1, 2.2, 3.3]) == ColumnType.FLOAT

    def test_infer_bool(self):
        assert _infer_column_type([True, False, True]) == ColumnType.BOOLEAN

    def test_infer_string(self):
        assert _infer_column_type(["a", "b", "c"]) == ColumnType.STRING

    def test_infer_empty(self):
        assert _infer_column_type([None, None]) == ColumnType.STRING

    def test_infer_mixed_defaults_to_dominant(self):
        assert _infer_column_type([1, 2, 3, "x"]) == ColumnType.INTEGER
