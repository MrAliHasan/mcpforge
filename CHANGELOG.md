# Changelog

All notable changes to MCP-Maker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.1] - 2026-02-23

### Added
- **Granular Security (`--ops`)**: Control exactly what the LLM can edit with precise `--ops read,insert,update,delete` arrays. 100% template-native conditional compilation.
- **Cloud API Rate Limiting**: Extensively upgraded the `server.py.jinja2` generation engine to auto-inject a `TokenBucketRateLimiter` securing Cloud endpoints (Notion, Airtable, Sheets) against `429 Too Many Requests` bans.
- **Google Sheets Connector**: Direct integration with `gsheets://URL` endpoints. Generates `update_cell` tools.
- **Notion Connector**: Supports Multi-Database URIs natively, handles cursor pagination, auto-parses 20+ Notion property types.
- **E2E Test Framework**: Deployed a dynamic End-to-End server generation and mock execution testing pipeline in `tests/e2e`.

### Changed
- **Massive Architectural Refactor**: Obliterated monolithic dependencies. `cli.py` and `test_mcpforge.py` bisected gracefully into modular domain packages.
- **Test Integrity**: Test suite significantly expanded (88 passing regression checks).
- Re-architected Open Source Documentation (`CONTRIBUTING.md`) for streamlined Fork/Branch/PR Git workflows.

## [0.2.0] - 2026-02-21

### Added
- **PostgreSQL Connector**: Fully typed extraction for postgres schema inspection.
- **MySQL Connector**: Queue-based connection pools supporting `mysql://`.
- **Airtable Connector**: Auto-generation of formula-based queries and Base Discovery via `mcp-maker bases`.
- **Semantic Search**: Vector database integrations explicitly enabled via `--semantic`.

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
