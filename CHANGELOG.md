# Changelog

All notable changes to MCP-Maker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.2] - 2026-02-23

### Added
- **Pagination & Sorting**: All `list_` tools now return `{results, total, has_more, next_offset}` with `sort_field` and `sort_direction` params across every connector (SQL, NoSQL, Excel, Files, GSheets, Notion, Airtable, Supabase).
- **Field Selection**: `list_` tools accept `fields="col1,col2"` for column projection with SQL injection-safe whitelisting.
- **Date Range Filters**: Auto-detected date/datetime columns get `date_from` and `date_to` params on `list_` tools.
- **Foreign Key Discovery & Join Tools**: Auto-discovers FK relationships in SQLite, PostgreSQL, and MySQL. Generates `join_{from}_{to}()` tools for cross-table queries.
- **Batch Operations**: `batch_insert_{table}(records=[...])` and `batch_delete_{table}(ids=[...])` tools with transaction safety.
- **Export Tools**: `export_{table}_csv()` and `export_{table}_json()` for every table across all connectors.
- **Webhook Support**: Optional `--webhooks` flag generates `register_webhook_{table}()`, `list_webhooks_{table}()`, and `fire_webhooks_{table}()` tools.
- **Redis Pub/Sub**: `publish_message(channel, message)`, `channel_list(pattern)`, and `channel_subscribers(channel)` tools.
- **Multi-Source Initialization**: `mcp-maker init source1 source2 ...` merges schemas from multiple data sources into a single unified MCP server.
- **Async Templates**: `--async` flag generates `aiosqlite`-based async handlers for SQLite connectors.

### Changed
- **Connector Documentation**: All 11 connector docs updated with Advanced Features sections covering pagination, fields, date filters, batch, export, and join tools.
- **Test Coverage**: Boosted from 43% to 73% (244 tests) with comprehensive mock-based tests for Excel, MongoDB, Redis, Supabase, OpenAPI, MySQL, PostgreSQL, GSheets, Notion, Airtable connectors and CLI deploy/server/environment commands.
- **Lint Clean**: Resolved all 402 ruff lint errors (F401, F811, F841, E402).

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
