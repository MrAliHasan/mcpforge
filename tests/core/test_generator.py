import os
import tempfile


from mcp_maker.core.schema import (
    Column,
    ColumnType,
    DataSourceSchema,
    Table,
)
from mcp_maker.connectors.sqlite import SQLiteConnector
from mcp_maker.connectors.files import FileConnector
from mcp_maker.core.generator import generate_server_code
from mcp_maker.cli import app
from typer.testing import CliRunner


class TestCodeGenerator:
    def test_generate_sqlite_server(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        # Should be valid Python
        compile(code, "<generated>", "exec")

        # Should contain expected tools
        assert "def list_users" in code
        assert "def list_posts" in code
        assert "def get_users_by_id" in code
        assert "def search_users" in code
        assert "def count_users" in code
        assert "def schema_users" in code

        # Should use FastMCP
        assert "from mcp.server.fastmcp import FastMCP" in code

    def test_generate_file_server(self, sample_data_dir):
        connector = FileConnector(sample_data_dir)
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        # Should be valid Python
        compile(code, "<generated>", "exec")

        # Should contain tools for products
        assert "def list_products" in code
        assert "def search_products" in code

        # Should contain resource for readme
        assert "read_readme" in code

    def test_generated_code_has_main(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        assert 'if __name__ == "__main__":' in code
        assert "mcp.run()" in code

    def test_generate_read_only_by_default(self, sample_db):
        """Verify that by default, write tools are NOT generated."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, ops=["read"]))

        assert "def insert_users" not in code
        assert "def update_users_by_id" not in code
        assert "def delete_users_by_id" not in code
        assert "def insert_posts" not in code

    def test_generate_read_write_mode(self, sample_db):
        """Verify that write tools ARE generated with read_only=False."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, ops=["read", "insert", "update", "delete"]))

        # Should be valid Python
        compile(code, "<generated>", "exec")

        # Should contain write tools
        assert "def insert_users" in code
        assert "def update_users_by_id" in code
        assert "def delete_users_by_id" in code

        # Should still have read tools
        assert "def list_users" in code
        assert "def get_users_by_id" in code
        assert "def search_users" in code

    def test_branding_in_generated_code(self, sample_db):
        """Verify template uses MCP-Maker branding, not MCPForge."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        assert "MCP-Maker" in code
        assert "mcp-maker" in code
        # Should NOT contain old branding
        assert "MCPForge" not in code
        assert "mcpforge" not in code


class TestGeneratedCodePatterns:
    """Tests to verify that generated code follows correct patterns."""

    def test_sqlite_uses_raise_on_error(self, sample_db):
        """Generated SQLite tools should raise RuntimeError, not return error dicts."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        assert 'raise RuntimeError' in code
        assert 'return {"error"' not in code

    def test_sqlite_write_has_rollback(self, sample_db):
        """Generated SQLite write tools should call conn.rollback() on error."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, ops=["read", "insert", "update", "delete"]))

        assert "conn.rollback()" in code
        assert 'raise RuntimeError(f"insert_' in code
        assert 'raise RuntimeError(f"update_' in code
        assert 'raise RuntimeError(f"delete_' in code

    def test_postgres_has_connection_pool(self):
        """Generated Postgres code should use a ThreadedConnectionPool."""
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="postgres",
            source_uri="postgresql://user:pass@localhost/testdb",
            tables=[
                Table(
                    name="items",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="name", type=ColumnType.STRING),
                    ],
                    row_count=10,
                )
            ],
        )
        code = "\n\n".join(generate_server_code(schema))

        assert "ThreadedConnectionPool" in code
        assert "_put_connection" in code
        assert "raise RuntimeError" in code
        assert 'return {"error"' not in code

    def test_mysql_has_connection_pool(self):
        """Generated MySQL code should use a queue-based connection pool."""
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType

        schema = DataSourceSchema(
            source_type="mysql",
            source_uri="mysql://user:pass@localhost/testdb",
            tables=[
                Table(
                    name="orders",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="total", type=ColumnType.FLOAT),
                    ],
                    row_count=5,
                )
            ],
            metadata={"host": "localhost", "port": 3306, "user": "root", "password": "", "database": "testdb"},
        )
        code = "\n\n".join(generate_server_code(schema))

        assert "_mysql_pool" in code
        assert "_put_connection" in code
        assert "ping(reconnect=True)" in code
        assert "raise RuntimeError" in code
        assert 'return {"error"' not in code

    def test_large_schema_cli_warning(self):
        """CLI should warn when schema has >20 tables."""

        runner = CliRunner()

        # Create a SQLite DB with 25 tables
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            for i in range(25):
                conn.execute(f"CREATE TABLE table_{i} (id INTEGER PRIMARY KEY, name TEXT)")
                conn.execute(f"INSERT INTO table_{i} (name) VALUES ('test')")
            conn.commit()
            conn.close()

            result = runner.invoke(app, ["init", f"sqlite:///{db_path}"])
            assert "Large schema detected" in result.output
            assert "25 tables" in result.output
        finally:
            os.unlink(db_path)
            # Clean up generated file if it exists
            if os.path.isfile("mcp_server.py"):
                os.unlink("mcp_server.py")


class TestRBAC:
    def test_rbac_filters_operations(self):
        from mcp_maker.core.schema import DataSourceSchema, Table, Column, ColumnType
        
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(name="users", columns=[Column(name="id", type=ColumnType.INTEGER, primary_key=True)]),
                Table(name="orders", columns=[Column(name="id", type=ColumnType.INTEGER, primary_key=True)]),
            ]
        )
        
        # Test global ops
        server_code, autogen_code = generate_server_code(schema, ops=["read", "insert"])
        assert "def list_users(" in autogen_code
        assert "def list_orders(" in autogen_code
        assert "def insert_orders(" in autogen_code
        
        # Test granular RBAC config
        rbac_config = {
            "users": ["read"],
            "orders": ["insert"]
        }
        
        server_code, autogen_code = generate_server_code(schema, ops=["read", "insert"], rbac_config=rbac_config)
        assert "def list_users(" in autogen_code    # users has read
        assert "def insert_users(" not in autogen_code # users missing insert
        
        assert "def list_orders(" not in autogen_code  # orders missing read
        assert "def insert_orders(" in autogen_code   # orders has insert

class TestSecurityHardening:
    """Tests to verify that production security hardening is applied."""

    def test_consolidated_mode_has_table_whitelist(self, sample_db):
        """Generated consolidated-mode code should include _KNOWN_TABLES and _validate_table."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, consolidate_threshold=1))

        assert "_KNOWN_TABLES" in code
        assert "_validate_table" in code
        assert "table_name = _validate_table(table_name)" in code

    def test_consolidated_mode_blocks_unknown_tables(self, sample_db):
        """Generated consolidated-mode list_tables should return known tables only."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, consolidate_threshold=1))

        # Should return sorted known tables, not query sqlite_master
        assert "return sorted(_KNOWN_TABLES)" in code
        assert "sqlite_master" not in code

    def test_no_dead_imports_in_generated_code(self, sample_db):
        """Generated code should not contain unused traceback or sys imports."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema))

        assert "import traceback" not in code
        assert "import sys" not in code

    def test_no_autoescape_corruption(self):
        """Generated code should not HTML-escape special characters in names."""
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///test.db",
            tables=[
                Table(
                    name="items",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="price_in_usd", type=ColumnType.FLOAT),
                    ],
                    row_count=5,
                )
            ],
        )
        code = "\n\n".join(generate_server_code(schema))

        # Should be valid Python
        compile(code, "<generated>", "exec")

        # Should not contain any HTML entities
        assert "&amp;" not in code
        assert "&lt;" not in code
        assert "&gt;" not in code

    def test_postgres_lazy_pool_initialization(self):
        """Generated Postgres code should use lazy pool initialization."""
        schema = DataSourceSchema(
            source_type="postgres",
            source_uri="postgresql://user:pass@localhost/testdb",
            tables=[
                Table(
                    name="items",
                    columns=[
                        Column(name="id", type=ColumnType.INTEGER, primary_key=True),
                        Column(name="name", type=ColumnType.STRING),
                    ],
                    row_count=10,
                )
            ],
        )
        code = "\n\n".join(generate_server_code(schema))

        assert "_pg_pool = None" in code
        assert "def _get_pool():" in code
        # Should NOT crash on import by creating pool at module level
        assert "ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DSN)" in code

    def test_sqlite_uses_configurable_max_limit(self, sample_db):
        """Generated SQLite code should use max_limit, not hardcoded 500."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, max_limit=1000))

        # Should use the configured max_limit, not hardcoded 500
        assert "min(limit, 1000)" in code
        assert "min(limit, 500)" not in code


class TestSchemaVersioning:
    """Tests for schema hash and lock file change detection."""

    def test_schema_hash_is_stable(self, sample_db):
        """Same schema should always produce the same hash."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        hash1 = schema.schema_hash
        hash2 = schema.schema_hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256

    def test_schema_diff_detects_changes(self):
        """schema_diff should detect added and removed tables."""
        diff = DataSourceSchema.schema_diff(
            ["users", "orders"],
            ["users", "products"],
        )
        assert diff["added"] == ["products"]
        assert diff["removed"] == ["orders"]

    def test_lock_file_written_on_generate(self, sample_db):
        """write_server should create .mcp-maker.lock."""
        from mcp_maker.core.generator import write_server, read_lock_file
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        with tempfile.TemporaryDirectory() as tmpdir:
            write_server(schema, output_dir=tmpdir)
            lock = read_lock_file(tmpdir)
            assert lock is not None
            assert "schema_hash" in lock
            assert "tables" in lock
            assert lock["source_type"] == "sqlite"


