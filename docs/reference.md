# CLI Reference & Architecture

Complete reference documentation for MCP-Maker CLI, environment variables, security, and architecture.

---

## CLI Commands

```bash
# Server Generation
mcp-maker init <source>                        # Generate an MCP server
mcp-maker init <source1> <source2>             # Multi-source: merge into one server
mcp-maker init <source> --ops read,insert      # Include specific write operations
mcp-maker init <source> --tables users,orders  # Only include specific tables
mcp-maker init <source> --semantic             # Enable vector/semantic search
mcp-maker init <source> --audit                # Enable structured JSON audit logging
mcp-maker init <source> --auth api-key         # Require MCP_API_KEY for access
mcp-maker init <source> --async                # Generate async tools
mcp-maker init <source> --cache 60             # Cache read results for 60 seconds
mcp-maker init <source> --webhooks             # Enable webhook notifications
mcp-maker init <source> --no-ssl               # Disable SSL/TLS (local dev only)
mcp-maker init <source> --force                # Skip schema change warnings
mcp-maker init <source> --consolidate-threshold 20  # Consolidate large schemas

# Deployment
mcp-maker deploy --platform railway            # Generate Railway deployment files
mcp-maker deploy --platform render             # Generate Render deployment files
mcp-maker deploy --platform fly                # Generate Fly.io deployment files

# Server Management
mcp-maker serve                                # Run the generated server
mcp-maker test                                 # Smoke test a generated server
mcp-maker test --output ./my-server            # Test a server in a specific directory

# Configuration
mcp-maker config                               # Show Claude Desktop config JSON
mcp-maker config --install                     # Auto-write Claude Desktop config
mcp-maker inspect <source>                     # Dry run — preview generated schema
mcp-maker inspect <source> --tables users      # Preview filtered schema

# Environment
mcp-maker env set KEY VALUE                    # Store API key in .env
mcp-maker env list                             # List stored keys (masked)
mcp-maker env show KEY                         # Show actual key value
mcp-maker env delete KEY                       # Remove a key

# Discovery
mcp-maker list-connectors                      # Show available connectors
mcp-maker bases                                # Discover Airtable bases
```

---

## Connector URIs

```bash
sqlite:///path/to/db.sqlite           # SQLite
./path/to/directory/                   # Files (CSV, JSON, TXT)
postgres://user:pass@host:5432/db      # PostgreSQL
mysql://user:pass@host:3306/db         # MySQL
airtable://appXXXXXXXXXXX             # Airtable
gsheet://SPREADSHEET_ID               # Google Sheets
notion://DATABASE_ID                   # Notion (single DB)
notion://DB_ID_1,DB_ID_2              # Notion (multiple DBs)
excel:///path/to/file.xlsx            # Excel
mongodb://user:pass@host:27017/db      # MongoDB
supabase://PROJECT_REF                 # Supabase
openapi:///path/to/spec.yaml          # REST API (OpenAPI)
redis://host:6379/0                    # Redis
rediss://host:6379/0                   # Redis (TLS)
hubspot://pat=YOUR_TOKEN               # HubSpot
```

---

## Environment Variables

| Variable | Used By | Example |
|----------|---------|---------|
| `DATABASE_URL` | SQLite, PostgreSQL, MySQL | `sqlite:///my.db` |
| `AIRTABLE_API_KEY` | Airtable | `pat_xxxxxxxxxxxx` |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Google Sheets | `/path/to/credentials.json` |
| `GOOGLE_CREDENTIALS_JSON` | Google Sheets (alt) | `'{"type":"service_account",...}'` |
| `NOTION_API_KEY` | Notion | `ntn_xxxxxxxxxxxx` |
| `SUPABASE_URL` | Supabase | `https://your-project.supabase.co` |
| `SUPABASE_KEY` | Supabase | `eyJhbG...` (anon or service_role) |
| `HUBSPOT_ACCESS_TOKEN` | HubSpot | `pat-na1-...` |
| `API_TOKEN` | OpenAPI/REST | Bearer token |
| `REDIS_URL` | Redis | `redis://localhost:6379/0` |
| `MCP_API_KEY` | Auth middleware | Any secret string |

---

## Security Features

### API Key Authentication

```bash
mcp-maker init sqlite:///my.db --auth api-key
export MCP_API_KEY="your-secret-key"
mcp-maker serve
```

Every tool call requires a valid `api_key` parameter matching `MCP_API_KEY`. Without it, requests are rejected with `PermissionError`.

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

**Key design principle:** The generated `mcp_server.py` is **standalone** — it doesn't import `mcp-maker`. Regenerating safely updates only the `_autogen_` file. Your custom tools are never overwritten. You can uninstall MCP-Maker after generation.
