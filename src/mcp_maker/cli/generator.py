
import json
import os
import subprocess
import sys

import typer
from rich.console import Console
from rich.table import Table as RichTable
from rich.panel import Panel

from mcp_maker import __version__
from mcp_maker.core.schema import DataSourceSchema
from mcp_maker.connectors.base import get_connector, register_connector
from mcp_maker.core.generator import generate_server_code, write_server
from .main import app, console

def _load_connectors():
    """Import all built-in connectors to trigger registration."""
    from mcp_maker.connectors import sqlite  # noqa: F401
    from mcp_maker.connectors import files  # noqa: F401

    # Optional connectors — only load if dependencies available
    try:
        from mcp_maker.connectors import postgres  # noqa: F401
    except ImportError:
        pass

    try:
        from mcp_maker.connectors import mysql  # noqa: F401
    except ImportError:
        pass

    try:
        from mcp_maker.connectors import airtable  # noqa: F401
    except ImportError:
        pass

    try:
        from mcp_maker.connectors import gsheets  # noqa: F401
    except ImportError:
        pass

    try:
        from mcp_maker.connectors import notion  # noqa: F401
    except ImportError:
        pass

def _print_schema_summary(schema):
    """Pretty-print a schema summary using Rich."""
    if schema.tables:
        table = RichTable(title=f"📊 Discovered Tables ({len(schema.tables)})")
        table.add_column("Table", style="cyan", no_wrap=True)
        table.add_column("Columns", style="green")
        table.add_column("Rows", justify="right")
        table.add_column("Primary Key", style="yellow")

        for t in schema.tables:
            cols = ", ".join(c.name for c in t.columns[:6])
            if len(t.columns) > 6:
                cols += f" (+{len(t.columns) - 6} more)"
            pk = ", ".join(c.name for c in t.primary_key_columns) or "—"
            rows = str(t.row_count) if t.row_count is not None else "—"
            table.add_row(t.name, cols, rows, pk)

        console.print()
        console.print(table)

    if schema.resources:
        res_table = RichTable(title=f"📄 Discovered Resources ({len(schema.resources)})")
        res_table.add_column("Name", style="cyan")
        res_table.add_column("Type", style="green")

        for r in schema.resources:
            res_table.add_row(r.name, r.mime_type)

        console.print()
        console.print(res_table)



