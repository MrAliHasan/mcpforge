"""
MCP-Maker CLI — The command-line interface for MCP-Maker.

Usage:
    mcp-maker init <source>     Generate an MCP server from a data source
    mcp-maker serve             Run the generated MCP server
    mcp-maker inspect <source>  Preview what would be generated (dry run)
    mcp-maker list-connectors   Show available connectors
    mcp-maker config            Generate Claude Desktop config
"""

import json
import os
import platform
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

    # Optional connectors — only load if dependencies available
    try:
        from .connectors import postgres  # noqa: F401
    except ImportError:
        pass

    try:
        from .connectors import mysql  # noqa: F401
    except ImportError:
        pass

    try:
        from .connectors import airtable  # noqa: F401
    except ImportError:
        pass

    try:
        from .connectors import gsheets  # noqa: F401
    except ImportError:
        pass

    try:
        from .connectors import notion  # noqa: F401
    except ImportError:
        pass


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
):
    """⚒️  Generate an MCP server from a data source.

    Examples:
        mcp-maker init sqlite:///my.db
        mcp-maker init ./data/
        mcp-maker init postgres://user:pass@localhost/mydb
        mcp-maker init sqlite:///my.db --read-write
        mcp-maker init sqlite:///my.db --tables users,orders
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

    # Print schema summary
    _print_schema_summary(schema)

    # Step 4: Generate server
    read_only = not read_write
    with console.status("[bold green]Generating MCP server..."):
        output_path = write_server(
            schema,
            output_dir=output,
            filename=filename,
            read_only=read_only,
        )

    console.print()
    console.print(f"  🎉 Generated: [bold green]{output_path}[/bold green]")
    if read_write:
        console.print("  📝 [yellow]Write operations enabled[/yellow] (INSERT, UPDATE, DELETE)")
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
    from .connectors.base import get_connector

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
    table.add_column("Status", style="yellow")

    examples = {
        "sqlite": "sqlite:///my_database.db",
        "files": "./data/",
        "postgres": "postgres://user:pass@localhost/mydb",
        "postgresql": "postgres://user:pass@localhost/mydb",
        "mysql": "mysql://user:pass@localhost/mydb",
    }

    # Always show all connectors, even if not installed
    all_connectors = {
        "sqlite": ("SQLiteConnector", True),
        "files": ("FileConnector", True),
        "postgres": ("PostgresConnector", "postgres" in _CONNECTOR_REGISTRY),
        "mysql": ("MySQLConnector", "mysql" in _CONNECTOR_REGISTRY),
        "airtable": ("AirtableConnector", "airtable" in _CONNECTOR_REGISTRY),
        "gsheet": ("GoogleSheetsConnector", "gsheet" in _CONNECTOR_REGISTRY),
        "notion": ("NotionConnector", "notion" in _CONNECTOR_REGISTRY),
    }

    for scheme, (cls_name, available) in all_connectors.items():
        example = examples.get(scheme, f"{scheme}://...")
        status = "✅ Installed" if available else "📦 pip install mcp-maker[" + scheme + "]"
        table.add_row(scheme, cls_name, example, status)

    console.print(table)
    console.print()


@app.command()
def bases():
    """🗂️  Discover Airtable bases accessible by your API key.

    Lists all Airtable bases visible to your AIRTABLE_API_KEY token.
    Use the base ID with: mcp-maker init airtable://BASE_ID

    Requires AIRTABLE_API_KEY environment variable.
    """
    console.print()
    console.print(
        Panel.fit("🗂️  [bold cyan]Airtable Base Discovery[/bold cyan]", subtitle="v" + __version__)
    )

    api_key = os.environ.get("AIRTABLE_API_KEY") or os.environ.get("AIRTABLE_TOKEN")
    if not api_key:
        console.print(
            "\n[red]Error:[/red] AIRTABLE_API_KEY environment variable not set.\n"
            "Set it with: [cyan]export AIRTABLE_API_KEY=pat_xxxxxxxxxxxx[/cyan]\n"
            "Get a token from: https://airtable.com/create/tokens\n"
        )
        raise typer.Exit(code=1)

    try:
        from pyairtable import Api
    except ImportError:
        console.print(
            "\n[red]Error:[/red] pyairtable not installed.\n"
            "Install with: [cyan]pip install mcp-maker[airtable][/cyan]\n"
        )
        raise typer.Exit(code=1)

    with console.status("[bold green]Fetching Airtable bases..."):
        try:
            api = Api(api_key)
            base_list = api.bases()
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise typer.Exit(code=1)

    if not base_list:
        console.print("\n  No bases found. Check your API key permissions.\n")
        return

    table = RichTable(title=f"📋 Accessible Bases ({len(base_list)})")
    table.add_column("Base ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Command", style="dim")

    for b in base_list:
        base_id = b.id
        base_name = b.name or "—"
        cmd = f"mcp-maker init airtable://{base_id}"
        table.add_row(base_id, base_name, cmd)

    console.print()
    console.print(table)
    console.print()
    console.print("  [dim]Run any command above to generate an MCP server for that base.[/dim]\n")


@app.command()
def config(
    server_file: str = typer.Option(
        "mcp_server.py",
        "--file", "-f",
        help="Path to the generated server file.",
    ),
    name: str = typer.Option(
        "my-data",
        "--name", "-n",
        help="Name for the MCP server in Claude Desktop config.",
    ),
    install: bool = typer.Option(
        False,
        "--install",
        help="Auto-write to Claude Desktop config file.",
    ),
):
    """🔧 Generate Claude Desktop configuration.

    Outputs the JSON config needed to connect your generated MCP server
    to Claude Desktop. Use --install to auto-write it.

    Examples:
        mcp-maker config
        mcp-maker config --name my-db --install
    """
    server_path = os.path.abspath(server_file)

    if not os.path.isfile(server_path):
        console.print(
            f"\n[red]Error:[/red] Server file not found: {server_file}\n"
            f"Run [cyan]mcp-maker init <source>[/cyan] first.\n"
        )
        raise typer.Exit(code=1)

    console.print()
    console.print(
        Panel.fit("🔧 [bold cyan]Claude Desktop Config[/bold cyan]", subtitle="v" + __version__)
    )

    server_config = {
        "command": sys.executable,
        "args": [server_path],
    }

    if install:
        config_path = _get_claude_config_path()
        if config_path is None:
            console.print(
                "\n[red]Error:[/red] Could not determine Claude Desktop config path.\n"
                "Please add the config manually.\n"
            )
            install = False
        else:
            # Read existing config or create new
            if os.path.isfile(config_path):
                with open(config_path, "r") as f:
                    try:
                        existing = json.load(f)
                    except json.JSONDecodeError:
                        existing = {}
            else:
                existing = {}

            if "mcpServers" not in existing:
                existing["mcpServers"] = {}

            existing["mcpServers"][name] = server_config

            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w") as f:
                json.dump(existing, f, indent=2)

            console.print(f"  ✅ Written to: [green]{config_path}[/green]")
            console.print(f"  📝 Server name: [cyan]{name}[/cyan]")
            console.print()
            console.print("  [bold yellow]Restart Claude Desktop[/bold yellow] to activate.\n")
            return

    # Just print the config
    snippet = {
        "mcpServers": {
            name: server_config,
        }
    }

    config_path = _get_claude_config_path()
    console.print()
    console.print(f"  Add this to your Claude Desktop config:")
    if config_path:
        console.print(f"  📁 [dim]{config_path}[/dim]")
    console.print()
    console.print_json(json.dumps(snippet, indent=2))
    console.print()
    console.print(f"  [dim]Or run [cyan]mcp-maker config --install[/cyan] to auto-write it.[/dim]\n")


def _get_claude_config_path() -> str | None:
    """Get the Claude Desktop config file path for the current OS."""
    system = platform.system()
    if system == "Darwin":  # macOS
        return os.path.expanduser(
            "~/Library/Application Support/Claude/claude_desktop_config.json"
        )
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return os.path.join(appdata, "Claude", "claude_desktop_config.json")
    elif system == "Linux":
        return os.path.expanduser(
            "~/.config/Claude/claude_desktop_config.json"
        )
    return None


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

