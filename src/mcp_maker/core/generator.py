"""
MCP-Maker Code Generator — Generates MCP server code from schemas.

Takes a DataSourceSchema and produces a complete, runnable MCP server
Python file using FastMCP (part of the official mcp SDK).
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from .schema import DataSourceSchema

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
console = Console()

# Required metadata keys for each connector type
_REQUIRED_METADATA = {
    "airtable": ["base_id"],
    "gsheet": ["spreadsheet_id"],
    "notion": ["database_map"],
}


def _validate_schema_metadata(schema: DataSourceSchema) -> None:
    """Validate that the schema contains required metadata for its source type."""
    required = _REQUIRED_METADATA.get(schema.source_type, [])
    metadata = getattr(schema, "metadata", {}) or {}
    missing = [key for key in required if key not in metadata]
    if missing:
        raise ValueError(
            f"Schema for '{schema.source_type}' is missing required metadata: {', '.join(missing)}. "
            f"This usually means the connector didn't provide expected data."
        )

def generate_server_code(
    schema: DataSourceSchema,
    ops: list[str] = None,
    semantic: bool = False,
    default_limit: int = 50,
    max_limit: int = 500,
    target_filename: str = "mcp_server.py",
    autogen_module: str = "_autogen_tools",
    audit: bool = False,
    consolidate_threshold: int = 20,
) -> tuple[str, str]:
    """Generate complete MCP server Python code from a schema.

    Returns:
        A tuple of (server_code, autogen_code).
    """
    if ops is None:
        ops = ["read"]

    # Validate schema has required metadata for the connector type
    _validate_schema_metadata(schema)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,  # Generating Python code, not HTML
        trim_blocks=True,
        lstrip_blocks=True,
    )

    consolidate = False
    if len(schema.tables) > consolidate_threshold:
        consolidate = True

    context = {
        "schema": schema,
        "source_type": schema.source_type,
        "source_uri": schema.source_uri,
        "tables": schema.tables,
        "resources": schema.resources,
        "ops": ops,
        "semantic": semantic,
        "default_limit": default_limit,
        "max_limit": max_limit,
        "target_filename": target_filename,
        "autogen_module": autogen_module,
        "audit": audit,
        "consolidate": consolidate,
    }

    server_template = env.get_template("server.py.jinja2")
    autogen_template = env.get_template("_autogen.py.jinja2")

    server_code = server_template.render(**context)
    autogen_code = autogen_template.render(**context)

    return server_code, autogen_code


def format_and_verify_code(code: str, filename: str) -> str:
    """Verify code syntax using AST, and format it using Black if available."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        console.print(f"\n[bold red]SyntaxError in generated code for {filename}:[/bold red] {e}")
        console.print("[dim]This may be caused by complex schemas. Please report this issue.[/dim]")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "black", "-", "-q"],
            input=code,
            text=True,
            capture_output=True,
            check=True
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print(f"  [dim]⚠️  Warning: `black` formatter not found or failed. Code for {filename} is not auto-formatted.[/dim]")
        return code


def write_server(
    schema: DataSourceSchema,
    output_dir: str = ".",
    filename: str = "mcp_server.py",
    ops: list[str] = None,
    semantic: bool = False,
    default_limit: int = 50,
    max_limit: int = 500,
    audit: bool = False,
    consolidate_threshold: int = 20,
) -> tuple[str, str, bool]:
    """Write generated MCP server files.

    Generates `server.py` (only if it doesn't exist) and `_autogen_tools.py` (always overwritten).

    Returns:
        Tuple of (server_file_path, autogen_file_path, server_file_created).
    """
    # Compute safe module name
    base_name = os.path.splitext(filename)[0]
    autogen_module = f"_autogen_{base_name}"
    autogen_filename = f"{autogen_module}.py"

    server_code, autogen_code = generate_server_code(
        schema, 
        ops=ops, 
        semantic=semantic, 
        default_limit=default_limit, 
        max_limit=max_limit,
        target_filename=filename,
        autogen_module=autogen_module,
        audit=audit,
        consolidate_threshold=consolidate_threshold,
    )

    server_code_formatted = format_and_verify_code(server_code, filename)
    autogen_code_formatted = format_and_verify_code(autogen_code, autogen_filename)

    os.makedirs(output_dir, exist_ok=True)
    server_path = os.path.join(output_dir, filename)
    autogen_path = os.path.join(output_dir, autogen_filename)

    server_created = False
    if not os.path.exists(server_path):
        with open(server_path, "w", encoding="utf-8") as f:
            f.write(server_code_formatted)
        server_created = True

    with open(autogen_path, "w", encoding="utf-8") as f:
        f.write(autogen_code_formatted)

    return os.path.abspath(server_path), os.path.abspath(autogen_path), server_created
