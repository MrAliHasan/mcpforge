# MCP-Maker Documentation

Complete documentation for MCP-Maker — organized by connector.

---

## 📚 Guides

### Getting Started

| Guide | Description |
|-------|------------|
| **[Getting Started](docs/getting-started.md)** | Installation, tutorial, first server, Claude Desktop setup, write operations |

### Connector Guides

Each guide includes step-by-step setup, authentication, complete examples with sample Claude conversations, type mapping, and troubleshooting.

| Connector | Guide | Key Features |
|-----------|-------|-------------|
| **SQLite** | [docs/sqlite.md](docs/sqlite.md) | Zero config, auto-PK detection, views support |
| **Files (CSV/JSON)** | [docs/files.md](docs/files.md) | CSV/JSON as tables, TXT/MD as resources, type inference |
| **PostgreSQL** | [docs/postgresql.md](docs/postgresql.md) | Custom schemas, SSL support, all PG types mapped |
| **MySQL** | [docs/mysql.md](docs/mysql.md) | MariaDB compatible, charset support |
| **Airtable** | [docs/airtable.md](docs/airtable.md) | Formula filtering, views, sorting, base discovery, CRUD |
| **Google Sheets** | [docs/google-sheets.md](docs/google-sheets.md) | GCP service account setup, sheet tabs as tables, cell updates |
| **Notion** | [docs/notion.md](docs/notion.md) | Integration setup, multi-DB support, cursor pagination, 20+ property types |

### Feature Guides

| Feature | Guide | Key Features |
|---------|-------|-------------|
| **Semantic Search** | [docs/semantic-search.md](docs/semantic-search.md) | ChromaDB vector search, search by meaning, works with all connectors |

---

## Quick Reference

### CLI Commands

```bash
mcp-maker init <source>                        # Generate an MCP server
mcp-maker init <source> --read-write           # Include write operations
mcp-maker init <source> --tables users,orders  # Only include specific tables
mcp-maker init <source> --semantic             # Enable vector/semantic search
mcp-maker serve                                # Run the generated server
mcp-maker inspect <source>                     # Dry run — preview what would be generated
mcp-maker inspect <source> --tables users      # Preview filtered schema
mcp-maker config                               # Show Claude Desktop config JSON
mcp-maker config --install                     # Auto-write Claude Desktop config
mcp-maker env set KEY VALUE                    # Store API key in .env
mcp-maker env list                             # List stored keys (masked)
mcp-maker env show KEY                         # Show actual key value
mcp-maker env delete KEY                       # Remove a key
mcp-maker list-connectors                      # Show available connectors
mcp-maker bases                                # Discover Airtable bases
```

### Schema Filtering

For large databases with many tables, use `--tables` to only generate tools for what you need:

```bash
# 50-table database but you only need 3
mcp-maker init postgres://user:pass@host/db --tables users,orders,products

# Preview what would be included
mcp-maker inspect postgres://user:pass@host/db --tables users
```

### Environment Variable Management

Store API keys safely in a `.env` file instead of hardcoding or exporting:

```bash
# Store your keys
mcp-maker env set AIRTABLE_API_KEY pat_xxxxxxxxxxxx
mcp-maker env set NOTION_API_KEY ntn_xxxxxxxxxxxx
mcp-maker env set GOOGLE_SERVICE_ACCOUNT_FILE ./credentials.json

# View stored keys (values are masked)
mcp-maker env list
# ┌─────────────────────────────┬────────────────┬─────────────────────────────┐
# │ Variable                    │ Value (masked) │ Description                 │
# ├─────────────────────────────┼────────────────┼─────────────────────────────┤
# │ AIRTABLE_API_KEY            │ pat_xx...xxxx  │ Airtable API key (PAT)      │
# │ NOTION_API_KEY              │ ntn_xx...xxxx  │ Notion integration secret   │
# └─────────────────────────────┴────────────────┴─────────────────────────────┘

# Load into your shell
source .env

# Or add to Claude Desktop config env section
```

### Connector URIs

```bash
sqlite:///path/to/db.sqlite           # SQLite
./path/to/directory/                   # Files (CSV, JSON, TXT)
postgres://user:pass@host:5432/db      # PostgreSQL
mysql://user:pass@host:3306/db         # MySQL
airtable://appXXXXXXXXXXX             # Airtable
gsheet://SPREADSHEET_ID               # Google Sheets
notion://DATABASE_ID                   # Notion (single DB)
notion://DB_ID_1,DB_ID_2              # Notion (multiple DBs)
```

### Environment Variables

| Variable | Used By | Example |
|----------|---------|---------|
| `AIRTABLE_API_KEY` | Airtable | `pat_xxxxxxxxxxxx` |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Google Sheets | `/path/to/credentials.json` |
| `GOOGLE_CREDENTIALS_JSON` | Google Sheets (alt) | `'{"type":"service_account",...}'` |
| `NOTION_API_KEY` | Notion | `ntn_xxxxxxxxxxxx` |

---

## Architecture

```
1. INSPECT              2. GENERATE             3. SERVE
┌───────────────┐    ┌──────────────────┐    ┌──────────────┐
│ Connector     │    │ Jinja2 Template  │    │ Generated    │
│ inspects your │───▶│ renders a full   │───▶│ Python file  │
│ data source   │    │ MCP server file  │    │ runs as MCP  │
└───────────────┘    └──────────────────┘    └──────────────┘
```

**Key point:** The generated `mcp_server.py` is **standalone** — it doesn't import `mcp-maker`. You can uninstall MCP-Maker after generation and the server keeps working.

---

## Coming Soon

### 🥈 High Impact
- **One-Command Deploy** — `mcp-maker deploy` → push to Railway/Render/Fly.io
- **REST API Connector** — Pass an OpenAPI/Swagger spec, auto-generate MCP tools
- **Excel (.xlsx) Connector** — Point at `.xlsx` files, auto-detect sheets as tables
- **MongoDB Connector** — `mcp-maker init mongodb://...`
- **Supabase Connector** — Built on Postgres but adds Supabase auth/storage tools

### 🥉 Polish & Power
- **Smart Caching** — Cache API responses to reduce calls and speed up queries
- **Relationship Detection** — Auto-detect foreign keys, generate join tools
- **`mcp-maker upgrade`** — Re-inspect and update without overwriting customizations
- **Web Dashboard** — `mcp-maker ui` → browser-based management
- **Multi-Source Servers** — Combine sources: `mcp-maker init sqlite:///users.db airtable://appXXX`

