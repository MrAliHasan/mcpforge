# Getting Started with MCP-Maker

Learn how to create your first MCP server in under 5 minutes.

---

## What is MCP-Maker?

MCP-Maker auto-generates [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers from your data. Instead of writing Python code to define tools, you point it at your data and it generates everything.

**What does "MCP server" mean in practice?** It means your AI assistant (Claude, ChatGPT, Cursor) can directly query, search, and modify your data through natural language.

### Before MCP-Maker (manual)

```python
# You'd write this by hand for EVERY table...
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def list_users(limit: int = 50, offset: int = 0) -> list[dict]:
    """List users from the database."""
    conn = sqlite3.connect("my.db")
    cursor = conn.execute("SELECT * FROM users LIMIT ? OFFSET ?", (limit, offset))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

@mcp.tool()
def search_users(query: str) -> list[dict]:
    """Search users."""
    # ... more code ...

# Repeat for every table, every operation...
```

### With MCP-Maker (automatic)

```bash
mcp-maker init sqlite:///my.db
# Done. All tools generated automatically.
```

---

## Installation

### Step 1: Install MCP-Maker

```bash
pip install mcp-maker
```

This gives you SQLite and file connectors out of the box.

### Step 2: Install connectors you need

```bash
# Pick what you need:
pip install mcp-maker[postgres]     # PostgreSQL
pip install mcp-maker[mysql]        # MySQL
pip install mcp-maker[airtable]     # Airtable
pip install mcp-maker[gsheets]      # Google Sheets
pip install mcp-maker[notion]       # Notion

# Or install everything:
pip install mcp-maker[all]
```

### Step 3: Verify installation

```bash
mcp-maker list-connectors
```

You'll see a table showing which connectors are installed:

```
┌──────────┬──────────────────────┬──────────────────────────┬──────────────┐
│ Scheme   │ Connector            │ Example URI              │ Status       │
├──────────┼──────────────────────┼──────────────────────────┼──────────────┤
│ sqlite   │ SQLiteConnector      │ sqlite:///my_database.db │ ✅ Installed │
│ files    │ FileConnector        │ ./data/                  │ ✅ Installed │
│ airtable │ AirtableConnector    │ airtable://...           │ ✅ Installed │
│ gsheet   │ GoogleSheetsConnector│ gsheet://...             │ ✅ Installed │
│ notion   │ NotionConnector      │ notion://...             │ ✅ Installed │
└──────────┴──────────────────────┴──────────────────────────┴──────────────┘
```

---

## Tutorial: Your First MCP Server

Let's create a server from a SQLite database.

### 1. Create a sample database (or use your own)

```bash
# Create a quick test database
python3 -c "
import sqlite3
conn = sqlite3.connect('demo.db')
conn.execute('''CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    company TEXT,
    role TEXT
)''')
conn.executemany('INSERT INTO contacts (name, email, company, role) VALUES (?, ?, ?, ?)', [
    ('Alice Johnson', 'alice@acme.com', 'Acme Corp', 'Engineer'),
    ('Bob Smith', 'bob@globex.com', 'Globex Inc', 'Designer'),
    ('Carol Williams', 'carol@initech.com', 'Initech', 'Manager'),
    ('Dave Brown', 'dave@acme.com', 'Acme Corp', 'Director'),
    ('Eve Davis', 'eve@globex.com', 'Globex Inc', 'Engineer'),
])
conn.commit()
print('Created demo.db with 5 contacts')
"
```

### 2. Generate the MCP server

```bash
mcp-maker init sqlite:///demo.db
```

Output:

```
⚒️ MCP-Maker                                         v0.2.2

  ✅ Connected to sqlite source

  ┌────────────────────────────────────────────────────────┐
  │ 📊 Discovered Tables (1)                              │
  ├──────────┬──────────────────────────┬──────┬───────────┤
  │ Table    │ Columns                  │ Rows │ PK        │
  ├──────────┼──────────────────────────┼──────┼───────────┤
  │ contacts │ id, name, email, company │    5 │ id        │
  └──────────┴──────────────────────────┴──────┴───────────┘

  🎉 Generated: mcp_server.py
```

### 3. Preview what was generated

Open `mcp_server.py` — you'll see auto-generated tools:

```python
@mcp.tool()
def list_contacts(limit: int = 50, offset: int = 0) -> list[dict]:
    """List rows from the 'contacts' table."""
    ...

@mcp.tool()
def get_contacts_by_id(id: int) -> dict | None:
    """Get a single row from 'contacts' by id."""
    ...

@mcp.tool()
def search_contacts(query: str, limit: int = 20) -> list[dict]:
    """Search 'contacts' across all text columns."""
    ...

@mcp.tool()
def count_contacts() -> int:
    """Get the total number of rows in 'contacts'."""
    ...

@mcp.tool()
def schema_contacts() -> dict:
    """Get the schema of the 'contacts' table."""
    ...
```

### 4. Run it

```bash
mcp-maker serve
```

### 5. Connect to Claude Desktop

```bash
mcp-maker config --install
```

Restart Claude Desktop. Now you can ask:

> **You:** "What contacts do I have?"
>
> **Claude:** *calls `list_contacts(limit=50)`*
> "You have 5 contacts: Alice Johnson (Engineer at Acme Corp), Bob Smith (Designer at Globex Inc)..."

> **You:** "Find everyone at Acme Corp"
>
> **Claude:** *calls `search_contacts(query="Acme Corp")`*
> "I found 2 contacts at Acme Corp: Alice Johnson (Engineer) and Dave Brown (Director)."

> **You:** "How many contacts total?"
>
> **Claude:** *calls `count_contacts()`*
> "You have 5 contacts in total."

---

## What Tools Get Generated?

Every connector generates these **standard tools** per table:

| Tool | What it does | Example call |
|------|-------------|-------------|
| `list_{table}(limit, offset)` | Paginated listing | `list_contacts(limit=10, offset=0)` |
| `get_{table}_by_{pk}(id)` | Get by primary key | `get_contacts_by_id(id=3)` |
| `search_{table}(query)` | Full-text search | `search_contacts(query="alice")` |
| `count_{table}()` | Row count | `count_contacts()` |
| `schema_{table}()` | Column info | `schema_contacts()` |

### What does the output look like?

**`list_contacts(limit=2)`** returns:

```json
[
  {"id": 1, "name": "Alice Johnson", "email": "alice@acme.com", "company": "Acme Corp", "role": "Engineer"},
  {"id": 2, "name": "Bob Smith", "email": "bob@globex.com", "company": "Globex Inc", "role": "Designer"}
]
```

**`schema_contacts()`** returns:

```json
{
  "id": {"type": "INTEGER", "primary_key": true, "nullable": false},
  "name": {"type": "TEXT", "primary_key": false, "nullable": false},
  "email": {"type": "TEXT", "primary_key": false, "nullable": true},
  "company": {"type": "TEXT", "primary_key": false, "nullable": true},
  "role": {"type": "TEXT", "primary_key": false, "nullable": true}
}
```

---

## Write Operations

By default, servers are **read-only**. Add `--read-write` to enable data modification:

```bash
mcp-maker init sqlite:///demo.db --read-write
```

This generates additional tools:

| Tool | What it does | Example call |
|------|-------------|-------------|
| `insert_{table}(...)` | Create a new row | `insert_contacts(name="Frank", email="frank@co.com")` |
| `update_{table}_by_{pk}(...)` | Update a row | `update_contacts_by_id(id=1, role="Senior Engineer")` |
| `delete_{table}_by_{pk}(id)` | Delete a row | `delete_contacts_by_id(id=3)` |

> **⚠️ Warning:** Write tools allow the AI to modify your data. Use with caution in production.

---

## Connecting to Claude Desktop

### Auto-Configure (recommended)

```bash
mcp-maker config --install
```

This writes the correct JSON to your Claude Desktop config file.

**Then restart Claude Desktop** (fully quit and reopen).

### Manual Configuration

If auto-config doesn't work, do it manually:

1. Open your Claude Desktop config file:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`
   - **Linux:** `~/.config/Claude/claude_desktop_config.json`

2. Add this JSON (adjust paths):

```json
{
  "mcpServers": {
    "my-data": {
      "command": "/usr/bin/python3",
      "args": ["/full/path/to/mcp_server.py"]
    }
  }
}
```

3. For API-based connectors (Airtable, Sheets, Notion), add env vars:

```json
{
  "mcpServers": {
    "my-airtable": {
      "command": "/usr/bin/python3",
      "args": ["/full/path/to/mcp_server.py"],
      "env": {
        "AIRTABLE_API_KEY": "pat_xxxxxxxxxxxx"
      }
    }
  }
}
```

4. Restart Claude Desktop.

---

## Next Steps

Choose your connector guide:

- **[SQLite Guide](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/sqlite.md)** — Local databases
- **[Files Guide](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/files.md)** — CSV, JSON, text files
- **[PostgreSQL Guide](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/postgresql.md)** — Production databases
- **[MySQL Guide](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/mysql.md)** — MySQL/MariaDB
- **[Airtable Guide](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/airtable.md)** — Airtable bases with formulas & views
- **[Google Sheets Guide](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/google-sheets.md)** — Spreadsheets
- **[Notion Guide](https://github.com/MrAliHasan/mcp-maker/blob/main/docs/notion.md)** — Notion databases
