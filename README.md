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
┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐
│ SQLite DB    │    │                  │    │ list_users()      │
│ Google Sheet │───▶│  mcp-maker init  │───▶│ search_users()    │
│ Airtable     │    │                  │    │ count_users()     │
│ Notion DB    │    │  (auto-inspect)  │    │ create_users()    │
│ CSV files    │    │  (auto-generate) │    │ ... 10+ tools     │
│ PostgreSQL   │    │                  │    │                   │
│ MySQL        │    └──────────────────┘    └───────────────────┘
└──────────────┘                            Ready for Claude ✅
```

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

### Feature Guides

| Feature | Guide |
|---------|-------|
| Semantic Search | [docs/semantic-search.md](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/semantic-search.md) — ChromaDB vector search, search by meaning |

---

## 🔌 Supported Connectors (7)

| Connector | URI Format | Auth Required | Install |
|-----------|-----------|-------------|---------|
| SQLite | `sqlite:///my.db` | ❌ | Built-in |
| Files | `./data/` | ❌ | Built-in |
| PostgreSQL | `postgres://user:pass@host/db` | ✅ DB creds | `pip install mcp-maker[postgres]` |
| MySQL | `mysql://user:pass@host/db` | ✅ DB creds | `pip install mcp-maker[mysql]` |
| Airtable | `airtable://appXXXX` | ✅ API key | `pip install mcp-maker[airtable]` |
| Google Sheets | `gsheet://SPREADSHEET_ID` | ✅ Service acct | `pip install mcp-maker[gsheets]` |
| Notion | `notion://DATABASE_ID` | ✅ Integration | `pip install mcp-maker[notion]` |

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

# All connectors + semantic search
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

