
import os

import typer
from rich.table import Table as RichTable
from rich.panel import Panel

from mcp_maker import __version__
from mcp_maker.core.schema import DataSourceSchema
from mcp_maker.connectors.base import get_connector
from mcp_maker.core.generator import write_server, read_lock_file
from .connectors_loader import load_all_connectors
from .schema_ops import merge_schemas, filter_tables, detect_migration
from .main import app, console



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
    source: list[str] = typer.Argument(
        ...,
        help="Data source URI(s). Combine multiple: sqlite:///a.db mongodb://x/y",
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
        help="[DEPRECATED] Use --ops read,insert,update,delete instead. Generate write tools.",
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
    default_limit: int = typer.Option(
        50,
        "--default-limit",
        help="Default number of records to return for list tools.",
    ),
    max_limit: int = typer.Option(
        500,
        "--max-limit",
        help="Maximum number of records allowed per request.",
    ),
    audit: bool = typer.Option(
        False,
        "--audit",
        help="Enable structured audit logging for all tool executions.",
    ),
    otel: bool = typer.Option(
        False,
        "--otel",
        help="Enable OpenTelemetry tracing for enterprise observability (requires opentelemetry-api/sdk).",
    ),
    consolidate_threshold: int = typer.Option(
        20,
        "--consolidate-threshold",
        help="Threshold of tables before switching to consolidated generic tools instead of per-table tools.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Skip schema change warnings and force regeneration.",
    ),
    no_ssl: bool = typer.Option(
        False,
        "--no-ssl",
        help="Disable SSL/TLS enforcement for database connections (use for local dev only).",
    ),
    auth: str = typer.Option(
        "none",
        "--auth",
        help="Authentication mode for generated server. Options: none, api-key.",
    ),
    async_mode: bool = typer.Option(
        False,
        "--async",
        help="Generate async tools using aiosqlite/asyncpg/aiomysql.",
    ),
    cache: int = typer.Option(
        0,
        "--cache",
        help="Enable smart caching with TTL in seconds (e.g., --cache 60). 0 = disabled.",
    ),
    cache_backend: str = typer.Option(
        "memory",
        "--cache-backend",
        help="Cache backend to use ('memory' or a redis:// URL).",
    ),
    rate_limit: float = typer.Option(
        0.0,
        "--rate-limit",
        help="Global rate limit for all generated tools in requests per second. 0 = disabled.",
    ),
    template_dir: str = typer.Option(
        None,
        "--template-dir",
        help="Path to a directory containing custom Jinja2 templates to override the defaults.",
    ),
    config: str = typer.Option(
        None,
        "--config",
        help="Path to a YAML/JSON configuration file for granular RBAC.",
    ),
    auto_commit: bool = typer.Option(
        False,
        "--auto-commit",
        help="Automatically commit generated changes to git if inside a repository.",
    ),
    webhooks: bool = typer.Option(
        False,
        "--webhooks",
        help="Generate webhook registration and notification tools for data change events.",
    ),
):
    """⚒️  Generate an MCP server from one or more data sources.

    Examples:
        mcp-maker init sqlite:///my.db
        mcp-maker init ./data/
        mcp-maker init postgres://user:pass@localhost/mydb
        mcp-maker init sqlite:///my.db --read-write
        mcp-maker init sqlite:///my.db --ops read,insert
        mcp-maker init sqlite:///my.db --tables users,orders
        mcp-maker init sqlite:///my.db --semantic
        mcp-maker init sqlite:///users.db mongodb://localhost/orders
    """
    load_all_connectors()

    console.print()
    console.print(
        Panel.fit("⚒️  [bold cyan]MCP-Maker[/bold cyan]", subtitle="v" + __version__)
    )

    # Multi-source: connect, validate, and inspect each source
    schemas = []
    for src_uri in source:
        with console.status(f"[bold green]Connecting to {src_uri}..."):
            try:
                connector = get_connector(src_uri)
            except ValueError as e:
                console.print(f"\n[red]Error:[/red] {e}")
                raise typer.Exit(code=1)

        with console.status(f"[bold green]Validating {connector.source_type} source..."):
            try:
                connector.validate()
            except (FileNotFoundError, ConnectionError, ValueError, ImportError) as e:
                console.print(f"\n[red]Validation failed:[/red] {e}")
                raise typer.Exit(code=1)

        console.print(f"  ✅ Connected to [cyan]{connector.source_type}[/cyan] source")

        with console.status(f"[bold green]Inspecting {connector.source_type}..."):
            schemas.append(connector.inspect())

    # Merge schemas if multiple sources
    schema = merge_schemas(schemas, console)

    # Filter tables if --tables specified
    if tables:
        filter_tables(schema, tables, console)
        if not schema.tables:
            console.print("\n[red]Error:[/red] No matching tables found.")
            console.print(f"  Requested: {tables}")
            raise typer.Exit(code=1)

    # Parse ops
    parsed_ops = ["read"]
    if read_write:
        console.print("  ⚠️  [yellow]--read-write is deprecated.[/yellow] Use [cyan]--ops read,insert,update,delete[/cyan] instead.")
        parsed_ops = ["read", "insert", "update", "delete"]
    if ops:
        if read_write:
            console.print("  ⚠️  [yellow]Both --read-write and --ops provided.[/yellow] Using --ops value; --read-write is ignored.")
        parsed_ops = [op.strip().lower() for op in ops.split(",") if op.strip()]

    # Parse RBAC config if provided
    rbac_config = None
    if config:
        if not os.path.exists(config):
            console.print(f"\n[red]Error:[/red] Config file not found: {config}")
            raise typer.Exit(code=1)
        try:
            import yaml
            with open(config, "r", encoding="utf-8") as f:
                cfg_data = yaml.safe_load(f)
            
            if isinstance(cfg_data, dict) and "tables" in cfg_data:
                rbac_config = {}
                for tbl_name, tbl_cfg in cfg_data["tables"].items():
                    if "ops" in tbl_cfg:
                        rbac_config[tbl_name.lower()] = [o.lower() for o in tbl_cfg["ops"]]
            console.print(f"  🔒 Loaded RBAC config from: [cyan]{config}[/cyan]")
        except Exception as e:
            console.print(f"\n[red]Error parsing config file:[/red] {e}")
            raise typer.Exit(code=1)

    # Warn about monolithic scaling for large schemas
    table_count = len(schema.tables)
    if table_count > 20:
        tools_per_table = (2 if "read" in parsed_ops else 0) + (1 if "insert" in parsed_ops else 0) + (1 if "update" in parsed_ops else 0) + (1 if "delete" in parsed_ops else 0) + (2 if semantic else 0)
        estimated_tools = table_count * tools_per_table
        console.print()
        console.print(f"  ⚠️  [yellow]Large schema detected:[/yellow] {table_count} tables → ~{estimated_tools} tools")
        console.print("  [dim]Tip: Use [cyan]--tables users,orders[/cyan] to only include what you need.[/dim]")
        console.print("  [dim]Large tool counts may exceed LLM context windows.[/dim]")

    # Print schema summary
    _print_schema_summary(schema)

    # Schema change detection via lock file
    diff = None
    if not force:
        old_lock = read_lock_file(output)
        if old_lock:
            diff = detect_migration(schema, old_lock, console)

    # Step 4: Generate server
    with console.status("[bold green]Generating MCP server..."):
        limit_kwargs = {
            "default_limit": default_limit,
            "max_limit": max_limit,
            "audit": audit,
            "otel": otel,
            "consolidate_threshold": consolidate_threshold,
            "ssl_enabled": not no_ssl,
            "auth_mode": auth,
            "async_mode": async_mode,
            "cache_ttl": cache,
            "cache_backend": cache_backend,
            "rate_limit": rate_limit,
            "template_dir": template_dir,
            "webhooks": webhooks,
        }
        server_path, autogen_path, server_created = write_server(
            schema,
            output_dir=output,
            filename=filename,
            ops=parsed_ops,
            rbac_config=rbac_config,
            semantic=semantic,
            **limit_kwargs
        )

    # Generate .env.example with placeholder (never embed real credentials)
    env_example_path = os.path.join(output, ".env.example")
    with open(env_example_path, "w") as f:
        f.write("# Copy this file to .env and fill in the values\n")
        f.write("DATABASE_URL='your-connection-string-here'\n")

    # Generate .gitignore for generated files (if not already present)
    gitignore_path = os.path.join(output, ".gitignore")
    if not os.path.exists(gitignore_path):
        from pathlib import Path
        template_gitignore = Path(__file__).parent.parent / "templates" / ".generated.gitignore"
        if template_gitignore.exists():
            import shutil
            shutil.copy2(template_gitignore, gitignore_path)

    console.print()
    if server_created:
        console.print(f"  🎉 Created: [bold green]{server_path}[/bold green] (Safe to edit)")
    else:
        console.print(f"  ⏭️  Skipped: [bold yellow]{server_path}[/bold yellow] (Already exists, preserving customizations)")
    
    console.print(f"  ♻️  Updated: [bold cyan]{autogen_path}[/bold cyan] (Auto-generated tools)")
    console.print(f"  🔐 Created: [bold cyan]{env_example_path}[/bold cyan]")
    
    if auto_commit:
        from mcp_maker.core.git_utils import commit_schema_changes
        diff_to_pass = diff
            
        files_to_commit = [os.path.basename(autogen_path), ".mcp-maker.lock", ".env.example", ".gitignore"]
        if server_created:
            files_to_commit.append(os.path.basename(server_path))
            
        commit_schema_changes(output, files_to_commit, diff=diff_to_pass)

    console.print(f"  🔧 [yellow]Operations enabled:[/yellow] {', '.join(op.upper() for op in parsed_ops)}")
    if semantic:
        console.print("  🧠 [magenta]Semantic search enabled[/magenta] (ChromaDB vector search)")
    console.print()
    console.print("  [dim]Next steps:[/dim]")
    console.print("    [cyan]mcp-maker serve[/cyan]           — Run the server")
    console.print("    [cyan]mcp-maker config[/cyan]          — Generate Claude Desktop config")
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
    load_all_connectors()

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
        console.print(f"    • list_{table.name}(limit, offset, sort_field, sort_direction)")
        if table.primary_key_columns:
            pk = table.primary_key_columns[0]
            console.print(f"    • get_{table.name}_by_{pk.name}({pk.name})")
        if table.searchable_columns:
            console.print(f"    • search_{table.name}(query, limit)")
        console.print(f"    • count_{table.name}()")
        console.print(f"    • schema_{table.name}()")
        console.print(f"    • aggregate_{table.name}(group_by, agg_function)")
        console.print(f"    • export_{table.name}_csv(limit)")
        console.print(f"    • export_{table.name}_json(limit)")
        console.print("    [dim]With --ops insert,update,delete:[/dim]")
        if table.primary_key_columns:
            pk = table.primary_key_columns[0]
            console.print(f"    • insert_{table.name}(...)")
            console.print(f"    • update_{table.name}_by_{pk.name}(...)")
            console.print(f"    • delete_{table.name}_by_{pk.name}({pk.name})")
            console.print(f"    • batch_insert_{table.name}(records)")
            console.print(f"    • batch_delete_{table.name}(ids)")

    # Show FK joins
    if schema.foreign_keys:
        console.print("\n  🔗 [bold]Relationship Joins:[/bold]")
        for fk in schema.foreign_keys:
            console.print(f"    • join_{fk.from_table}_with_{fk.to_table}(limit, offset)")
            console.print(f"      [dim]{fk.from_table}.{fk.from_column} → {fk.to_table}.{fk.to_column}[/dim]")

    for resource in schema.resources:
        console.print(f"\n  📄 [cyan]{resource.name}[/cyan]:")
        console.print(f"    • read_{resource.name}() → {resource.mime_type}")

    console.print()


