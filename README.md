# ⚒️ MCP-Maker

[![PyPI version](https://img.shields.io/pypi/v/mcp-maker.svg)](https://pypi.org/project/mcp-maker/)
[![Python 3.10+](https://img.shields.io/pypi/pyversions/mcp-maker.svg)](https://pypi.org/project/mcp-maker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/MrAliHasan/mcp-maker/blob/main/LICENSE)

**Auto-generate MCP servers from any data source. Zero code required.**

Point MCP-Maker at a database, spreadsheet, or directory and get a fully functional [MCP](https://modelcontextprotocol.io/) server in seconds — ready for Claude, ChatGPT, Cursor, and any MCP-compatible AI.

> **Note:** MCP-Maker is built on top of the official [MCP Python SDK](https://pypi.org/project/mcp/) (`mcp` package). The SDK is the low-level framework for building MCP servers in Python — **you write every tool, resource, and handler yourself**. MCP-Maker uses that SDK under the hood to **auto-generate** everything from your data source. Think of it like Django vs raw SQL: same power, less work.

---

## How It Works

```
Your Data Source          MCP-Maker              MCP Server
┌──────────────┐    ┌──────────────────┐    ┌─────────────────────────┐
│ SQLite DB    │    │                  │    │ 📄 server.py (Editable) │
│ Google Sheet │───▶│  mcp-maker init  │───▶│   ↳ Add custom tools    │
│ Airtable     │    │                  │    │                         │
│ Notion DB    │    │  (auto-inspect)  │    │ ⚙️ _autogen_tools.py      │
│ CSV files    │    │  (auto-generate) │    │   ↳ list_users()        │
│ PostgreSQL   │    │                  │    │   ↳ search_users()      │
│ MySQL        │    └──────────────────┘    └─────────────────────────┘
└──────────────┘                            Ready for Claude ✅
```

## 🏢 Enterprise-Ready Architecture

- **Non-Destructive Generation**: `mcp-maker init` safely outputs two files: `server.py` (your editable entry point) and `_autogen_tools.py`. Regenerate as often as you like—your custom tools and business logic are never overwritten.
- **Credential Hardening**: Connection strings and API keys are strictly forbidden in generated files. They are securely loaded via generated `.env` files and standard environment variables.
- **API Key Authentication (`--auth api-key`)**: Gate access to your generated server with an `MCP_API_KEY` environment variable. Every tool call is wrapped with an auth check.
- **SSL/TLS by Default**: All PostgreSQL and MySQL connections enforce encrypted transport (`sslmode=require` / `ssl=True`). Disable with `--no-ssl` for local development only.
- **Schema Versioning & Migrations**: Generates a `.mcp-maker.lock` file tracking your schema fingerprint. On re-generation, detects added/removed tables/columns and displays a detailed migration diff with color-coded changes, then auto-updates tools.
- **Multi-Source Servers**: Combine multiple data sources into a single server: `mcp-maker init sqlite:///users.db mongodb://localhost/orders` merges schemas and generates tools for both.
- **Relationship Detection**: Auto-discovers foreign keys in SQL databases and generates `join_` tools (e.g., `join_orders_with_users`).
- **Pagination Helpers**: All `list_` tools return `{results, total, has_more, next_offset}` for proper cursor-based pagination.
- **Column Selection**: Pass `fields="name,email"` to any `list_` tool to receive only specific columns instead of `SELECT *`.
- **Date Range Filters**: When date/datetime columns are detected, `list_` tools auto-generate `date_from`/`date_to` parameters.
- **Batch Operations**: `batch_insert_` and `batch_delete_` tools wrapped in transactions for all SQL connectors, MongoDB, and Supabase.
- **Export Tools**: `export_{table}_csv()` and `export_{table}_json()` for every table across all connectors.
- **Webhook Support (`--webhooks`)**: Register, list, and remove webhooks for real-time notifications on insert/update/delete events.
- **Redis Pub/Sub**: `publish_message()`, `channel_list()`, and `channel_subscribers()` tools for Redis channels.
- **Async Generation (`--async`)**: Generate async tools using `aiosqlite`, `asyncpg`, or `aiomysql` for high-concurrency MCP servers.
- **LLM Context Optimization (`--consolidate-threshold`)**: For massive schemas (>20 tables), MCP-Maker intelligently switches from generating per-table CRUD tools to consolidated generic tools (e.g., `query_database`) to prevent LLM context window bloat and reasoning degradation.
- **Structured Audit Logging (`--audit`)**: Optionally generate servers that output structured JSON logs for every tool invocation, ready for ingestion into Datadog, Splunk, or ELK.
- **Async-Ready Connection Pooling**: Fast, thread-safe database interactions with built-in connection pooling for PostgreSQL (`psycopg2.pool`), MySQL, and SQLite.
- **Guaranteed Code Quality**: All generated Python code is automatically syntactically verified through `ast.parse` and statically formatted with `black`.

## ✨ Why MCP-Maker?

- **Zero-Code Generation**: Instantly maps tables, columns, and APIs into atomic MCP tools. No coding required.
- **Zero Vendor Lock-In**: The generated `mcp_server.py` file is a 100% standalone, standard Python file built entirely on the official SDK. You can uninstall MCP-Maker immediately after generation and your server will continue to run flawlessly forever.
- **Granular Security (`--ops`)**: You control exactly what the LLM can do. Explicitly authorize `read`, `insert`, `update`, or `delete` operations.
- **Auto-Rate Limiting**: Built-in TokenBucket throttling for Cloud APIs (Airtable, Notion, Google Sheets) prevents `429 Too Many Requests` bans when LLMs make aggressive parallel tool calls.
- **Semantic Vector Search (`--semantic`)**: Automatically spins up a ChromaDB vector database alongside your SQL tables for high-quality, meaning-based search.
- **Context Window Optimized (`--tables`)**: Only expose the data you actually need to prevent LLM context bloat and hallucination.
- **Environment Management**: Safely manage API credentials via `mcp-maker env` instead of hardcoding them.

## 🔌 Supercharged Connectors

While basic tools stop at simple SQL tables, MCP-Maker's Connectors are engineered for complex enterprise use cases:

- **Notion**: Supports **Multi-Database URIs** (`notion://DB1,DB2`), automatically parses **20+ property types** (Rollups, Relations, Formulas), handles cursor pagination, and exposes deep `filter` tools.
- **Airtable**: Generates tools to query via Airtable **Formulas**, target specific **Views**, automatically sorts records, and discovers your Bases directly (`mcp-maker bases`).
- **Google Sheets**: Treats entire tabs as discrete SQL-like tables, infers column types, and provides pinpoint `update_cell` tools.
- **PostgreSQL / MySQL**: Detects Primary Keys automatically, maps all complex SQL native types, and fully supports SSL-encrypted TLS connections.

## Quick Start (2 minutes)

### Step 1: Install

```bash
pip install mcp-maker
```

### Step 2: Generate a server from your data

```bash
# SQLite database
mcp-maker init sqlite:///path/to/my_database.db

# CSV/JSON files in a directory
mcp-maker init ./my-data/

# Google Sheets (see docs for auth setup)
mcp-maker init gsheet://YOUR_SPREADSHEET_ID

# Airtable
mcp-maker init airtable://appXXXXXXXXXX

# Notion
mcp-maker init notion://DATABASE_ID
```

This creates a `mcp_server.py` file with all your tools.

### Step 3: Connect to Claude Desktop

```bash
# Auto-configure Claude Desktop
mcp-maker config --install

# Restart Claude Desktop, then ask:
# "What tables are in my database?"
# "Show me the top 10 customers"
# "Search for records containing 'Python'"
```

That's it. Your AI can now query your data.

---

## 📖 Documentation

**👉 [Getting Started Guide](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/getting-started.md)** — Tutorial, installation, first server, Claude Desktop setup

**📋 [Full Reference (DOCS.md)](https://github.com/MrAliHasan/mcp-maker/blob/main/DOCS.md)** — CLI commands, schema filtering, env management, architecture, roadmap

### Connector Guides (with step-by-step setup, examples, and troubleshooting)

| Connector | Guide |
|-----------|-------|
| SQLite | [docs/sqlite.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/sqlite.md) |
| Files (CSV/JSON) | [docs/files.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/files.md) |
| PostgreSQL | [docs/postgresql.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/postgresql.md) |
| MySQL | [docs/mysql.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/mysql.md) |
| Airtable | [docs/airtable.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/airtable.md) — Formulas, views, sorting, CRUD |
| Google Sheets | [docs/google-sheets.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/google-sheets.md) — GCP service account setup |
| Notion | [docs/notion.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/notion.md) — Integration setup, multi-DB support |
| Excel | [docs/excel.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/excel.md) — .xlsx files, sheets as tables |
| MongoDB | [docs/mongodb.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/mongodb.md) — Document sampling, full CRUD |
| Supabase | [docs/supabase.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/supabase.md) — Auth/storage tools, PostgREST |
| REST API | [docs/openapi.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/openapi.md) — OpenAPI/Swagger specs |
| Redis | [docs/redis.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/redis.md) — Key grouping, type-aware tools |

### Feature Guides

| Feature | Guide |
|---------|-------|
| Semantic Search | [docs/semantic-search.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/semantic-search.md) — ChromaDB vector search, search by meaning |

---

## 🔌 Supported Connectors (12)

| Connector | URI Format | Auth Required | Install |
|-----------|-----------|-------------|---------|
| SQLite | `sqlite:///my.db` | ❌ | Built-in |
| Files | `./data/` | ❌ | Built-in |
| PostgreSQL | `postgres://user:pass@host/db` | ✅ DB creds | `pip install mcp-maker[postgres]` |
| MySQL | `mysql://user:pass@host/db` | ✅ DB creds | `pip install mcp-maker[mysql]` |
| Airtable | `airtable://appXXXX` | ✅ API key | `pip install mcp-maker[airtable]` |
| Google Sheets | `gsheet://SPREADSHEET_ID` | ✅ Service acct | `pip install mcp-maker[gsheets]` |
| Notion | `notion://DATABASE_ID` | ✅ Integration | `pip install mcp-maker[notion]` |
| Excel | `./data.xlsx` or `excel:///path.xlsx` | ❌ | `pip install mcp-maker[excel]` |
| MongoDB | `mongodb://user:pass@host/db` | ✅ DB creds | `pip install mcp-maker[mongodb]` |
| Supabase | `supabase://PROJECT_REF` | ✅ API key | `pip install mcp-maker[supabase]` |
| REST API | `openapi:///path/to/spec.yaml` | ✅ API token | `pip install mcp-maker[openapi]` |
| Redis | `redis://host:6379/0` | ✅ Password | `pip install mcp-maker[redis]` |

Install all connectors at once:

```bash
pip install mcp-maker[all]
```

---

## CLI Commands

```bash
mcp-maker init <source>                    # Generate an MCP server
mcp-maker init <source> --ops read,insert  # Include specific write operations
mcp-maker init <source> --tables users,orders  # Only include specific tables
mcp-maker init <source> --semantic         # Enable vector/semantic search
mcp-maker init <source> --audit            # Enable structured JSON audit logging
mcp-maker init <source> --auth api-key     # Require MCP_API_KEY for access
mcp-maker init <source> --async            # Generate async tools (aiosqlite/asyncpg)
mcp-maker init <source> --cache 60          # Cache read results for 60 seconds
mcp-maker init <source> --no-ssl           # Disable SSL for local development
mcp-maker init <source> --force            # Skip schema change warnings
mcp-maker init <source> --consolidate-threshold 10 # Consolidate large schemas
mcp-maker deploy --platform railway        # Generate deployment files
mcp-maker deploy --platform render         # Render deployment
mcp-maker deploy --platform fly            # Fly.io deployment
mcp-maker serve                            # Run the generated server
mcp-maker inspect <source>                 # Preview what would be generated (dry run)
mcp-maker config --install                 # Auto-write Claude Desktop config
mcp-maker env set KEY VALUE                # Store API keys safely in .env
mcp-maker env list                         # List stored keys (masked)
mcp-maker list-connectors                  # Show available connectors
mcp-maker bases                            # Discover Airtable bases
```

---

## 📦 Installation

```bash
# Core (SQLite + Files)
pip install mcp-maker

# With PostgreSQL support
pip install mcp-maker[postgres]

# With Airtable support
pip install mcp-maker[airtable]

# With Google Sheets support
pip install mcp-maker[gsheets]

# With Notion support
pip install mcp-maker[notion]

# With semantic search (ChromaDB vector search)
pip install mcp-maker[semantic]

# With async support
pip install mcp-maker[async-sqlite]    # aiosqlite
pip install mcp-maker[async-postgres]  # asyncpg
pip install mcp-maker[async-mysql]     # aiomysql

# New connectors
pip install mcp-maker[excel]           # Excel (.xlsx)
pip install mcp-maker[mongodb]         # MongoDB
pip install mcp-maker[supabase]        # Supabase
pip install mcp-maker[openapi]         # REST API (OpenAPI specs)
pip install mcp-maker[redis]           # Redis

# All connectors + semantic search + async
pip install mcp-maker[all]

# Development
pip install mcp-maker[dev]
```

---

## 🤝 Contributing

MCP-Maker is designed for community contributions — each new **connector** is a self-contained PR.

See [CONTRIBUTING.md](https://github.com/MrAliHasan/mcp-maker/blob/main/CONTRIBUTING.md) for detailed instructions and a step-by-step connector creation guide.

## 📄 License

This project is licensed under the [MIT License](https://github.com/MrAliHasan/mcp-maker/blob/main/LICENSE).

