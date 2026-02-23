import os
import sys
import tempfile
import sqlite3
import importlib.util

import pytest

from mcp_maker.connectors.sqlite import SQLiteConnector
from mcp_maker.core.generator import write_server

@pytest.fixture
def sample_e2e_db():
    """Create a temporary SQLite database for End-to-End testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE e2e_users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            active BOOLEAN DEFAULT 1
        )
    """)
    conn.execute(
        "INSERT INTO e2e_users (username) VALUES (?), (?)",
        ("Alice_E2E", "Bob_E2E"),
    )
    conn.commit()
    conn.close()

    yield db_path
    os.unlink(db_path)


@pytest.mark.asyncio
async def test_generated_server_execution(sample_e2e_db, monkeypatch):
    """
    End-to-End Test:
    1. Inspects the sample DB.
    2. Generates the mcp_server.py code.
    3. Dynamically imports the generated FastMCP instance.
    4. Invokes the generated 'list_e2e_users' tool natively.
    5. Asserts the correct data is returned from the database.
    """
    # 1. Inspect
    connector = SQLiteConnector(f"sqlite:///{sample_e2e_db}")
    schema = connector.inspect()

    # 2. Generate
    with tempfile.TemporaryDirectory() as tmpdir:
        server_file = "mcp_server_e2e.py"
        server_path, autogen_path, server_created = write_server(
            schema,
            output_dir=tmpdir,
            filename=server_file,
            ops=["read", "insert", "update", "delete"]
        )

        assert os.path.exists(server_path)
        assert os.path.exists(autogen_path)

        # 3. Dynamically import the generated server module
        sys.path.insert(0, tmpdir)
        try:
            spec = importlib.util.spec_from_file_location("_autogen_mcp_server_e2e", autogen_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Ensure the 'mcp' object is exported
            assert hasattr(module, "mcp")
            mcp = getattr(module, "mcp")
            
            # The tools are fastmcp.utilities.types.Tool objects, we need to execute the function directly.
            # In FastMCP, tools are added via decorator, but we can call the underlying python function if we want.
            # Or we can just call it via mcp._tool_registry?
            # Actually, `list_e2e_users` is directly exported on the module since it's a top level def!
            assert hasattr(module, "list_e2e_users")
            assert hasattr(module, "insert_e2e_users")

            # 4. Invoke list tool
            list_func = getattr(module, "list_e2e_users")
            response = list_func(limit=10, offset=0)
            
            # 5. Assertions — list_ now returns {results, total, has_more, next_offset}
            assert isinstance(response, dict), f"Expected dict, got {type(response)}"
            results = response["results"]
            assert len(results) == 2
            assert results[0]["username"] == "Alice_E2E"
            assert results[1]["username"] == "Bob_E2E"
            assert response["total"] == 2
            assert response["has_more"] is False

            # 6. Invoke insert tool
            insert_func = getattr(module, "insert_e2e_users")
            new_record = insert_func(username="Charlie_E2E")
            assert new_record["id"] == 3
            assert new_record["username"] == "Charlie_E2E"

            # Verify it was persisted
            response2 = list_func()
            assert len(response2["results"]) == 3

        finally:
            # Clean up sys.path
            sys.path.remove(tmpdir)
