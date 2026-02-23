import os
from unittest.mock import patch
import pytest

# Skip this entire test module if requests is not installed
pytest.importorskip("requests")

from mcp_maker.connectors.hubspot import HubSpotConnector
from mcp_maker.core.schema import ColumnType

class TestHubSpotMock:
    @patch("requests.get")
    def test_inspect_schema_extraction(self, mock_get):
        # Mock responses
        def mock_hubspot_api(*args, **kwargs):
            url = args[0]
            class MockResponse:
                def __init__(self, json_data, status_code=200):
                    self.json_data = json_data
                    self.status_code = status_code
                def json(self): return self.json_data
                def raise_for_status(self): pass

            if "/properties/contacts" in url:
                return MockResponse({
                    "results": [
                        {"name": "email", "label": "Email", "type": "string", "hasUniqueValue": True},
                        {"name": "lifecyclestage", "label": "Lifecycle Stage", "type": "enumeration", "options": [{"label": "Lead", "hidden": False}]}
                    ]
                })
            elif "/properties/" in url:
                return MockResponse({"results": []})
            return MockResponse({"results": []})
            
        mock_get.side_effect = mock_hubspot_api
        
        # Test inspection
        with patch.dict(os.environ, {"HUBSPOT_ACCESS_TOKEN": "test_token"}):
            conn = HubSpotConnector(uri="hubspot://")
            schema = conn.inspect()
            
            assert schema.source_type == "hubspot"
            assert len(schema.tables) == 11
            
            contacts_table = next(t for t in schema.tables if t.name == "contacts")
            assert len(contacts_table.columns) == 2
            
            email_col = next(c for c in contacts_table.columns if c.name == "email")
            assert email_col.type == ColumnType.STRING
            assert email_col.primary_key is True
            assert email_col.description == "Email"

            lifecycle_col = next(c for c in contacts_table.columns if c.name == "lifecyclestage")
            assert lifecycle_col.type == ColumnType.STRING
            assert "Lifecycle Stage (Options: Lead)" in lifecycle_col.description
