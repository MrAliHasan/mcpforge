# MCPForge

### ⚒️ Auto-generate MCP servers from any data source. Zero code required.

> Point MCPForge at a database, API, or file directory and get a fully functional [MCP](https://modelcontextprotocol.io/) server in seconds — ready for Claude, ChatGPT, Cursor, and any MCP-compatible AI.

---

## 🚀 Quick Start

```bash
pip install mcpforge

# From a SQLite database
mcpforge init sqlite:///my_database.db
mcpforge serve

# From CSV/JSON files
mcpforge init ./data/
mcpforge serve

# That's it! Your AI can now query your data.
```

## Why MCPForge?

| | FastMCP | MCPForge |
|---|---------|----------|
| **Approach** | You write Python tools | It generates everything |
| **Setup time** | Minutes–hours | Seconds |
| **Code required** | Yes | No |
| **Best for** | Custom logic | Data access |

MCPForge uses FastMCP under the hood — it's not competing, it's building on top.

---

## 📋 Commands

| Command | Description |
|---------|-------------|
| `mcpforge init <source>` | Generate an MCP server from a data source |
| `mcpforge inspect <source>` | Preview what would be generated (dry run) |
| `mcpforge serve` | Run the generated MCP server |
| `mcpforge list-connectors` | Show available connectors |

## 🔌 Connectors

### Built-in

| Connector | URI Format | Status |
|-----------|-----------|--------|
| **SQLite** | `sqlite:///path/to/db.sqlite` | ✅ Ready |
| **Files** (CSV, JSON, txt) | `./path/to/directory/` | ✅ Ready |
| **PostgreSQL** | `postgres://user:pass@host/db` | 🔜 Coming |
| **MySQL** | `mysql://user:pass@host/db` | 🔜 Coming |
| **Airtable** | `airtable://appXXXX` | 🔜 Coming |

### Want to add a connector?

Every connector is a single Python file — PRs welcome! See [Contributing](#contributing).

---

## 🛠️ What Gets Generated

For each table in your data source, MCPForge generates:

| Tool | Description |
|------|-------------|
| `list_{table}(limit, offset)` | Paginated listing |
| `get_{table}_by_{pk}(id)` | Get by primary key |
| `search_{table}(query)` | Full-text search |
| `count_{table}()` | Row count |
| `schema_{table}()` | Column names and types |

For text files, it generates `read_{name}()` resources.

---

## 💡 Example: SQLite Database

```bash
$ mcpforge init sqlite:///chinook.db

⚒️  MCPForge v0.1.0

✅ Connected to sqlite source

┌──────────────────────────────────┐
│ 📊 Discovered Tables (11)       │
├──────────┬──────────┬────────────┤
│ Table    │ Columns  │ Rows       │
├──────────┼──────────┼────────────┤
│ albums   │ id, ...  │ 347        │
│ artists  │ id, ...  │ 275        │
│ tracks   │ id, ...  │ 3503       │
└──────────┴──────────┴────────────┘

🎉 Generated: mcp_server.py

$ mcpforge serve
🚀 MCPForge Server running...
```

Now in Claude Desktop, add the server and ask: *"What are the top 5 artists with the most albums?"*

---

## 🤝 Contributing

MCPForge is designed for community contributions — each new **connector** is a self-contained PR:

1. Create `src/mcpforge/connectors/your_connector.py`
2. Subclass `BaseConnector`
3. Implement `validate()` and `inspect()`
4. Register with `register_connector("scheme", YourConnector)`
5. Add tests

See `connectors/sqlite.py` as a reference implementation.

---

## 📦 Installation

```bash
# Core (SQLite + Files)
pip install mcpforge

# With PostgreSQL support
pip install mcpforge[postgres]

# With all connectors
pip install mcpforge[all]

# Development
pip install mcpforge[dev]
```

## License

MIT