class TestSSLEnforcement:
    """Tests for SSL/TLS enforcement in generated code."""

    def test_postgres_ssl_enabled_by_default(self, sample_db):
        """Postgres code should enforce sslmode=require by default."""
        schema = DataSourceSchema(
            source_type="postgres",
            source_uri="postgres://localhost/test",
            tables=[Table(name="users", columns=[
                Column(name="id", type=ColumnType.INTEGER, primary_key=True),
            ])],
        )
        code = "\n\n".join(generate_server_code(schema))
        assert "sslmode=require" in code

    def test_postgres_ssl_disabled(self):
        """Postgres code should NOT enforce SSL when ssl_enabled=False."""
        schema = DataSourceSchema(
            source_type="postgres",
            source_uri="postgres://localhost/test",
            tables=[Table(name="users", columns=[
                Column(name="id", type=ColumnType.INTEGER, primary_key=True),
            ])],
        )
        code = "\n\n".join(generate_server_code(schema, ssl_enabled=False))
        assert "sslmode=require" not in code


class TestAuthMiddleware:
    """Tests for API key authentication in generated servers."""

    def test_auth_api_key_generates_middleware(self, sample_db):
        """--auth api-key should generate MCP_API_KEY check."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, auth_mode="api-key"))
        assert "MCP_API_KEY" in code
        assert "PermissionError" in code

    def test_auth_none_no_middleware(self, sample_db):
        """--auth none should NOT generate auth middleware."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, auth_mode="none"))
        assert "MCP_API_KEY" not in code


class TestAsyncGeneration:
    """Tests for async tool generation."""

    def test_async_sqlite_uses_aiosqlite(self, sample_db):
        """--async should generate aiosqlite imports."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, async_mode=True))
        assert "import aiosqlite" in code
        assert "import sqlite3" not in code
        assert "async def list_" in code
        assert "async with aiosqlite.connect" in code

    def test_sync_sqlite_no_aiosqlite(self, sample_db):
        """Non-async mode should NOT import aiosqlite."""
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()
        code = "\n\n".join(generate_server_code(schema, async_mode=False))
        assert "import sqlite3" in code
        assert "import aiosqlite" not in code

