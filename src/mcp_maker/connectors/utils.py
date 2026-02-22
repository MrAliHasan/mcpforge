"""
Shared utility functions for MCP-Maker connectors.
"""

import re
from mcp_maker.core.schema import ColumnType


def sanitize_name(name: str) -> str:
    """Convert an arbitrary string into a valid Python identifier.

    Used by Airtable, Google Sheets, and Notion connectors to convert
    their field/property names into safe Python identifiers.

    Examples:
        >>> sanitize_name("First Name")
        'first_name'
        >>> sanitize_name("123-count")
        '_123_count'
        >>> sanitize_name("email@address")
        'email_address'
    """
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_").lower()
    if not name:
        return "_unnamed"
    if name[0].isdigit():
        name = "_" + name
    return name


def infer_type(value) -> ColumnType:
    """Infer a ColumnType from a Python value.

    Used by File and Google Sheets connectors to infer column types
    from sample data values.

    Args:
        value: A sample value from the data source.

    Returns:
        The inferred ColumnType.
    """
    if value is None:
        return ColumnType.UNKNOWN
    if isinstance(value, bool):
        return ColumnType.BOOLEAN
    if isinstance(value, int):
        return ColumnType.INTEGER
    if isinstance(value, float):
        return ColumnType.FLOAT
    s = str(value).strip().lower()
    if s in ("true", "false"):
        return ColumnType.BOOLEAN
    try:
        int(s)
        return ColumnType.INTEGER
    except (ValueError, TypeError):
        pass
    try:
        float(s)
        return ColumnType.FLOAT
    except (ValueError, TypeError):
        pass
    return ColumnType.STRING
