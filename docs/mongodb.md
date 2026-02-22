# MongoDB Connector

Connect to any MongoDB database and auto-generate MCP tools for every collection.

```bash
pip install mcp-maker[mongodb]
```

---

## Quick Start

```bash
mcp-maker init mongodb://localhost:27017/mydb
mcp-maker serve
```

Every collection now has list, search, count, insert, update, and delete tools.

---

## URI Format

```
mongodb://localhost:27017/mydb                    # Local, no auth
mongodb://user:pass@host:27017/mydb               # With authentication
mongodb+srv://user:pass@cluster.mongodb.net/mydb   # MongoDB Atlas (SRV)
```

> **Important:** The database name is required in the URI path.

---

## What Gets Generated

For each collection, MCP-Maker samples 100 documents to infer the schema, then generates:

### Read Tools

```
list_users(limit=50, offset=0)        → Paginated listing
get_users_by_id(id="64a...")           → Get by ObjectId (_id)
search_users(query="alice")            → Regex search across text fields
count_users()                          → Estimated document count
schema_users()                         → Field names & inferred types
```

### Write Tools (with `--ops read,insert,update,delete`)

```bash
mcp-maker init mongodb://localhost:27017/mydb --ops read,insert,update,delete
```

```
insert_users(data={...})                → Insert a document
update_users_by_id(id="64a...", data={...}) → Update by _id
delete_users_by_id(id="64a...")         → Delete by _id
```

---

## Example: Complete Walkthrough

### 1. Generate the server

```bash
mcp-maker init mongodb://localhost:27017/ecommerce --ops read,insert
```

```
⚒️ MCP-Maker                                         v0.3.0

  ✅ Connected to mongodb source

  ┌──────────────────────────────────────────────────────────┐
  │ 📊 Discovered Collections (3)                            │
  ├───────────┬──────────────────────────────┬───────┬───────┤
  │ Collection│ Fields                       │ Docs  │ PK    │
  ├───────────┼──────────────────────────────┼───────┼───────┤
  │ products  │ _id, name, price, category   │ 1,200 │ _id   │
  │ orders    │ _id, user_id, total, items   │ 5,000 │ _id   │
  │ users     │ _id, email, name, created    │   350 │ _id   │
  └───────────┴──────────────────────────────┴───────┴───────┘

  🎉 Generated: mcp_server.py
```

### 2. Run and connect

```bash
mcp-maker serve
mcp-maker config --install
```

### 3. Ask Claude

> **You:** "Search for products in the electronics category"
>
> **Claude:** *calls `search_products(query="electronics")`*

> **You:** "Insert a new user with email john@example.com"
>
> **Claude:** *calls `insert_users(data={"email": "john@example.com", "name": "John"})`*

---

## Type Mapping

MCP-Maker maps BSON/Python types from sampled documents:

| BSON Type | Mapped To | Example |
|-----------|-----------|---------|
| `str` | String | `"hello"` |
| `int` | Integer | `42` |
| `float` | Float | `3.14` |
| `bool` | Boolean | `true` |
| `datetime` | DateTime | `ISODate("2024-01-15")` |
| `ObjectId` | String | `"64a7b3..."` |
| `list`, `dict` | JSON | `[1, 2, 3]`, `{"key": "val"}` |

---

## Tips

- **ObjectId handling**: `_id` fields are automatically converted to strings for JSON serialization. You can pass string IDs to `get_by_id` / `update_by_id` / `delete_by_id`.
- **Schema inference**: MCP-Maker samples the first 100 documents. If your collection has varied schemas, some fields may be missing.
- **System collections** (`system.*`) are automatically excluded.
- **Estimated counts**: `count_` tools use `estimated_document_count()` for performance.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Auto-set | Your MongoDB connection string (set automatically from the URI) |

For MongoDB Atlas with authentication, your URI already contains credentials.

---

## Troubleshooting

### "pymongo is required"

```
ImportError: pymongo is required for MongoDB support.
```

**Fix:**
```bash
pip install mcp-maker[mongodb]
```

### "MongoDB URI must include a database name"

```
ValueError: MongoDB URI must include a database name.
```

**Fix:** Add the database name to your URI path:
```bash
# ❌ Wrong
mcp-maker init mongodb://localhost:27017

# ✅ Correct
mcp-maker init mongodb://localhost:27017/mydb
```

### "Cannot connect to MongoDB"

Check that your MongoDB server is running and accessible:
```bash
mongosh mongodb://localhost:27017
```
