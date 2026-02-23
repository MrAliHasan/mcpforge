# Files Connector (CSV, JSON, TXT)

Point MCP-Maker at a directory and it auto-generates tools for every file inside.

**No extra installation needed** — file support is built into the core `mcp-maker` package.

---

## Quick Start

```bash
mcp-maker init ./my-data/
mcp-maker serve
```

---

## URI Format

```bash
mcp-maker init ./data/              # Relative path to directory
mcp-maker init /absolute/path/data/ # Absolute path
```

---

## How Files Are Handled

| File Type | Treated As | What You Get |
|-----------|-----------|-------------|
| `.csv` | **Table** | list, search, count, schema tools |
| `.json` (array of objects) | **Table** | list, search, count, schema tools |
| `.txt`, `.md`, `.log` | **Resource** | read tool (returns content) |
| `.yaml`, `.toml`, `.xml` | **Resource** | read tool (returns content) |

---

## Example: Directory with Mixed Files

### Your directory structure

```
my-data/
├── customers.csv
├── products.json
├── README.md
└── config.txt
```

### `customers.csv`

```csv
id,name,email,city
1,Alice,alice@acme.com,NYC
2,Bob,bob@globex.com,London
3,Carol,carol@initech.com,Tokyo
```

### `products.json`

```json
[
  {"sku": "PRD-001", "name": "Widget", "price": 9.99, "category": "Tools"},
  {"sku": "PRD-002", "name": "Gadget", "price": 24.99, "category": "Electronics"},
  {"sku": "PRD-003", "name": "Doohickey", "price": 14.99, "category": "Tools"}
]
```

### Generate the server

```bash
mcp-maker init ./my-data/
```

```
⚒️ MCP-Maker                                         v0.2.3

  ✅ Connected to files source

  ┌───────────────────────────────────────────────────────┐
  │ 📊 Discovered Tables (2)                             │
  ├───────────┬──────────────────────────┬──────┬────────┤
  │ Table     │ Columns                  │ Rows │ PK     │
  ├───────────┼──────────────────────────┼──────┼────────┤
  │ customers │ id, name, email, city    │    3 │ —      │
  │ products  │ sku, name, price, ...    │    3 │ —      │
  └───────────┴──────────────────────────┴──────┴────────┘

  ┌───────────────────────────────────────────────────────┐
  │ 📄 Discovered Resources (2)                          │
  ├──────────┬───────────────────────────────────────────┤
  │ Name     │ Type                                      │
  ├──────────┼───────────────────────────────────────────┤
  │ readme   │ text/markdown                             │
  │ config   │ text/plain                                │
  └──────────┴───────────────────────────────────────────┘

  🎉 Generated: mcp_server.py
```

### Generated tools

**For CSV/JSON tables:**

```
list_customers(limit=50, offset=0)     → {results, total, has_more, next_offset}
search_customers(query="alice")         → Search across all columns
count_customers()                       → Total row count
schema_customers()                      → Column names & types
export_customers_csv()                  → Export as CSV string
export_customers_json()                 → Export as JSON string

list_products(limit=50, offset=0)      → {results, total, has_more, next_offset}
search_products(query="widget")         → Search products
count_products()                        → Count products
schema_products()                       → Product schema
export_products_csv()                   → Export as CSV string
export_products_json()                  → Export as JSON string
```

**Advanced list features:**

```
list_customers(fields="name,email")     → Column selection
list_customers(sort_field="name")       → Sorting
```

**For text files:**

```
read_readme()     → Returns the content of README.md
read_config()     → Returns the content of config.txt
```

### Ask Claude

> **You:** "What products do we have?"
>
> **Claude:** *calls `list_products()`*
> "You have 3 products: Widget ($9.99), Gadget ($24.99), and Doohickey ($14.99)."

> **You:** "Find all customers in NYC"
>
> **Claude:** *calls `search_customers(query="NYC")`*
> "I found 1 customer in NYC: Alice (alice@acme.com)."

> **You:** "Show me the README"
>
> **Claude:** *calls `read_readme()`*
> Shows the full content of README.md

---

## Column Type Inference

For CSV files, MCP-Maker infers types from the data:

| Data Pattern | Inferred Type | Example |
|-------------|--------------|---------|
| Numbers only | Integer | `1`, `42` |
| Decimal numbers | Float | `9.99`, `3.14` |
| Everything else | String | `"hello"` |

For JSON files, types come from the JSON:

| JSON Type | Mapped To |
|-----------|----------|
| `string` | String |
| `number` (int) | Integer |
| `number` (float) | Float |
| `boolean` | Boolean |
| `array` | JSON |
| `object` | JSON |

---

## Tips

- **File names become table names.** `customers.csv` → `customers` table, `product-list.json` → `product_list` table.
- **First row of CSV = headers.** Make sure your CSV has header names in row 1.
- **JSON must be an array of objects.** `[{"a":1}, {"a":2}]` works. `{"a":1}` alone is treated as a resource.
- **Nested directories** are not recursively scanned (only top-level files).

---

## Troubleshooting

### "No tables or resources found"

The directory exists but has no recognizable files.

**Fix:** Make sure your directory contains `.csv`, `.json`, `.txt`, or `.md` files.

### CSV parsing errors

If your CSV has unusual delimiters or encoding:

**Fix:** MCP-Maker uses Python's built-in CSV parser. Make sure your file uses commas as delimiters and UTF-8 encoding.
