"""
MCP-Maker Chat Agent — Interactive database chat via LLM function calling.

Converts a DataSourceSchema into OpenAI-compatible tools, executes queries
against the database, and manages multi-turn conversations.
"""

import json
import sqlite3
from dataclasses import dataclass

from ..core.schema import ColumnType, DataSourceSchema

# ──── Schema → OpenAI Tools Converter ────


_TYPE_MAP = {
    ColumnType.STRING: "string",
    ColumnType.INTEGER: "integer",
    ColumnType.FLOAT: "number",
    ColumnType.BOOLEAN: "boolean",
    ColumnType.DATE: "string",
    ColumnType.DATETIME: "string",
    ColumnType.JSON: "string",
    ColumnType.BLOB: "string",
    ColumnType.UNKNOWN: "string",
}


def schema_to_tools(schema: DataSourceSchema) -> list[dict]:
    """Convert a DataSourceSchema into OpenAI function-calling tool definitions.

    Generates list, search, count, and get tools for each table.
    """
    tools = []

    for table in schema.tables:
        col_names = [c.name for c in table.columns]
        col_desc = ", ".join(col_names)
        pk_cols = [c.name for c in table.primary_key_columns]
        pk_name = pk_cols[0] if pk_cols else "id"

        # list_<table>
        tools.append({
            "type": "function",
            "function": {
                "name": f"list_{table.name}",
                "description": (
                    f"List rows from the '{table.name}' table. "
                    f"Columns: {col_desc}."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max rows to return (default 50)",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "Rows to skip for pagination",
                        },
                        "order_by": {
                            "type": "string",
                            "description": f"Column to sort by. Options: {col_desc}",
                        },
                        "order_dir": {
                            "type": "string",
                            "enum": ["asc", "desc"],
                            "description": "Sort direction",
                        },
                        **{
                            col.name: {
                                "type": _TYPE_MAP.get(col.type, "string"),
                                "description": f"Filter by {col.name}",
                            }
                            for col in table.columns
                            if not col.primary_key
                        },
                    },
                    "required": [],
                },
            },
        })

        # get_<table>
        tools.append({
            "type": "function",
            "function": {
                "name": f"get_{table.name}",
                "description": (
                    f"Get a single row from '{table.name}' by {pk_name}."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        pk_name: {
                            "type": _TYPE_MAP.get(
                                next(
                                    (c.type for c in table.columns if c.name == pk_name),
                                    ColumnType.INTEGER,
                                ),
                                "integer",
                            ),
                            "description": f"The {pk_name} of the record",
                        },
                    },
                    "required": [pk_name],
                },
            },
        })

        # search_<table>
        searchable = [c.name for c in table.searchable_columns if not c.primary_key]
        if searchable:
            tools.append({
                "type": "function",
                "function": {
                    "name": f"search_{table.name}",
                    "description": (
                        f"Search '{table.name}' by text. "
                        f"Searches across: {', '.join(searchable)}."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search text",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Max results (default 20)",
                            },
                        },
                        "required": ["query"],
                    },
                },
            })

        # count_<table>
        tools.append({
            "type": "function",
            "function": {
                "name": f"count_{table.name}",
                "description": f"Count rows in '{table.name}', optionally filtered.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        **{
                            col.name: {
                                "type": _TYPE_MAP.get(col.type, "string"),
                                "description": f"Filter by {col.name}",
                            }
                            for col in table.columns
                            if not col.primary_key
                        },
                    },
                    "required": [],
                },
            },
        })

    return tools


# ──── Query Executor ────


class QueryExecutor:
    """Executes tool calls against a SQLite database.

    Translates high-level tool names (list_employees, search_orders)
    into SQL queries and runs them against the database.
    """

    def __init__(self, db_path: str, schema: DataSourceSchema):
        self.db_path = db_path
        self.schema = schema
        self._table_names = {t.name for t in schema.tables}
        self._column_names = {}
        for t in schema.tables:
            self._column_names[t.name] = {c.name for c in t.columns}

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _validate_column(self, table: str, col: str) -> bool:
        return col in self._column_names.get(table, set())

    def execute(self, tool_name: str, args: dict) -> str:
        """Execute a tool call and return JSON result."""
        parts = tool_name.split("_", 1)
        if len(parts) != 2:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

        action, table = parts[0], parts[1]

        if table not in self._table_names:
            return json.dumps({"error": f"Unknown table: {table}"})

        try:
            if action == "list":
                return self._list(table, args)
            elif action == "get":
                return self._get(table, args)
            elif action == "search":
                return self._search(table, args)
            elif action == "count":
                return self._count(table, args)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _list(self, table: str, args: dict) -> str:
        limit = min(int(args.pop("limit", 50)), 500)
        offset = int(args.pop("offset", 0))
        order_by = args.pop("order_by", None)
        order_dir = args.pop("order_dir", "asc")

        conn = self._get_conn()
        try:
            conditions, values = [], []
            for col, val in args.items():
                if self._validate_column(table, col):
                    conditions.append(f'"{col}" = ?')
                    values.append(val)

            query = f'SELECT * FROM "{table}"'
            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"
            if order_by and self._validate_column(table, order_by):
                direction = "DESC" if order_dir.lower() == "desc" else "ASC"
                query += f' ORDER BY "{order_by}" {direction}'
            query += f" LIMIT {limit} OFFSET {offset}"

            rows = conn.execute(query, values).fetchall()
            return json.dumps([dict(r) for r in rows], default=str)
        finally:
            conn.close()

    def _get(self, table: str, args: dict) -> str:
        conn = self._get_conn()
        try:
            pk_col = None
            for t in self.schema.tables:
                if t.name == table:
                    pks = t.primary_key_columns
                    pk_col = pks[0].name if pks else "id"
                    break

            pk_val = args.get(pk_col, args.get("id"))
            if pk_val is None:
                return json.dumps({"error": "Primary key value required"})

            row = conn.execute(
                f'SELECT * FROM "{table}" WHERE "{pk_col}" = ?', (pk_val,)
            ).fetchone()
            return json.dumps(dict(row) if row else {"error": "Not found"}, default=str)
        finally:
            conn.close()

    def _search(self, table: str, args: dict) -> str:
        query_text = args.get("query", "")
        limit = min(int(args.get("limit", 20)), 100)

        conn = self._get_conn()
        try:
            searchable = []
            for t in self.schema.tables:
                if t.name == table:
                    searchable = [
                        c.name for c in t.searchable_columns if not c.primary_key
                    ]
                    break

            if not searchable:
                return json.dumps({"error": "No searchable columns"})

            conditions = [f'"{col}" LIKE ?' for col in searchable]
            values = [f"%{query_text}%" for _ in searchable]

            sql = (
                f'SELECT * FROM "{table}" '
                f"WHERE {' OR '.join(conditions)} LIMIT {limit}"
            )
            rows = conn.execute(sql, values).fetchall()
            return json.dumps([dict(r) for r in rows], default=str)
        finally:
            conn.close()

    def _count(self, table: str, args: dict) -> str:
        conn = self._get_conn()
        try:
            conditions, values = [], []
            for col, val in args.items():
                if self._validate_column(table, col):
                    conditions.append(f'"{col}" = ?')
                    values.append(val)

            query = f'SELECT COUNT(*) as count FROM "{table}"'
            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"

            row = conn.execute(query, values).fetchone()
            return json.dumps({"count": row["count"]})
        finally:
            conn.close()


