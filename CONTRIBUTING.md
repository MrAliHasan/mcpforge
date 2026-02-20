# Contributing to MCP-Maker

Thank you for your interest in contributing! MCP-Maker is designed to make contributing easy — each **connector** is a self-contained Python file.

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/MrAliHasan/mcp-maker.git
cd mcp-maker

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## 🔌 Adding a New Connector

This is the #1 way to contribute. Each connector is a single file in `src/mcp_maker/connectors/`.

### Step 1: Create the Connector

Create `src/mcp_maker/connectors/your_connector.py`:

```python
"""
MCP-Maker YourDB Connector — Inspect YourDB databases.
"""

from .base import BaseConnector, register_connector
from ..core.schema import Column, ColumnType, DataSourceSchema, Table

class YourDBConnector(BaseConnector):
    """Connector for YourDB databases."""

    @property
    def source_type(self) -> str:
        return "yourdb"

    def validate(self) -> bool:
        """Check that the data source is accessible."""
        # Try connecting, raise ConnectionError if it fails
        return True

    def inspect(self) -> DataSourceSchema:
        """Inspect the data source and return its schema."""
        tables = []
        # Discover tables, columns, types, etc.
        return DataSourceSchema(
            source_type="yourdb",
            source_uri=self.uri,
            tables=tables,
        )

# Register this connector
register_connector("yourdb", YourDBConnector)
```

### Step 2: Register in `__init__.py`

Add the import to `src/mcp_maker/connectors/__init__.py`:

```python
from .your_connector import YourDBConnector
```

### Step 3: Add Lazy Loading in CLI

Add the import to `cli.py`'s `_load_connectors()` function:

```python
from .connectors import your_connector  # noqa: F401
```

### Step 4: Write Tests

Add tests to `tests/test_mcpforge.py` or create a new test file.

### Step 5: Submit PR

- Reference `connectors/sqlite.py` as a model implementation
- Include a brief example in your PR description
- Make sure all tests pass

## 📝 Other Contributions

Besides connectors, we welcome:

- **Bug fixes** — open an issue first if it's non-trivial
- **Documentation** — README improvements, examples, tutorials
- **Template enhancements** — improving the generated server code
- **New CLI features** — additional commands or options

## 🧪 Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run a specific test class
pytest tests/test_mcpforge.py::TestSQLiteConnector -v
```

## 📐 Code Style

- Use type hints for all function parameters and return values
- Add docstrings to all public functions and classes
- Follow the existing code patterns (dataclasses for data, ABC for interfaces)
- Keep connectors self-contained — each one should be a single file

## 🐛 Reporting Issues

When reporting bugs, please include:

1. Python version (`python --version`)
2. MCP-Maker version (`pip show mcp-maker`)
3. The command you ran
4. The full error traceback
5. Your data source type (SQLite, CSV, etc.)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
