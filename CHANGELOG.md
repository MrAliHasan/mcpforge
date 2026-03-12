# Changelog

All notable changes to MCP-Maker will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.5] - 2026-03-13

### Fixed
- **Critical: Insert function parameter ordering** — Schemas with nullable columns before non-nullable columns (e.g., foreign keys before `NOT NULL` fields) caused `SyntaxError: parameter without a default follows parameter with a default` in generated server code. Fixed across all 6 SQL templates (SQLite, PostgreSQL, MySQL + async variants) by sorting required parameters before optional ones.
- **Codecov CI integration** — Added `CODECOV_TOKEN` secret and upgraded to `codecov-action@v5`.

## [0.2.4] - 2026-03-13

### Security
- **SQL Injection Prevention**: Added column whitelist validation (`_KNOWN_COLUMNS` + `_validate_column`) in consolidated-mode tools across SQLite, PostgreSQL, and MySQL templates.
- **Credential Hardening**: Removed hardcoded `DB_PATH` fallback in SQLite template; now raises `RuntimeError` if `DATABASE_URL` is unset.
- **API Key Authentication**: Auth wrapper now validates a client-provided `api_key` parameter against `MCP_API_KEY` environment variable, replacing the previous no-op check.
- **Token Leak Prevention**: HubSpot connector now sanitizes URIs in error messages to prevent API token exposure.
- **Batch Input Sanitization**: All `batch_insert_` tools now validate column names against schema whitelist before SQL interpolation.

### Fixed
- **Connection Leaks**: PostgreSQL cursor cleanup moved to `finally` blocks. SQLite connections now registered with `atexit` handler for shutdown cleanup.
- **Batch Size Limits**: Batch insert/delete operations capped at 1,000 records to prevent resource exhaustion.
- **CLI Flag Conflict**: Warning now emitted when both `--read-write` and `--ops` flags are provided.
- **Mixed Source Types**: Multi-source `init` now supports mixing source types (e.g., SQLite + MongoDB) with a warning instead of rejecting.
- **.env Parser**: Now correctly handles `export` prefix and strips inline `#` comments from unquoted values.
- **Connector Registration**: Added missing optional connectors (Excel, MongoDB, Supabase, OpenAPI, Redis) to `connectors/__init__.py`.
- **Connector Loading**: Improved error handling to distinguish missing third-party dependencies from internal import errors.

### Changed
- **Project Status**: Upgraded from Alpha to Beta (`Development Status :: 4 - Beta`).
- **Architecture**: Extracted `cli/connectors_loader.py` and `cli/schema_ops.py` from `generator.py`, reducing it from 626 to 512 lines.
- **Connector Naming**: Renamed `redis_connector.py` to `redis.py` for consistency with all other connectors.
- **Test Organization**: Moved `test_cloud_inspect.py` and `test_sql_inspect.py` to `tests/core/`. Renamed `test_env_extended.py` to `test_env_edge_cases.py`. Added `conftest.py` and `__init__.py` to all test subdirectories.
- **Documentation**: Deleted root-level `DOCS.md` in favor of `docs/reference.md`. Expanded `docs/hubspot.md` from 95 to 250+ lines.
- **CI/CD**: Added Codecov upload, coverage badge, `ruff` and `mypy` configuration in `pyproject.toml`.
- **Repository Hygiene**: Removed tracked generated files and test artifacts from git.

### Added
- **SECURITY.md**: Vulnerability reporting policy with 48-hour response SLA.
- **CODE_OF_CONDUCT.md**: Contributor Covenant v2.1.
- **Makefile**: Standard `make test`, `make lint`, `make fmt`, `make clean` targets.
- **Test Coverage**: 272 tests passing (up from 256), including 22 new regression tests for security and correctness fixes.

## [0.2.3] - 2026-02-23

### Added
- **HubSpot Data-Bridge**: Natively connects to HubSpot CRM using Private App Tokens (`hubspot://pat=YOUR_TOKEN`).
- **Deep Auto-Discovery**: Automatically traverses and introspects all Custom Properties for Contacts, Companies, Deals, Tickets, Products, Quotes, Notes, Tasks, Meetings, Emails, Calls, and any defined Custom Objects natively.
- **Context Maximization**: Advanced Jinja generation intelligently maps human names (`hubspot_get_owners`), sales stages (`hubspot_get_deal_pipelines`), and audience segments (`hubspot_get_lists`).
- **Compound Tools**: Advanced tools like `hubspot_search_crm_objects` and `batch_upsert_{table}` created for efficient data-syncing natively.

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
