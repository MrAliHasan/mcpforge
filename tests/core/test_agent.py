"""
Tests for MCP-Maker Chat Agent — core/agent.py

Covers:
- schema_to_tools: schema → OpenAI function-calling format
- QueryExecutor: SQL query execution against SQLite
- ChatAgent: multi-turn conversation with mocked LLM
"""

import json
import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from mcp_maker.core.agent import ChatAgent, QueryExecutor, schema_to_tools
from mcp_maker.core.schema import (
    Column,
    ColumnType,
    DataSourceSchema,
    ForeignKey,
    Table,
)


# ──── Fixtures ────


@pytest.fixture
def sample_schema():
    """A realistic schema with 2 tables and a foreign key."""
    return DataSourceSchema(
        source_type="sqlite",
        source_uri="sqlite:///test.db",
        tables=[
            Table(
                name="employees",
                columns=[
                    Column(name="id", type=ColumnType.INTEGER, nullable=False, primary_key=True),
                    Column(name="name", type=ColumnType.STRING, nullable=False),
                    Column(name="email", type=ColumnType.STRING, nullable=True),
                    Column(name="department", type=ColumnType.STRING, nullable=True),
                    Column(name="salary", type=ColumnType.FLOAT, nullable=True),
                ],
                row_count=10,
            ),
            Table(
                name="projects",
                columns=[
                    Column(name="id", type=ColumnType.INTEGER, nullable=False, primary_key=True),
                    Column(name="name", type=ColumnType.STRING, nullable=False),
                    Column(name="budget", type=ColumnType.FLOAT, nullable=True),
                    Column(name="status", type=ColumnType.STRING, nullable=True),
                ],
                row_count=5,
            ),
        ],
        foreign_keys=[
            ForeignKey(
                from_table="projects",
                from_column="lead_id",
                to_table="employees",
                to_column="id",
            ),
        ],
    )


