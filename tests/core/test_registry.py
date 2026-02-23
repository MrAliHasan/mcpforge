
import pytest

from mcp_maker.connectors.base import get_connector
from mcp_maker.connectors.sqlite import SQLiteConnector
from mcp_maker.connectors.files import FileConnector


class TestConnectorRegistry:
    def test_get_connector_sqlite(self, sample_db):
        connector = get_connector(f"sqlite:///{sample_db}")
        assert isinstance(connector, SQLiteConnector)

    def test_get_connector_directory(self, sample_data_dir):
        connector = get_connector(sample_data_dir)
        assert isinstance(connector, FileConnector)

    def test_get_connector_db_file(self, sample_db):
        connector = get_connector(sample_db)
        assert isinstance(connector, SQLiteConnector)

    def test_get_connector_unknown(self):
        with pytest.raises(ValueError, match="No connector found"):
            get_connector("ftp://localhost/test")
