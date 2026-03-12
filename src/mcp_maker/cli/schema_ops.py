"""Schema operations: merging multi-source schemas, filtering, and migration detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.table import Table as RichTable

from mcp_maker.core.schema import DataSourceSchema

if TYPE_CHECKING:
    from rich.console import Console


def merge_schemas(schemas: list[DataSourceSchema], console: Console) -> DataSourceSchema:
    """Merge multiple inspected schemas into a single combined schema.

    Uses the first schema's source_type as the primary type for
    template selection.
    """
    if len(schemas) == 1:
        return schemas[0]

    console.print(f"\n  🔗 [bold]Merging {len(schemas)} data sources into one server[/bold]")

    merged_tables = []
    merged_resources = []
    merged_fks = []
    merged_metadata = {}
    source_types = []

    for s in schemas:
        merged_tables.extend(s.tables)
        merged_resources.extend(s.resources)
        merged_fks.extend(s.foreign_keys)
        merged_metadata[s.source_type] = s.metadata
        source_types.append(s.source_type)

    schema = DataSourceSchema(
        source_type=schemas[0].source_type,
        source_uri=" + ".join(s.source_uri for s in schemas),
        tables=merged_tables,
        resources=merged_resources,
        foreign_keys=merged_fks,
        metadata={
            "multi_source": True,
            "source_types": source_types,
            "sources": merged_metadata,
        },
    )

    for st in source_types:
        console.print(f"    • {st}: {sum(1 for s in schemas if s.source_type == st)} source(s)")

    unique_types = set(source_types)
    if len(unique_types) > 1:
        console.print(f"  ⚠️  [yellow]Mixed source types:[/yellow] {', '.join(sorted(unique_types))}")
        console.print("  [dim]Combined schema will use the first source type for code generation.[/dim]")

    return schema


def filter_tables(schema: DataSourceSchema, tables_csv: str, console: Console) -> None:
    """Filter schema tables by a comma-separated list of names (in-place)."""
    wanted = {t.strip().lower() for t in tables_csv.split(",") if t.strip()}
    before_count = len(schema.tables)
    schema.tables = [t for t in schema.tables if t.name.lower() in wanted]
    skipped = before_count - len(schema.tables)
    if skipped > 0:
        console.print(
            f"  📋 Filtered: keeping {len(schema.tables)} of {before_count} tables ({skipped} skipped)"
        )


def detect_migration(
    schema: DataSourceSchema,
    old_lock: dict,
    console: Console,
) -> dict | None:
    """Compare the current schema against a lock file and display migration diff.

    Returns the diff dict or None if no changes detected.
    """
    old_hash = old_lock.get("schema_hash", "")
    new_hash = schema.schema_hash
    if old_hash == new_hash:
        return None

    diff = DataSourceSchema.schema_diff(
        old_lock.get("tables", []),
        schema.table_names,
        old_columns=old_lock.get("columns"),
        new_columns=schema.column_fingerprint,
    )

    console.print()
    console.print("  ⚠️  [yellow]Schema migration detected — auto-updating tools[/yellow]")

    migration_table = RichTable(title="📋 Schema Migration Summary", show_lines=True)
    migration_table.add_column("Change", style="bold")
    migration_table.add_column("Details")

    if diff["added"]:
        migration_table.add_row("[green]+ Added Tables[/green]", ", ".join(diff["added"]))
    if diff["removed"]:
        migration_table.add_row("[red]- Removed Tables[/red]", ", ".join(diff["removed"]))
    for tbl, changes in diff.get("column_changes", {}).items():
        parts = []
        if changes.get("added"):
            parts.append(f"[green]+{', '.join(changes['added'])}[/green]")
        if changes.get("removed"):
            parts.append(f"[red]-{', '.join(changes['removed'])}[/red]")
        if changes.get("type_changed"):
            parts.append(f"[yellow]~{', '.join(changes['type_changed'])}[/yellow]")
        migration_table.add_row(f"↻ {tbl}", " | ".join(parts))

    if diff["added"] or diff["removed"] or diff.get("column_changes"):
        console.print()
        console.print(migration_table)
    else:
        console.print("  [dim]  Primary key or ordering changes detected.[/dim]")

    console.print("  [green]✅ Tools will be regenerated with the new schema.[/green]")
    return diff
