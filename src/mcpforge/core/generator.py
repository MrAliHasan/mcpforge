"""
MCPForge Code Generator — Generates MCP server code from schemas.

Takes a DataSourceSchema and produces a complete, runnable MCP server
Python file using FastMCP (part of the official mcp SDK).
"""

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schema import DataSourceSchema

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def generate_server_code(schema: DataSourceSchema) -> str:
    """Generate a complete MCP server Python file from a schema.

    Args:
        schema: The inspected data source schema.

    Returns:
        A string containing valid Python code for an MCP server.
    """
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
    )


def write_server(
    schema: DataSourceSchema,
    output_dir: str = ".",
    filename: str = "mcp_server.py",
) -> str:
    """Generate and write the MCP server file to disk.

    Args:
        schema: The inspected data source schema.
        output_dir: Directory to write the server file to.
        filename: Name of the generated server file.

    Returns:
        The absolute path to the generated file.
    """
    code = generate_server_code(schema)
    output_path = os.path.join(output_dir, filename)
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(code)

    return os.path.abspath(output_path)