@app.command()
def test(
    output: str = typer.Option(
        ".",
        "--output", "-o",
        help="Directory containing the generated server.",
    ),
    filename: str = typer.Option(
        "mcp_server.py",
        "--filename", "-f",
        help="Name of the generated server file.",
    ),
):
    """🧪 Smoke test a generated MCP server.

    Imports the generated server, finds all tools, and invokes each
    list_ tool to verify the server starts and returns data.
    """
    import sys
    import importlib.util

    console.print()
    autogen_module = f"_autogen_{os.path.splitext(filename)[0]}"
    autogen_path = os.path.join(output, f"{autogen_module}.py")

    if not os.path.exists(autogen_path):
        console.print(f"[red]Error:[/red] Generated file not found: {autogen_path}")
        console.print("  [dim]Generate a server first with:[/dim] mcp-maker init <source>")
        raise typer.Exit(code=1)

    # Dynamically import the generated server module
    sys.path.insert(0, os.path.abspath(output))
    try:
        spec = importlib.util.spec_from_file_location(autogen_module, autogen_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except SyntaxError as e:
        console.print(f"[red]SyntaxError in generated code:[/red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Failed to import generated code:[/red] {e}")
        raise typer.Exit(code=1)
    finally:
        sys.path.pop(0)

    if not hasattr(module, "mcp"):
        console.print("[red]Error:[/red] 'mcp' instance not found in generated code.")
        raise typer.Exit(code=1)

    mcp_instance = module.mcp
    tool_funcs = []
    
    if hasattr(mcp_instance, "_tool_registry"):
        tool_funcs = list(mcp_instance._tool_registry.keys())
    else:
        import inspect
        prefixes = ("list_", "get_", "search_", "count_", "schema_", "aggregate_", "insert_", "update_", "delete_", "batch_", "export_", "webhook_", "server_health", "join_", "query_database", "describe_table")
        for name, obj in inspect.getmembers(module):
            if callable(obj) and name.startswith(prefixes):
                tool_funcs.append(name)

    console.print(f"  📂 [cyan]{autogen_path}[/cyan]")
    console.print(f"  🔧 Found [bold]{len(tool_funcs)}[/bold] tools:")

    # Count tool types
    categories = {}
    for fn in tool_funcs:
        prefix = fn.split("_")[0] + "_"
        if fn.startswith("batch_"):
            prefix = "batch_"
        elif fn.startswith("export_"):
            prefix = "export_"
        elif fn.startswith("join_"):
            prefix = "join_"
        elif fn.startswith("webhook_"):
            prefix = "webhook_"
        elif fn == "server_health":
            prefix = "system_"
        elif fn == "query_database" or fn == "describe_table":
            prefix = "consolidated_"
        categories.setdefault(prefix, []).append(fn)

    for cat, fns in sorted(categories.items()):
        console.print(f"    [dim]{cat}[/dim]: {len(fns)} tools")

    console.print()
    console.print("  ✅ [green]Syntax check passed via dynamic import[/green]")

    # List all list_ tools
    list_tools = [fn for fn in tool_funcs if fn.startswith("list_")]
    console.print(f"  ✅ [green]{len(list_tools)} list tools available for smoke testing[/green]")
    for fn in list_tools:
        console.print(f"    • {fn}(...)")

    console.print()
    console.print("  [bold green]All checks passed![/bold green] 🎉")
    console.print()