@app.command()
def init(
    source: str = typer.Argument(
        ...,
        help="Data source URI (e.g., sqlite:///my.db, ./data/, postgres://...)",
    ),
    output: str = typer.Option(
        ".",
        "--output", "-o",
        help="Output directory for the generated server file.",
    ),
    filename: str = typer.Option(
        "mcp_server.py",
        "--filename", "-f",
        help="Name of the generated server file.",
    ),
    read_write: bool = typer.Option(
        False,
        "--read-write",
        help="Generate write tools (INSERT, UPDATE, DELETE) in addition to read tools.",
    ),
    tables: str = typer.Option(
        None,
        "--tables", "-t",
        help="Comma-separated list of table names to include (default: all). Example: --tables users,orders",
    ),
    ops: str = typer.Option(
        None,
        "--ops",
        help="Comma-separated operations to generate tools for (read,insert,update,delete). Defaults to 'read'.",
    ),
    semantic: bool = typer.Option(
        False,
        "--semantic",
        help="Generate semantic (vector) search tools using ChromaDB. Requires: pip install mcp-maker[semantic]",
    ),
):
    """⚒️  Generate an MCP server from a data source.

    Examples:
        mcp-maker init sqlite:///my.db
        mcp-maker init ./data/
        mcp-maker init postgres://user:pass@localhost/mydb
        mcp-maker init sqlite:///my.db --read-write
        mcp-maker init sqlite:///my.db --ops read,insert
        mcp-maker init sqlite:///my.db --tables users,orders
        mcp-maker init sqlite:///my.db --semantic
    """
    _load_connectors()
    from mcp_maker.connectors.base import get_connector
    from mcp_maker.core.generator import write_server

    console.print()
    console.print(
        Panel.fit("⚒️  [bold cyan]MCP-Maker[/bold cyan]", subtitle="v" + __version__)
    )

    # Step 1: Resolve connector
    with console.status("[bold green]Connecting to data source..."):
        try:
            connector = get_connector(source)
        except ValueError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

    # Step 2: Validate
    with console.status(f"[bold green]Validating {connector.source_type} source..."):
        try:
            connector.validate()
        except (FileNotFoundError, ConnectionError, ValueError, ImportError) as e:
            console.print(f"\n[red]Validation failed:[/red] {e}")
            raise typer.Exit(code=1)

    console.print(f"  ✅ Connected to [cyan]{connector.source_type}[/cyan] source")

    # Step 3: Inspect schema
    with console.status("[bold green]Inspecting data source..."):
        schema = connector.inspect()

    # Filter tables if --tables specified
    if tables:
        wanted = {t.strip().lower() for t in tables.split(",") if t.strip()}
        before_count = len(schema.tables)
        schema.tables = [t for t in schema.tables if t.name.lower() in wanted]
        skipped = before_count - len(schema.tables)
        if skipped > 0:
            console.print(f"  📋 Filtered: keeping {len(schema.tables)} of {before_count} tables ({skipped} skipped)")
        if not schema.tables:
            console.print("\n[red]Error:[/red] No matching tables found.")
            console.print(f"  Requested: {tables}")
            raise typer.Exit(code=1)

    # Parse ops
    parsed_ops = ["read"]
    if read_write:
        parsed_ops = ["read", "insert", "update", "delete"]
    if ops:
        parsed_ops = [op.strip().lower() for op in ops.split(",") if op.strip()]

    # Warn about monolithic scaling for large schemas
    table_count = len(schema.tables)
    if table_count > 20:
        tools_per_table = (2 if "read" in parsed_ops else 0) + (1 if "insert" in parsed_ops else 0) + (1 if "update" in parsed_ops else 0) + (1 if "delete" in parsed_ops else 0) + (2 if semantic else 0)
        estimated_tools = table_count * tools_per_table
        console.print()
        console.print(f"  ⚠️  [yellow]Large schema detected:[/yellow] {table_count} tables → ~{estimated_tools} tools")
        console.print(f"  [dim]Tip: Use [cyan]--tables users,orders[/cyan] to only include what you need.[/dim]")
        console.print(f"  [dim]Large tool counts may exceed LLM context windows.[/dim]")

    # Print schema summary
    _print_schema_summary(schema)

    # Step 4: Generate server
    with console.status("[bold green]Generating MCP server..."):
        output_path = write_server(
            schema,
            output_dir=output,
            filename=filename,
            ops=parsed_ops,
            semantic=semantic,
        )

    console.print()
    console.print(f"  🎉 Generated: [bold green]{output_path}[/bold green]")
    console.print(f"  🔧 [yellow]Operations enabled:[/yellow] {', '.join(op.upper() for op in parsed_ops)}")
    if semantic:
        console.print("  🧠 [magenta]Semantic search enabled[/magenta] (ChromaDB vector search)")
    console.print()
    console.print("  [dim]Next steps:[/dim]")
    console.print(f"    [cyan]mcp-maker serve[/cyan]           — Run the server")
    console.print(f"    [cyan]mcp-maker config[/cyan]          — Generate Claude Desktop config")
    console.print(f"    [cyan]python {filename}[/cyan]  — Run directly")
    console.print()


@app.command()
def inspect(
    source: str = typer.Argument(
        ...,
        help="Data source URI to inspect (dry run, no files generated).",
    ),
    tables: str = typer.Option(
        None,
        "--tables", "-t",
        help="Comma-separated list of table names to include (default: all).",
    ),
):
    """🔍 Preview the schema that would be generated (dry run)."""
    _load_connectors()
    from mcp_maker.connectors.base import get_connector

    console.print()

    with console.status("[bold green]Inspecting data source..."):
        try:
            connector = get_connector(source)
            connector.validate()
            schema = connector.inspect()
        except (ValueError, FileNotFoundError, ConnectionError, ImportError) as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

    # Filter tables if --tables specified
    if tables:
        wanted = {t.strip().lower() for t in tables.split(",") if t.strip()}
        schema.tables = [t for t in schema.tables if t.name.lower() in wanted]

    _print_schema_summary(schema)

    # Also show what tools would be generated
    console.print()
    console.print("[bold]Tools that would be generated:[/bold]")
    for table in schema.tables:
        console.print(f"\n  📋 [cyan]{table.name}[/cyan]:")
        console.print(f"    • list_{table.name}(limit, offset)")
        if table.primary_key_columns:
            pk = table.primary_key_columns[0]
            console.print(f"    • get_{table.name}_by_{pk.name}({pk.name})")
        if table.searchable_columns:
            console.print(f"    • search_{table.name}(query, limit)")
        console.print(f"    • count_{table.name}()")
        console.print(f"    • schema_{table.name}()")
        console.print(f"    [dim]With --read-write:[/dim]")
        if table.primary_key_columns:
            pk = table.primary_key_columns[0]
            console.print(f"    • insert_{table.name}(...)")
            console.print(f"    • update_{table.name}_by_{pk.name}(...)")
            console.print(f"    • delete_{table.name}_by_{pk.name}({pk.name})")

    for resource in schema.resources:
        console.print(f"\n  📄 [cyan]{resource.name}[/cyan]:")
        console.print(f"    • read_{resource.name}() → {resource.mime_type}")

    console.print()
