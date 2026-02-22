
import json
import os
import subprocess
import sys
import platform

import typer
from rich.console import Console
from rich.table import Table as RichTable
from rich.panel import Panel

from mcp_maker import __version__
from mcp_maker.core.schema import DataSourceSchema
from mcp_maker.connectors.base import get_connector, register_connector
from mcp_maker.core.generator import generate_server_code, write_server
from .main import app, console


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
    from .generator import _load_connectors
    _load_connectors()
    from mcp_maker.connectors.base import _CONNECTOR_REGISTRY

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
