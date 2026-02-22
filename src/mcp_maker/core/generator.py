"""
MCP-Maker Code Generator — Generates MCP server code from schemas.

Takes a DataSourceSchema and produces a complete, runnable MCP server
Python file using FastMCP (part of the official mcp SDK).
"""

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schema import DataSourceSchema

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def generate_server_code(
    schema: DataSourceSchema,
    ops: list[str] = None,
    semantic: bool = False,
) -> str:
    """Generate a complete MCP server Python file from a schema.

    Args:
        schema: The inspected data source schema.
        ops: List of allowed operations. Can include 'read', 'insert', 'update', 'delete'.
            If None, defaults to ['read'].
        semantic: If True, generate semantic (vector) search tools
            using ChromaDB.

    Returns:
        A string containing valid Python code for an MCP server.
    """
    if ops is None:
        ops = ["read"]

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    template = env.get_template("server.py.jinja2")

    return template.render(
        schema=schema,
        source_type=schema.source_type,
        source_uri=schema.source_uri,
        tables=schema.tables,
        resources=schema.resources,
        ops=ops,
        semantic=semantic,
    )


def write_server(
    schema: DataSourceSchema,
    output_dir: str = ".",
    filename: str = "mcp_server.py",
    ops: list[str] = None,
    semantic: bool = False,
) -> str:
    """Write generated MCP server code to a file.

    Args:
        schema: The inspected data source schema.
        output_dir: Directory to write the server file to.
        filename: Name of the generated server file.
        ops: List of allowed operations. Can include 'read', 'insert', 'update', 'delete'.
            If None, defaults to ['read'].
        semantic: If True, generate semantic search tools.

    Returns:
        The absolute path to the generated file.
    """
    code = generate_server_code(schema, ops=ops, semantic=semantic)
    output_path = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)

    return os.path.abspath(output_path)
