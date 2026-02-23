"""Mock-based tests for Redis connector — no live server needed."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from mcp_maker.connectors.redis_connector import RedisConnector


class TestRedisConnector:
    def test_source_type(self):
        c = RedisConnector("redis://localhost:6379/0")
        assert c.source_type == "redis"

    def test_parse_uri_default(self):
        c = RedisConnector("redis://localhost:6379/0")
        params = c._parse_uri()
        assert params["host"] == "localhost"
        assert params["port"] == 6379
        assert params["db"] == 0
        assert params["ssl"] is False

    def test_parse_uri_with_auth(self):
        c = RedisConnector("redis://:mypassword@redis.example.com:6380/2")
        params = c._parse_uri()
        assert params["host"] == "redis.example.com"
        assert params["port"] == 6380
        assert params["db"] == 2
        assert params["password"] == "mypassword"

    def test_parse_uri_ssl(self):
        c = RedisConnector("rediss://host:6379/0")
        params = c._parse_uri()
        assert params["ssl"] is True

    def test_parse_uri_no_scheme(self):
        c = RedisConnector("localhost:6379")
        params = c._parse_uri()
        assert params["host"] == "localhost"

    def test_validate_success(self):
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.Redis.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis}):
            c = RedisConnector("redis://localhost:6379/0")
            assert c.validate() is True

    def test_validate_connection_error(self):
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection refused")
        mock_redis.Redis.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis}):
            c = RedisConnector("redis://localhost:6379/0")
            with pytest.raises(ConnectionError, match="Cannot connect"):
                c.validate()

    def test_inspect_string_keys(self):
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, ["cache:page1", "cache:page2"])
        mock_client.type.return_value = "string"
        mock_client.dbsize.return_value = 2
        mock_redis.Redis.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis}):
            c = RedisConnector("redis://localhost:6379/0")
            schema = c.inspect()
            assert schema.source_type == "redis"
            assert len(schema.tables) >= 1
            assert schema.metadata["db_size"] == 2

    def test_inspect_hash_keys(self):
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, ["users:1", "users:2"])
        mock_client.type.return_value = "hash"
        mock_client.hkeys.return_value = ["name", "email"]
        mock_client.dbsize.return_value = 2
        mock_redis.Redis.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis}):
            c = RedisConnector("redis://localhost:6379/0")
            schema = c.inspect()
            table = schema.tables[0]
            col_names = [col.name for col in table.columns]
            assert "key" in col_names
            assert "name" in col_names
            assert "email" in col_names

    def test_inspect_mixed_types(self):
        mock_redis = MagicMock()
        mock_client = MagicMock()
        keys = ["cache:1", "queue:jobs"]
        types_map = {"cache:1": "string", "queue:jobs": "list"}
        mock_client.scan.return_value = (0, keys)
        mock_client.type.side_effect = lambda k: types_map.get(k, "string")
        mock_client.dbsize.return_value = 2
        mock_redis.Redis.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis}):
            c = RedisConnector("redis://localhost:6379/0")
            schema = c.inspect()
            assert len(schema.tables) == 2

    def test_inspect_set_keys(self):
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, ["tags:active"])
        mock_client.type.return_value = "set"
        mock_client.dbsize.return_value = 1
        mock_redis.Redis.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis}):
            c = RedisConnector("redis://localhost:6379/0")
            schema = c.inspect()
            col_names = [c.name for c in schema.tables[0].columns]
            assert "members" in col_names
            assert "cardinality" in col_names

    def test_inspect_zset_keys(self):
        mock_redis = MagicMock()
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, ["leaderboard"])
        mock_client.type.return_value = "zset"
        mock_client.dbsize.return_value = 1
        mock_redis.Redis.return_value = mock_client

        with patch.dict(sys.modules, {"redis": mock_redis}):
            c = RedisConnector("redis://localhost:6379/0")
            schema = c.inspect()
            col_names = [c.name for c in schema.tables[0].columns]
            assert "members_with_scores" in col_names

    def test_registration(self):
        from mcp_maker.connectors.base import get_connector
        c = get_connector("redis://localhost:6379/0")
        assert isinstance(c, RedisConnector)
