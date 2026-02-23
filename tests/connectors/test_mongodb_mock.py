"""Mock-based tests for MongoDB connector — no live server needed."""

import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from mcp_maker.connectors.mongodb import MongoDBConnector, _python_type_to_column_type
from mcp_maker.core.schema import ColumnType


class TestMongoDBConnector:
    def test_source_type(self):
        c = MongoDBConnector("mongodb://localhost:27017/testdb")
        assert c.source_type == "mongodb"

    def test_get_database_name(self):
        c = MongoDBConnector("mongodb://localhost:27017/mydb")
        assert c._get_database_name() == "mydb"

    def test_get_database_name_missing(self):
        c = MongoDBConnector("mongodb://localhost:27017")
        with pytest.raises(ValueError, match="must include a database name"):
            c._get_database_name()

    def test_get_database_name_with_auth(self):
        c = MongoDBConnector("mongodb://user:pass@host:27017/proddb")
        assert c._get_database_name() == "proddb"

    def test_validate_success(self):
        mock_pymongo = MagicMock()
        mock_client = MagicMock()
        mock_client.server_info.return_value = {"version": "7.0"}
        mock_pymongo.MongoClient.return_value = mock_client

        with patch.dict(sys.modules, {"pymongo": mock_pymongo}):
            c = MongoDBConnector("mongodb://localhost:27017/testdb")
            assert c.validate() is True
            mock_client.close.assert_called_once()

    def test_validate_connection_error(self):
        mock_pymongo = MagicMock()
        mock_client = MagicMock()
        mock_client.server_info.side_effect = Exception("Connection refused")
        mock_pymongo.MongoClient.return_value = mock_client

        with patch.dict(sys.modules, {"pymongo": mock_pymongo}):
            c = MongoDBConnector("mongodb://localhost:27017/testdb")
            with pytest.raises(ConnectionError, match="Cannot connect"):
                c.validate()

    def test_inspect(self):
        mock_pymongo = MagicMock()
        mock_collection = MagicMock()
        mock_collection.estimated_document_count.return_value = 5
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = [
            {"_id": "abc", "name": "Alice", "age": 30},
            {"_id": "def", "name": "Bob", "active": True},
        ]
        mock_collection.find.return_value = mock_cursor

        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["users"]
        mock_db.__getitem__ = lambda self, key: mock_collection

        mock_client = MagicMock()
        mock_client.__getitem__ = lambda self, key: mock_db
        mock_pymongo.MongoClient.return_value = mock_client

        with patch.dict(sys.modules, {"pymongo": mock_pymongo}):
            c = MongoDBConnector("mongodb://localhost:27017/testdb")
            schema = c.inspect()
            assert schema.source_type == "mongodb"
            assert len(schema.tables) == 1
            assert schema.tables[0].name == "users"
            assert schema.metadata["database"] == "testdb"

    def test_inspect_skips_system_collections(self):
        mock_pymongo = MagicMock()
        mock_db = MagicMock()
        mock_db.list_collection_names.return_value = ["system.indexes", "users"]
        mock_coll = MagicMock()
        mock_coll.estimated_document_count.return_value = 0
        mock_coll.find.return_value.limit.return_value = []
        mock_db.__getitem__ = lambda self, key: mock_coll

        mock_client = MagicMock()
        mock_client.__getitem__ = lambda self, key: mock_db
        mock_pymongo.MongoClient.return_value = mock_client

        with patch.dict(sys.modules, {"pymongo": mock_pymongo}):
            c = MongoDBConnector("mongodb://localhost:27017/testdb")
            schema = c.inspect()
            table_names = [t.name for t in schema.tables]
            assert "system.indexes" not in table_names


class TestPythonTypeToColumnType:
    def test_str(self):
        assert _python_type_to_column_type("hello") == ColumnType.STRING

    def test_int(self):
        assert _python_type_to_column_type(42) == ColumnType.INTEGER

    def test_float(self):
        assert _python_type_to_column_type(3.14) == ColumnType.FLOAT

    def test_bool(self):
        assert _python_type_to_column_type(True) == ColumnType.BOOLEAN

    def test_datetime(self):
        assert _python_type_to_column_type(datetime.now()) == ColumnType.DATETIME

    def test_list(self):
        assert _python_type_to_column_type([1, 2]) == ColumnType.JSON

    def test_dict(self):
        assert _python_type_to_column_type({"a": 1}) == ColumnType.JSON

    def test_none(self):
        assert _python_type_to_column_type(None) == ColumnType.UNKNOWN
