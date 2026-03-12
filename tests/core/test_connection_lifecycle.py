"""Tests for connection lifecycle management in generated servers.

Verifies that generated code properly cleans up database connections
on shutdown and does not leak file handles or pool connections.
"""

from mcp_maker.connectors.sqlite import SQLiteConnector
from mcp_maker.core.generator import generate_server_code


class TestSQLiteConnectionLifecycle:
    """Generated SQLite code must register atexit cleanup for thread-local connections."""

    def test_registers_atexit_handler(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        _, autogen = generate_server_code(schema)

        assert "import atexit" in autogen
        assert "_all_connections" in autogen
        assert "atexit.register(_cleanup_connections)" in autogen
        assert "def _cleanup_connections():" in autogen
