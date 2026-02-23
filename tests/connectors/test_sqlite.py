
import pytest

from mcp_maker.connectors.sqlite import SQLiteConnector


class TestSQLiteConnector:
    def test_validate_valid_db(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        assert connector.validate() is True

    def test_validate_missing_file(self):
        connector = SQLiteConnector("sqlite:///nonexistent.db")
        with pytest.raises(FileNotFoundError):
            connector.validate()

    def test_inspect_tables(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()

        assert schema.source_type == "sqlite"
        assert len(schema.tables) == 2

        # Check table names
        table_names = [t.name for t in schema.tables]
        assert "users" in table_names
        assert "posts" in table_names

    def test_inspect_columns(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()

        users = next(t for t in schema.tables if t.name == "users")
        col_names = [c.name for c in users.columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert "age" in col_names

    def test_inspect_primary_key(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()

        users = next(t for t in schema.tables if t.name == "users")
        pk_cols = users.primary_key_columns
        assert len(pk_cols) == 1
        assert pk_cols[0].name == "id"

    def test_inspect_row_count(self, sample_db):
        connector = SQLiteConnector(f"sqlite:///{sample_db}")
        schema = connector.inspect()

        users = next(t for t in schema.tables if t.name == "users")
        assert users.row_count == 2

        posts = next(t for t in schema.tables if t.name == "posts")
        assert posts.row_count == 1
