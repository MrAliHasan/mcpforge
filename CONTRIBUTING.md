# Contributing to MCP-Maker

Thank you for your interest in contributing! MCP-Maker is designed to make contributing easy — each **connector** is a self-contained Python file.

## 🚀 Quick Start (Git Workflow)

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:

```bash
git clone https://github.com/YOUR_USERNAME/mcp-maker.git
cd mcp-maker
```

3. **Create a branch** for your feature or fix:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bugfix-name
```

4. **Set up your environment**:

```bash
# Create a virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev,all]"
```

5. **Run tests** to ensure you're starting clean:

```bash
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

Add your connector to `src/mcp_maker/cli/generator.py`'s `_load_connectors()` function:

```python
    _try_load("yourdb")
```

### Step 4: Write Tests

Create a new test file for your connector in `tests/connectors/test_yourdb.py`.

### Step 5: Submit Pull Request

1. **Commit your changes**: `git commit -m "feat: Add YourDB connector"`
2. **Push to your fork**: `git push origin feature/your-feature-name`
3. **Open a PR** against the `main` branch of `MrAliHasan/mcp-maker`.

- Reference `connectors/sqlite.py` as a model implementation
- Include a brief example in your PR description
- Make sure all `pytest` checks pass

## 📝 Other Contributions

Besides connectors, we welcome:

- **Bug fixes** — open an issue first if it's non-trivial
- **Documentation** — README improvements, examples, tutorials
- **Template enhancements** — improving the generated server code
- **New CLI features** — additional commands or options

## 🧪 Running Tests

```bash
# Using Make (recommended)
make test          # Run all tests
make lint          # Run linter
make check         # Run lint + tests

# Or directly
pytest tests/ -v
ruff check src/ tests/
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
