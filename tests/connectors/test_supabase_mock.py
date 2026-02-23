"""Mock-based tests for Supabase connector — no live project needed."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcp_maker.connectors.supabase import SupabaseConnector
from mcp_maker.core.schema import ColumnType


class TestSupabaseConnector:
    def test_source_type(self):
        c = SupabaseConnector("supabase://myproject")
        assert c.source_type == "supabase"

    def test_get_config_from_uri(self):
        with patch.dict(os.environ, {"SUPABASE_KEY": "test-key"}, clear=False):
            os.environ.pop("SUPABASE_URL", None)
            c = SupabaseConnector("supabase://myref")
            url, key = c._get_config()
            assert url == "https://myref.supabase.co"
            assert key == "test-key"

    def test_get_config_from_env(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "https://custom.supabase.co", "SUPABASE_KEY": "anon-key"}, clear=False):
            c = SupabaseConnector("supabase://ignored")
            url, key = c._get_config()
            assert url == "https://custom.supabase.co"
            assert key == "anon-key"

    def test_get_config_missing_key(self):
        with patch.dict(os.environ, {"SUPABASE_URL": "https://x.supabase.co"}, clear=False):
            os.environ.pop("SUPABASE_KEY", None)
            os.environ.pop("SUPABASE_ANON_KEY", None)
            c = SupabaseConnector("supabase://x")
            with pytest.raises(ValueError, match="SUPABASE_KEY"):
                c._get_config()

    def test_get_config_missing_url(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SUPABASE_URL", None)
            os.environ.pop("SUPABASE_KEY", None)
            os.environ.pop("SUPABASE_ANON_KEY", None)
            c = SupabaseConnector("supabase://")
            with pytest.raises(ValueError, match="SUPABASE_URL"):
                c._get_config()

    def test_inspect(self):
        mock_httpx = MagicMock()

        # Mock OpenAPI response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "definitions": {
                "users": {
                    "properties": {
                        "id": {"format": "bigint", "type": "integer", "description": "primary key"},
                        "name": {"format": "text", "type": "string"},
                        "active": {"format": "boolean", "type": "boolean"},
                        "created_at": {"format": "timestamp with time zone", "type": "string"},
                        "score": {"format": "double precision", "type": "number"},
                        "meta": {"format": "jsonb", "type": "object"},
                        "birthday": {"format": "date", "type": "string"},
                    },
                    "required": ["id", "name"],
                }
            }
        }

        # Mock count response
        mock_count = MagicMock()
        mock_count.headers = {"Content-Range": "0-0/42"}
        mock_httpx.get.side_effect = [mock_resp, mock_count]

        with patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"}, clear=False):
            with patch.dict(sys.modules, {"httpx": mock_httpx}):
                c = SupabaseConnector("supabase://test")
                schema = c.inspect()

                assert schema.source_type == "supabase"
                assert len(schema.tables) == 1
                t = schema.tables[0]
                assert t.name == "users"
                assert t.row_count == 42

                col_types = {c.name: c.type for c in t.columns}
                assert col_types["id"] == ColumnType.INTEGER
                assert col_types["active"] == ColumnType.BOOLEAN
                assert col_types["created_at"] == ColumnType.DATETIME
                assert col_types["score"] == ColumnType.FLOAT
                assert col_types["meta"] == ColumnType.JSON
                assert col_types["birthday"] == ColumnType.DATE

    def test_inspect_api_error(self):
        mock_httpx = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_httpx.get.return_value = mock_resp

        with patch.dict(os.environ, {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_KEY": "test-key"}, clear=False):
            with patch.dict(sys.modules, {"httpx": mock_httpx}):
                c = SupabaseConnector("supabase://test")
                with pytest.raises(ConnectionError, match="Cannot reach"):
                    c.inspect()

    def test_registration(self):
        from mcp_maker.connectors.base import get_connector
        c = get_connector("supabase://myref")
        assert isinstance(c, SupabaseConnector)
