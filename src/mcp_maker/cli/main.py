import typer
from rich.console import Console

from mcp_maker import __version__

app = typer.Typer(
    name="mcp-maker",
    help="⚒️  Auto-generate MCP servers from any data source.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version and exit."
    ),
):
    """⚒️  MCP-Maker — Auto-generate MCP servers from any data source."""
    if version:
        console.print(f"mcp-maker version: [cyan]{__version__}[/cyan]")
        raise typer.Exit()