# ──── Chat Agent ────


@dataclass
class Message:
    """A single message in the conversation."""

    role: str
    content: str | None = None
    tool_calls: list | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ChatAgent:
    """Manages multi-turn conversations with an LLM and database tools.

    Sends user questions to OpenAI with auto-generated tools from the schema.
    When the LLM calls a tool, executes the query and returns results.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        schema: DataSourceSchema,
        executor: QueryExecutor,
        base_url: str | None = None,
    ):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI package required. Install with: "
                "pip install 'mcp-maker[chat]'"
            )

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**client_kwargs)
        self.model = model
        self.schema = schema
        self.executor = executor
        self.tools = schema_to_tools(schema)
        self.history: list[dict] = [
            {"role": "system", "content": self._build_system_prompt()},
        ]
        self.last_tool_calls: list[str] = []

    def _build_system_prompt(self) -> str:
        """Create a system prompt describing the database."""
        lines = [
            "You are a helpful database assistant. You have access to tools "
            "that query a database. Use these tools to answer the user's questions.",
            "",
            "Database schema:",
        ]
        for table in self.schema.tables:
            cols = ", ".join(
                f"{c.name} ({c.type.value}{'·PK' if c.primary_key else ''})"
                for c in table.columns
            )
            row_info = f" — {table.row_count} rows" if table.row_count else ""
            lines.append(f"  • {table.name}{row_info}: {cols}")

        if self.schema.foreign_keys:
            lines.append("\nRelationships:")
            for fk in self.schema.foreign_keys:
                lines.append(
                    f"  • {fk.from_table}.{fk.from_column} → "
                    f"{fk.to_table}.{fk.to_column}"
                )

        lines.extend([
            "",
            "Rules:",
            "- Always use the tools to get data, never make up answers.",
            "- Present data in clean, readable format.",
            "- If a query returns no results, say so clearly.",
            "- Be concise but thorough.",
        ])
        return "\n".join(lines)

    def ask(self, question: str) -> str:
        """Send a question and return the final answer.

        Handles multi-turn tool calling: if the LLM calls a tool,
        executes the query, feeds the result back, and repeats until
        the LLM returns a text answer.

        Returns:
            The LLM's final text response.
        """
        self.last_tool_calls = []
        self.history.append({"role": "user", "content": question})

        max_rounds = 10
        for _ in range(max_rounds):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.history,
                    tools=self.tools if self.tools else None,
                )
            except Exception as e:
                # Remove the failed user message from history
                self.history.pop()
                # Parse the actual error from OpenAI/OpenRouter
                error_msg = str(e)
                # Try to extract the nested error message
                if "message" in error_msg and "{" in error_msg:
                    try:
                        import ast
                        # Find the dict-like part of the error string
                        start = error_msg.index("{")
                        end = error_msg.rindex("}") + 1
                        err_dict = ast.literal_eval(error_msg[start:end])
                        if "error" in err_dict:
                            err_detail = err_dict["error"]
                            if isinstance(err_detail, dict):
                                error_msg = err_detail.get("message", error_msg)
                    except (ValueError, SyntaxError):
                        pass
                raise RuntimeError(f"LLM API error: {error_msg}") from None

            message = response.choices[0].message

            if message.tool_calls:
                # LLM wants to call tools
                self.history.append(message.model_dump())

                for tool_call in message.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)

                    self.last_tool_calls.append(
                        f"{fn_name}({', '.join(f'{k}={v!r}' for k, v in fn_args.items())})"
                    )

                    result = self.executor.execute(fn_name, fn_args)

                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                # LLM returned a text answer
                answer = message.content or ""
                self.history.append({"role": "assistant", "content": answer})
                return answer

        return "I couldn't complete the answer — too many tool calls needed."
