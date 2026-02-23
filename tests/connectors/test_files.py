
import pytest

from mcp_maker.connectors.files import FileConnector


class TestFileConnector:
    def test_validate_valid_dir(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        assert connector.validate() is True

    def test_validate_missing_dir(self):
        connector = FileConnector("/nonexistent/path")
        with pytest.raises(FileNotFoundError):
            connector.validate()

    def test_inspect_csv(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        schema = connector.inspect()

        products = next(
            (t for t in schema.tables if t.name == "products"), None
        )
        assert products is not None
        assert products.row_count == 3
        col_names = [c.name for c in products.columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "price" in col_names

    def test_inspect_json(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        schema = connector.inspect()

        config = next(
            (t for t in schema.tables if t.name == "config"), None
        )
        assert config is not None
        assert config.row_count == 2

    def test_inspect_text_as_resource(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        schema = connector.inspect()

        assert len(schema.resources) >= 1
        readme = next(
            (r for r in schema.resources if r.name == "readme"), None
        )
        assert readme is not None
        assert readme.mime_type == "text/plain"
