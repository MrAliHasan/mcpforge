"""Tests for the OpenAPI connector — uses temp JSON spec files."""

import json
import os
import tempfile

import pytest

from mcp_maker.connectors.openapi import (
    OpenAPIConnector,
    _openapi_type_to_column_type,
    _sanitize_operation_id,
)
from mcp_maker.core.schema import ColumnType


SAMPLE_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Pet Store", "version": "1.0.0"},
    "servers": [{"url": "https://api.example.com/v1"}],
    "paths": {
        "/pets": {
            "get": {
                "operationId": "listPets",
                "summary": "List all pets",
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}, "required": False},
                    {"name": "status", "in": "query", "schema": {"type": "string"}, "required": True},
                ],
            },
            "post": {
                "operationId": "createPet",
                "summary": "Create a pet",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "properties": {
                                    "name": {"type": "string"},
                                    "age": {"type": "integer"},
                                    "tags": {"type": "array"},
                                },
                                "required": ["name"],
                            }
                        }
                    }
                },
            },
        },
        "/pets/{petId}": {
            "get": {
                "operationId": "getPet",
                "summary": "Get a pet by ID",
                "parameters": [
                    {"name": "petId", "in": "path", "schema": {"type": "integer"}, "required": True},
                ],
            },
            "delete": {
                "summary": "Delete a pet",
                "parameters": [
                    {"name": "petId", "in": "path", "schema": {"type": "integer"}, "required": True},
                ],
            },
        },
    },
}


class TestOpenAPIConnector:
    def test_source_type(self):
        c = OpenAPIConnector("openapi:///spec.json")
        assert c.source_type == "openapi"

    def test_get_spec_path_triple_slash(self):
        c = OpenAPIConnector("openapi:///absolute/path/spec.json")
        assert c._get_spec_path() == "absolute/path/spec.json"

    def test_get_spec_path_double_slash(self):
        c = OpenAPIConnector("openapi://https://api.example.com/spec.json")
        assert c._get_spec_path() == "https://api.example.com/spec.json"

    def test_validate_valid_spec(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(SAMPLE_SPEC, f)
            path = f.name
        try:
            c = OpenAPIConnector(path)
            assert c.validate() is True
        finally:
            os.unlink(path)

    def test_validate_missing_paths(self):
        spec = {"openapi": "3.0.0", "info": {}}  # No paths
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(spec, f)
            path = f.name
        try:
            c = OpenAPIConnector(path)
            with pytest.raises(ValueError, match="no 'paths'"):
                c.validate()
        finally:
            os.unlink(path)

    def test_validate_not_openapi(self):
        spec = {"paths": {"/a": {}}}  # No openapi or swagger key
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(spec, f)
            path = f.name
        try:
            c = OpenAPIConnector(path)
            with pytest.raises(ValueError, match="Not a valid"):
                c.validate()
        finally:
            os.unlink(path)

    def test_validate_nonexistent_file(self):
        c = OpenAPIConnector("openapi:///nonexistent.json")
        with pytest.raises(ValueError, match="Cannot load"):
            c.validate()

    def test_inspect_full_spec(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(SAMPLE_SPEC, f)
            path = f.name
        try:
            c = OpenAPIConnector(path)
            schema = c.inspect()
            assert schema.source_type == "openapi"
            assert schema.metadata["spec_title"] == "Pet Store"
            assert schema.metadata["base_url"] == "https://api.example.com/v1"
            assert len(schema.tables) == 4  # get /pets, post /pets, get /pets/{petId}, delete /pets/{petId}

            # Check operation names
            table_names = sorted(t.name for t in schema.tables)
            assert "listpets" in table_names
            assert "createpet" in table_names
            assert "getpet" in table_names
        finally:
            os.unlink(path)

    def test_inspect_swagger2(self):
        spec = {
            "swagger": "2.0",
            "host": "api.example.com",
            "basePath": "/v1",
            "schemes": ["https"],
            "info": {"title": "API", "version": "2.0"},
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "listItems",
                        "parameters": [
                            {"name": "limit", "in": "query", "type": "integer"},
                        ],
                    }
                }
            },
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(spec, f)
            path = f.name
        try:
            c = OpenAPIConnector(path)
            schema = c.inspect()
            assert schema.metadata["base_url"] == "https://api.example.com/v1"
            assert len(schema.tables) == 1
        finally:
            os.unlink(path)

    def test_load_spec_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(SAMPLE_SPEC, f)
            path = f.name
        try:
            c = OpenAPIConnector(path)
            spec = c._load_spec()
            assert spec["openapi"] == "3.0.0"
        finally:
            os.unlink(path)


class TestOpenAPIHelpers:
    def test_type_mapping_integer(self):
        assert _openapi_type_to_column_type({"type": "integer"}) == ColumnType.INTEGER

    def test_type_mapping_number(self):
        assert _openapi_type_to_column_type({"type": "number"}) == ColumnType.FLOAT

    def test_type_mapping_boolean(self):
        assert _openapi_type_to_column_type({"type": "boolean"}) == ColumnType.BOOLEAN

    def test_type_mapping_array(self):
        assert _openapi_type_to_column_type({"type": "array"}) == ColumnType.JSON

    def test_type_mapping_object(self):
        assert _openapi_type_to_column_type({"type": "object"}) == ColumnType.JSON

    def test_type_mapping_date(self):
        assert _openapi_type_to_column_type({"type": "string", "format": "date-time"}) == ColumnType.DATETIME

    def test_type_mapping_string_default(self):
        assert _openapi_type_to_column_type({"type": "string"}) == ColumnType.STRING

    def test_sanitize_operation_id(self):
        assert _sanitize_operation_id("get", "/users/{id}/posts") == "get_users_id_posts"

    def test_sanitize_operation_id_root(self):
        assert _sanitize_operation_id("get", "/") == "get_"
