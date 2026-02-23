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
| **Excel** | [docs/excel.md](docs/excel.md) | .xlsx files, sheets as tables, auto type inference |
| **MongoDB** | [docs/mongodb.md](docs/mongodb.md) | Collection inspection, document sampling, full CRUD |
| **Supabase** | [docs/supabase.md](docs/supabase.md) | Built on Postgres, auth/storage tools, PostgREST |
| **REST API** | [docs/openapi.md](docs/openapi.md) | OpenAPI/Swagger specs, one tool per endpoint |
| **Redis** | [docs/redis.md](docs/redis.md) | Key grouping, type-aware tools (string/hash/list/set/zset) |

### Feature Guides

| Feature | Guide | Key Features |
|---------|-------|-------------|
| **Semantic Search** | [docs/semantic-search.md](docs/semantic-search.md) | ChromaDB vector search, search by meaning, works with all connectors |

---

## Quick Reference

### CLI Commands

```bash
mcp-maker init <source>                        # Generate an MCP server
mcp-maker init <source1> <source2>             # Multi-source: merge into one server
mcp-maker init <source> --ops read,insert      # Include specific write operations
mcp-maker init <source> --tables users,orders  # Only include specific tables
mcp-maker init <source> --semantic             # Enable vector/semantic search
mcp-maker init <source> --audit                # Enable structured JSON audit logging
mcp-maker init <source> --auth api-key         # Require MCP_API_KEY for access
mcp-maker init <source> --async                # Generate async tools
mcp-maker init <source> --cache 60             # Cache read results for 60 seconds
mcp-maker init <source> --webhooks             # Enable webhook registration and notifications
mcp-maker init <source> --no-ssl               # Disable SSL/TLS enforcement (local dev only)
mcp-maker init <source> --force                # Skip schema change warnings on re-generation
mcp-maker init <source> --consolidate-threshold 20 # Consolidate tools for large schemas
mcp-maker deploy --platform railway            # Generate Railway deployment files
mcp-maker deploy --platform render             # Generate Render deployment files
mcp-maker deploy --platform fly                # Generate Fly.io deployment files
mcp-maker serve                                # Run the generated server
mcp-maker inspect <source>                     # Dry run — preview what would be generated
mcp-maker inspect <source> --tables users      # Preview filtered schema
mcp-maker test                                 # Smoke test a generated server
mcp-maker test --output ./my-server            # Test a server in a specific directory
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
| `SUPABASE_URL` | Supabase | `https://your-project.supabase.co` |
| `SUPABASE_KEY` | Supabase | `eyJhbG...` (anon or service_role key) |
| `API_TOKEN` | OpenAPI/REST | Bearer token for API authentication |
| `REDIS_URL` | Redis | `redis://localhost:6379/0` |
| `MCP_API_KEY` | Auth middleware (`--auth api-key`) | Any secret string |

---

## 🔒 Security Features

### API Key Authentication

```bash
mcp-maker init sqlite:///my.db --auth api-key
export MCP_API_KEY="your-secret-key"
mcp-maker serve
```

Every tool call is validated against `MCP_API_KEY`. Without it, all requests are rejected with `PermissionError`.

### SSL/TLS Enforcement

PostgreSQL and MySQL connections enforce SSL by default:
- **PostgreSQL**: Appends `sslmode=require` to DSN
- **MySQL**: Adds `ssl=True` to connection config

```bash
# Disable for local development only
mcp-maker init postgres://localhost/dev --no-ssl
```

### Schema Versioning

MCP-Maker generates a `.mcp-maker.lock` file tracking your schema fingerprint. On re-generation, it detects breaking changes:

```
⚠️  Schema has changed since last generation!
  + Added tables: payments
  - Removed tables: legacy_orders
Use --force to suppress this warning.
```

---

## Architecture

```
1. INSPECT              2. GENERATE             3. SERVE
┌───────────────┐    ┌──────────────────┐    ┌─────────────────────────┐
│ Connector     │    │ Jinja2 Templates │    │ 📄 mcp_server.py        │
│ inspects your │───▶│ render dual      │───▶│   ↳ Add custom tools    │
│ data source   │    │ MCP files        │    │                         │
└───────────────┘    └──────────────────┘    │ ⚙️ _autogen_mcp_server.py │
                                             │   ↳ list_users()        │
                                             └─────────────────────────┘
```

**Key point:** The generated `mcp_server.py` is **standalone** and **non-destructive** — it doesn't import `mcp-maker`, and regenerating the server safely updates only the `_autogen_` file. Your custom tools are never overwritten. You can uninstall MCP-Maker after generation and the server keeps working!

---

## ✅ Recently Shipped

- **Relationship Detection** — Auto-detect foreign keys, generate `join_` tools
- **Multi-Source Servers** — `mcp-maker init sqlite:///users.db mongodb://localhost/orders` → single server
- **Pagination Helpers** — All `list_` tools return `{results, total, has_more, next_offset}`
- **Column Selection** — `fields="name,email"` param on all `list_` tools
- **Date Range Filters** — Auto-generated `_from`/`_to` for date/datetime columns
- **Batch Operations** — `batch_insert_` and `batch_delete_` for all SQL, MongoDB, Supabase
- **Export Tools** — `export_{table}_csv()` and `export_{table}_json()` for all connectors
- **Webhook Support** — `--webhooks` flag for real-time notifications
- **Redis Pub/Sub** — `publish_message()`, `channel_list()`, `channel_subscribers()`
- **`mcp-maker test`** — Smoke test generated servers with AST analysis
- **Schema Migrations** — Rich migration diff table with auto-update on re-generation

### 🥉 Coming Soon
- **Web Dashboard** — `mcp-maker ui` → browser-based management
- **GraphQL Support** — Generate MCP tools from GraphQL schemas