@pytest.fixture
def test_db():
    """Creates a temporary SQLite database with sample data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE employees ("
        "  id INTEGER PRIMARY KEY,"
        "  name TEXT NOT NULL,"
        "  email TEXT,"
        "  department TEXT,"
        "  salary REAL"
        ")"
    )
    conn.executemany(
        "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Ali Hassan", "ali@test.com", "Engineering", 120000),
            (2, "Sarah Chen", "sarah@test.com", "Marketing", 95000),
            (3, "James Wilson", "james@test.com", "Engineering", 110000),
            (4, "Maria Garcia", "maria@test.com", "Sales", 105000),
            (5, "David Kim", "david@test.com", "Engineering", 130000),
        ],
    )
    conn.commit()
    conn.close()

    yield db_path
    os.unlink(db_path)


@pytest.fixture
def executor(test_db, sample_schema):
    """QueryExecutor backed by the test database."""
    return QueryExecutor(test_db, sample_schema)


# ──── schema_to_tools Tests ────


class TestSchemaToTools:
    """Test schema → OpenAI tools conversion."""

    def test_generates_tools_for_each_table(self, sample_schema):
        tools = schema_to_tools(sample_schema)
        names = [t["function"]["name"] for t in tools]
        # employees: list, get, search, count = 4
        # projects: list, get, search, count = 4
        assert len(tools) == 8

    def test_tool_structure(self, sample_schema):
        tools = schema_to_tools(sample_schema)
        tool = tools[0]
        assert tool["type"] == "function"
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]

    def test_list_tool_has_pagination_params(self, sample_schema):
        tools = schema_to_tools(sample_schema)
        list_tool = next(t for t in tools if t["function"]["name"] == "list_employees")
        params = list_tool["function"]["parameters"]["properties"]
        assert "limit" in params
        assert "offset" in params
        assert "order_by" in params
        assert "order_dir" in params

    def test_list_tool_has_filter_columns(self, sample_schema):
        tools = schema_to_tools(sample_schema)
        list_tool = next(t for t in tools if t["function"]["name"] == "list_employees")
        params = list_tool["function"]["parameters"]["properties"]
        # Non-PK columns should be available as filters
        assert "name" in params
        assert "department" in params
        assert "salary" in params
        # PK should not be a filter
        assert "id" not in params

    def test_get_tool_requires_pk(self, sample_schema):
        tools = schema_to_tools(sample_schema)
        get_tool = next(t for t in tools if t["function"]["name"] == "get_employees")
        required = get_tool["function"]["parameters"]["required"]
        assert "id" in required

    def test_search_tool_exists_for_searchable_tables(self, sample_schema):
        tools = schema_to_tools(sample_schema)
        names = [t["function"]["name"] for t in tools]
        assert "search_employees" in names
        assert "search_projects" in names

    def test_count_tool_has_filter_params(self, sample_schema):
        tools = schema_to_tools(sample_schema)
        count_tool = next(t for t in tools if t["function"]["name"] == "count_employees")
        params = count_tool["function"]["parameters"]["properties"]
        assert "department" in params

    def test_type_mapping(self, sample_schema):
        tools = schema_to_tools(sample_schema)
        list_tool = next(t for t in tools if t["function"]["name"] == "list_employees")
        params = list_tool["function"]["parameters"]["properties"]
        assert params["name"]["type"] == "string"
        assert params["salary"]["type"] == "number"

    def test_empty_schema(self):
        schema = DataSourceSchema(
            source_type="sqlite",
            source_uri="sqlite:///empty.db",
            tables=[],
        )
        tools = schema_to_tools(schema)
        assert tools == []


# ──── QueryExecutor Tests ────


class TestQueryExecutor:
    """Test SQL query execution against SQLite."""

    def test_list_all(self, executor):
        result = json.loads(executor.execute("list_employees", {}))
        assert len(result) == 5
        assert result[0]["name"] == "Ali Hassan"

    def test_list_with_limit(self, executor):
        result = json.loads(executor.execute("list_employees", {"limit": 2}))
        assert len(result) == 2

    def test_list_with_filter(self, executor):
        result = json.loads(executor.execute("list_employees", {"department": "Engineering"}))
        assert len(result) == 3
        assert all(r["department"] == "Engineering" for r in result)

    def test_list_with_ordering(self, executor):
        result = json.loads(
            executor.execute("list_employees", {"order_by": "salary", "order_dir": "desc"})
        )
        assert result[0]["name"] == "David Kim"  # Highest salary
        assert result[0]["salary"] == 130000

    def test_list_with_offset(self, executor):
        result = json.loads(executor.execute("list_employees", {"limit": 2, "offset": 3}))
        assert len(result) == 2

    def test_get_by_id(self, executor):
        result = json.loads(executor.execute("get_employees", {"id": 1}))
        assert result["name"] == "Ali Hassan"

    def test_get_not_found(self, executor):
        result = json.loads(executor.execute("get_employees", {"id": 999}))
        assert "error" in result

    def test_search(self, executor):
        result = json.loads(executor.execute("search_employees", {"query": "Ali"}))
        assert len(result) == 1
        assert result[0]["name"] == "Ali Hassan"

    def test_search_multiple_results(self, executor):
        result = json.loads(executor.execute("search_employees", {"query": "a"}))
        # Ali Hassan, Sarah Chen, James Wilson, Maria Garcia, David Kim
        # "a" appears in Ali, Sarah, James, Maria, David (in name) and all emails
        assert len(result) >= 1

    def test_count_all(self, executor):
        result = json.loads(executor.execute("count_employees", {}))
        assert result["count"] == 5

    def test_count_with_filter(self, executor):
        result = json.loads(executor.execute("count_employees", {"department": "Engineering"}))
        assert result["count"] == 3

    def test_unknown_table(self, executor):
        result = json.loads(executor.execute("list_nonexistent", {}))
        assert "error" in result

    def test_unknown_action(self, executor):
        result = json.loads(executor.execute("drop_employees", {}))
        assert "error" in result

    def test_invalid_tool_name(self, executor):
        result = json.loads(executor.execute("badformat", {}))
        assert "error" in result

    def test_invalid_column_ignored(self, executor):
        """Injected columns should be silently ignored, not cause SQL errors."""
        result = json.loads(
            executor.execute("list_employees", {"nonexistent_col": "value"})
        )
        # Should return all rows, ignoring the bad filter
        assert len(result) == 5

    def test_limit_capped(self, executor):
        """Limit should be capped at 500."""
        result = json.loads(executor.execute("list_employees", {"limit": 9999}))
        # Our table only has 5 rows, but the limit should be capped
        assert len(result) == 5


# ──── ChatAgent Tests ────


class TestChatAgent:
    """Test ChatAgent with mocked OpenAI client."""

    def _make_agent(self, sample_schema, executor, base_url=None):
        """Create a ChatAgent with a mocked OpenAI client."""
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client

        with patch.dict("sys.modules", {"openai": mock_openai}):
            agent = ChatAgent(
                api_key="test-key",
                model="gpt-4o-mini",
                schema=sample_schema,
                executor=executor,
                base_url=base_url,
            )
        return agent, mock_client, mock_openai

    def test_system_prompt_contains_schema(self, sample_schema, executor):
        agent, _, _ = self._make_agent(sample_schema, executor)
        system_msg = agent.history[0]["content"]
        assert "employees" in system_msg
        assert "projects" in system_msg
        assert "10 rows" in system_msg

    def test_system_prompt_contains_relationships(self, sample_schema, executor):
        agent, _, _ = self._make_agent(sample_schema, executor)
        system_msg = agent.history[0]["content"]
        assert "projects.lead_id" in system_msg
        assert "employees.id" in system_msg

    def test_tools_loaded(self, sample_schema, executor):
        agent, _, _ = self._make_agent(sample_schema, executor)
        assert len(agent.tools) == 8

    def test_ask_text_response(self, sample_schema, executor):
        agent, mock_client, _ = self._make_agent(sample_schema, executor)

        # Mock LLM returning a text-only response (no tool calls)
        mock_message = MagicMock()
        mock_message.tool_calls = None
        mock_message.content = "There are 10 employees."

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_message)]

        mock_client.chat.completions.create.return_value = mock_response

        answer = agent.ask("How many employees?")
        assert answer == "There are 10 employees."
        assert len(agent.last_tool_calls) == 0

    def test_ask_with_tool_call(self, sample_schema, executor):
        agent, mock_client, _ = self._make_agent(sample_schema, executor)

        # First response: LLM calls count_employees
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "count_employees"
        mock_tool_call.function.arguments = "{}"

        mock_msg_with_tools = MagicMock()
        mock_msg_with_tools.tool_calls = [mock_tool_call]
        mock_msg_with_tools.model_dump.return_value = {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_123", "function": {"name": "count_employees", "arguments": "{}"}}],
        }

        # Second response: LLM returns final answer
        mock_msg_final = MagicMock()
        mock_msg_final.tool_calls = None
        mock_msg_final.content = "There are 5 employees."

        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=mock_msg_with_tools)]),
            MagicMock(choices=[MagicMock(message=mock_msg_final)]),
        ]

        answer = agent.ask("How many employees?")
        assert answer == "There are 5 employees."
        assert len(agent.last_tool_calls) == 1
        assert "count_employees" in agent.last_tool_calls[0]

    def test_ask_error_handling(self, sample_schema, executor):
        agent, mock_client, _ = self._make_agent(sample_schema, executor)

        mock_client.chat.completions.create.side_effect = Exception(
            "Error code: 401 - {'error': {'message': 'Invalid API key', 'code': 401}}"
        )

        with pytest.raises(RuntimeError, match="Invalid API key"):
            agent.ask("test")

    def test_ask_error_pops_history(self, sample_schema, executor):
        agent, mock_client, _ = self._make_agent(sample_schema, executor)
        initial_len = len(agent.history)

        mock_client.chat.completions.create.side_effect = Exception("API error")

        with pytest.raises(RuntimeError):
            agent.ask("test")

        # User message should be popped from history on error
        assert len(agent.history) == initial_len

    def test_base_url_passed_to_client(self, sample_schema, executor):
        _, _, mock_openai = self._make_agent(
            sample_schema, executor, base_url="https://openrouter.ai/api/v1"
        )
        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs[1]["base_url"] == "https://openrouter.ai/api/v1"

    def test_base_url_none_not_passed(self, sample_schema, executor):
        _, _, mock_openai = self._make_agent(sample_schema, executor)
        call_kwargs = mock_openai.OpenAI.call_args
        assert "base_url" not in call_kwargs[1]

    def test_conversation_history_grows(self, sample_schema, executor):
        agent, mock_client, _ = self._make_agent(sample_schema, executor)

        mock_message = MagicMock()
        mock_message.tool_calls = None
        mock_message.content = "Answer"
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=mock_message)]
        )

        agent.ask("Q1")
        agent.ask("Q2")
        # system + user + assistant + user + assistant = 5
        assert len(agent.history) == 5
