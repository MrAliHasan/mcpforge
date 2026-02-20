"""
MCPForge File Connector — Inspect CSV, JSON, and other file-based data sources.
"""

import csv
import json
import os
from pathlib import Path
from typing import List

from .base import BaseConnector, register_connector
from ..core.schema import (
    Column,
    ColumnType,
    DataSourceSchema,
    Resource,
    Table,
)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".csv": "text/csv",
    ".json": "application/json",
    ".jsonl": "application/jsonl",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".xml": "text/xml",
}


def _infer_type(value) -> ColumnType:
    """Infer the column type from a Python value."""
    if value is None:
        return ColumnType.STRING
    if isinstance(value, bool):
        return ColumnType.BOOLEAN
    if isinstance(value, int):
        return ColumnType.INTEGER
    if isinstance(value, float):
        return ColumnType.FLOAT
    if isinstance(value, dict):
        return ColumnType.JSON
    if isinstance(value, list):
        return ColumnType.JSON
    return ColumnType.STRING


def _inspect_csv(filepath: str) -> Table:
    """Inspect a CSV file and return its schema as a Table."""
    name = Path(filepath).stem

    with open(filepath, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []

        # Read a sample to infer types
        sample_rows = []
        for i, row in enumerate(reader):
            sample_rows.append(row)
            if i >= 99:  # Sample first 100 rows
                break

        # Count total rows
        f.seek(0)
        row_count = sum(1 for _ in f) - 1  # subtract header

    columns = []
    for field_name in fieldnames:
        # Infer type from sample values
        sample_values = [
            row.get(field_name, "") for row in sample_rows
            if row.get(field_name, "") != ""
        ]
        if sample_values:
            # Try int, then float, then string
            try:
                [int(v) for v in sample_values[:10]]
                col_type = ColumnType.INTEGER
            except (ValueError, TypeError):
                try:
                    [float(v) for v in sample_values[:10]]
                    col_type = ColumnType.FLOAT
                except (ValueError, TypeError):
                    if all(v.lower() in ("true", "false") for v in sample_values[:10]):
                        col_type = ColumnType.BOOLEAN
                    else:
                        col_type = ColumnType.STRING
        else:
            col_type = ColumnType.STRING

        columns.append(Column(name=field_name, type=col_type))

    # Set first column as primary key if it looks like an ID
    if columns and columns[0].name.lower() in ("id", "uuid", "key", "_id"):
        columns[0].primary_key = True

    return Table(name=name, columns=columns, row_count=row_count)


def _inspect_json(filepath: str) -> Table:
    """Inspect a JSON file and return its schema as a Table."""
    name = Path(filepath).stem

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both array of objects and single object
    if isinstance(data, list) and data and isinstance(data[0], dict):
        records = data
    elif isinstance(data, dict):
        records = [data]
    else:
        # Not a structured dataset — treat as a resource instead
        return None

    # Infer columns from all records (union of keys)
    all_keys = {}
    for record in records[:100]:  # Sample first 100
        for key, value in record.items():
            if key not in all_keys:
                all_keys[key] = _infer_type(value)

    columns = [
        Column(name=key, type=col_type)
        for key, col_type in all_keys.items()
    ]

    # Set first column as primary key if it looks like an ID
    if columns and columns[0].name.lower() in ("id", "uuid", "key", "_id"):
        columns[0].primary_key = True

    return Table(
        name=name,
        columns=columns,
        row_count=len(records) if isinstance(data, list) else 1,
    )


class FileConnector(BaseConnector):
    """Connector for file-based data sources (CSV, JSON, etc.).

    Inspects all supported files in a directory and generates:
    - Tables for structured data (CSV, JSON arrays)
    - Resources for unstructured data (text, markdown, etc.)

    URI format: A directory path (e.g., ./data/)
    """

    @property
    def source_type(self) -> str:
        return "files"

    def validate(self) -> bool:
        """Check that the directory exists and contains supported files."""
        path = os.path.expanduser(self.uri)
        if not os.path.isdir(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        # Check for at least one supported file
        for f in os.listdir(path):
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                return True
        raise ValueError(
            f"No supported files found in {path}. "
            f"Supported: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )

    def inspect(self) -> DataSourceSchema:
        """Inspect all files in the directory and return the schema."""
        dir_path = os.path.expanduser(self.uri)
        tables: List[Table] = []
        resources: List[Resource] = []

        for filename in sorted(os.listdir(dir_path)):
            filepath = os.path.join(dir_path, filename)
            if not os.path.isfile(filepath):
                continue

            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            mime_type = SUPPORTED_EXTENSIONS[ext]

            try:
                if ext == ".csv":
                    table = _inspect_csv(filepath)
                    if table:
                        tables.append(table)
                elif ext in (".json", ".jsonl"):
                    table = _inspect_json(filepath)
                    if table:
                        tables.append(table)
                    else:
                        resources.append(Resource(
                            name=Path(filename).stem,
                            uri=filepath,
                            mime_type=mime_type,
                        ))
                else:
                    # Text-based files become resources
                    resources.append(Resource(
                        name=Path(filename).stem,
                        uri=filepath,
                        mime_type=mime_type,
                    ))
            except Exception:
                # If a file can't be inspected, add as resource
                resources.append(Resource(
                    name=Path(filename).stem,
                    uri=filepath,
                    mime_type=mime_type,
                    description=f"Could not inspect: {filename}",
                ))

        return DataSourceSchema(
            source_type="files",
            source_uri=dir_path,
            tables=tables,
            resources=resources,
            metadata={"file_count": len(tables) + len(resources)},
        )


# Register this connector
register_connector("files", FileConnector)
