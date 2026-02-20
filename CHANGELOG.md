# Changelog

All notable changes to MCP-Maker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-02-21

### Added

- **CLI** with 4 commands: `init`, `inspect`, `serve`, `list-connectors`
- **SQLite connector**: inspects tables, columns, types, primary keys, and row counts
- **File connector**: CSV/JSON files → tables with type inference, text files → read-only resources
- **Code generator**: produces complete FastMCP server with 5 tools per table
  - `list_{table}(limit, offset)` — paginated listing
  - `get_{table}_by_{pk}(id)` — lookup by primary key
  - `search_{table}(query, limit)` — text search across string columns
  - `count_{table}()` — total row count
  - `schema_{table}()` — column names and types
- **Connector registry** pattern for easy community contributions
- **Rich terminal output** with tables, panels, and status spinners
- **24 unit tests** covering schema inspection, connectors, and code generation
- **GitHub Actions CI/CD**: tests on Python 3.10–3.12, auto-publish to PyPI on release

[0.1.0]: https://github.com/MrAliHasan/mcp-maker/releases/tag/v0.1.0
