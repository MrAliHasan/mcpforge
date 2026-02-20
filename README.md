# MCP-Maker

[![PyPI version](https://img.shields.io/pypi/v/mcp-maker.svg)](https://pypi.org/project/mcp-maker/)
[![Python](https://img.shields.io/pypi/pyversions/mcp-maker.svg)](https://pypi.org/project/mcp-maker/)
[![Tests](https://github.com/MrAliHasan/mcp-maker/actions/workflows/tests.yml/badge.svg)](https://github.com/MrAliHasan/mcp-maker/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/MrAliHasan/mcp-maker/blob/main/LICENSE)

### ⚒️ Auto-generate MCP servers from any data source. Zero code required.

> Point MCP-Maker at a database, API, or file directory and get a fully functional [MCP](https://modelcontextprotocol.io/) server in seconds — ready for Claude, ChatGPT, Cursor, and any MCP-compatible AI.

---

## 🚀 Quick Start

```bash
pip install mcp-maker

# From a SQLite database
mcp-maker init sqlite:///my_database.db
mcp-maker serve

# From CSV/JSON files
mcp-maker init ./data/
mcp-maker serve

# That's it! Your AI can now query your data.
```

## Why MCP-Maker?

| | FastMCP | MCP-Maker |
|---|---------|----------|
| **Approach** | You write Python tools | It generates everything |
| **Setup time** | Minutes–hours | Seconds |
| **Code required** | Yes | No |
| **Best for** | Custom logic | Data access |

MCP-Maker uses FastMCP under the hood — it's not competing, it's building on top.

---

## 📋 Commands

| Command | Description |
|---------|-------------|
| `mcp-maker init <source>` | Generate an MCP server from a data source |
| `mcp-maker inspect <source>` | Preview what would be generated (dry run) |
| `mcp-maker serve` | Run the generated MCP server |
| `mcp-maker list-connectors` | Show available connectors |

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

Every connector is a single Python file — PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 🛠️ What Gets Generated

For each table in your data source, MCP-Maker generates:

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
$ mcp-maker init sqlite:///chinook.db

⚒️  MCP-Maker v0.1.0

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

$ mcp-maker serve
🚀 MCP-Maker Server running...
```

Now in Claude Desktop, add the server and ask: *"What are the top 5 artists with the most albums?"*

---

## 🔗 Use with Claude Desktop

Add the generated server to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "my-data": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop and your data is accessible via natural language!

---

## 🤝 Contributing

MCP-Maker is designed for community contributions — each new **connector** is a self-contained PR.

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed instructions and a step-by-step connector creation guide.

## 📦 Installation

```bash
# Core (SQLite + Files)
pip install mcp-maker

# With PostgreSQL support
pip install mcp-maker[postgres]

# With all connectors
pip install mcp-maker[all]

# Development
pip install mcp-maker[dev]
```

## 📄 License

This project is licensed under the [MIT License](LICENSE).
