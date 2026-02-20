"""
MCP-Maker CLI — The command-line interface for MCP-Maker.

Usage:
    mcp-maker init <source>     Generate an MCP server from a data source
    mcp-maker serve             Run the generated MCP server
    mcp-maker inspect <source>  Preview what would be generated (dry run)
    mcp-maker list-connectors   Show available connectors
"""

import os
import subprocess
import sys

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table as RichTable

from . import __version__

app = typer.Typer(
    name="mcp-maker",
    help="⚒️  Auto-generate MCP servers from any data source.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def _load_connectors():
    """Import all built-in connectors to trigger registration."""
    from .connectors import sqlite  # noqa: F401
    from .connectors import files  # noqa: F401


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
):
    """⚒️  Generate an MCP server from a data source.

    Examples:
        mcp-maker init sqlite:///my.db
        mcp-maker init ./data/
        mcp-maker init my_database.sqlite
    """
    _load_connectors()
    from .connectors.base import get_connector
    from .core.generator import write_server

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
        except (FileNotFoundError, ConnectionError, ValueError) as e:
            console.print(f"\n[red]Validation failed:[/red] {e}")
            raise typer.Exit(code=1)

    console.print(f"  ✅ Connected to [cyan]{connector.source_type}[/cyan] source")

    # Step 3: Inspect schema
    with console.status("[bold green]Inspecting data source..."):
        schema = connector.inspect()

    # Print schema summary
    _print_schema_summary(schema)

    # Step 4: Generate server
    with console.status("[bold green]Generating MCP server..."):
        output_path = write_server(schema, output_dir=output, filename=filename)

    console.print()
    console.print(f"  🎉 Generated: [bold green]{output_path}[/bold green]")
    console.print()
    console.print("  [dim]Next steps:[/dim]")
    console.print(f"    [cyan]mcp-maker serve[/cyan]           — Run the server")
    console.print(f"    [cyan]python {filename}[/cyan]  — Run directly")
    console.print()


@app.command()
def inspect(
    source: str = typer.Argument(
        ...,
        help="Data source URI to inspect (dry run, no files generated).",
    ),
):
    """🔍 Preview the schema that would be generated (dry run)."""
    _load_connectors()
    from .connectors.base import get_connector

    console.print()

    with console.status("[bold green]Inspecting data source..."):
        connector = get_connector(source)
        connector.validate()
        schema = connector.inspect()

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

    for resource in schema.resources:
        console.print(f"\n  📄 [cyan]{resource.name}[/cyan]:")
        console.print(f"    • read_{resource.name}() → {resource.mime_type}")

    console.print()


@app.command()
def serve(
    server_file: str = typer.Option(
        "mcp_server.py",
        "--file", "-f",
        help="Path to the generated server file.",
    ),
):
    """🚀 Run the generated MCP server."""
    if not os.path.isfile(server_file):
        console.print(
            f"\n[red]Error:[/red] Server file not found: {server_file}\n"
            f"Run [cyan]mcp-maker init <source>[/cyan] first to generate it.\n"
        )
        raise typer.Exit(code=1)

    console.print()
    console.print(
        Panel.fit("🚀 [bold cyan]MCP-Maker Server[/bold cyan]", subtitle="v" + __version__)
    )
    console.print(f"  Running: [green]{server_file}[/green]")
    console.print(f"  Press [bold]Ctrl+C[/bold] to stop\n")

    try:
        subprocess.run([sys.executable, server_file], check=True)
    except KeyboardInterrupt:
        console.print("\n  👋 Server stopped.")
    except subprocess.CalledProcessError as e:
        console.print(f"\n[red]Server exited with error code {e.returncode}[/red]")
        raise typer.Exit(code=e.returncode)


@app.command(name="list-connectors")
def list_connectors():
    """📋 Show available data source connectors."""
    _load_connectors()
    from .connectors.base import _CONNECTOR_REGISTRY

    console.print()
    table = RichTable(title="Available Connectors")
    table.add_column("Scheme", style="cyan", no_wrap=True)
    table.add_column("Connector", style="green")
    table.add_column("Example URI")

    examples = {
        "sqlite": "sqlite:///my_database.db",
        "files": "./data/",
        "postgres": "postgres://user:pass@localhost/mydb",
        "mysql": "mysql://user:pass@localhost/mydb",
        "airtable": "airtable://appXXXX",
    }

    for scheme, cls in sorted(_CONNECTOR_REGISTRY.items()):
        example = examples.get(scheme, f"{scheme}://...")
        table.add_row(scheme, cls.__name__, example)

    console.print(table)
    console.print()


@app.callback()
def main():
    """⚒️  MCP-Maker — Auto-generate MCP servers from any data source."""


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
