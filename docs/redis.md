# Redis Connector

Connect to any Redis database and auto-generate MCP tools for every key group.

```bash
pip install mcp-maker[redis]
```

---

## Quick Start

```bash
mcp-maker init redis://localhost:6379/0
mcp-maker serve
```

MCP-Maker scans your keys, groups them by prefix and type, and generates type-aware tools.

---

## URI Format

```
redis://localhost:6379/0                   # Local, no auth
redis://:password@host:6379/0              # With password
rediss://user:pass@host:6379/0             # With SSL (TLS)
redis://host:6379/2                        # Database 2
```

---

## What Gets Generated

MCP-Maker scans keys and generates **type-aware tools** based on the Redis data type:

### String Keys

```
list_users(pattern="users:*")     → List matching key-value pairs
get_users(key="users:123")        → Get a single value
count_users()                     → Count matching keys
set_users(key, value, ttl=None)   → Set a value (write mode)
delete_users(key)                 → Delete a key (delete mode)
```

### Hash Keys

```
list_sessions(pattern="sessions:*")  → List hashes with all fields
get_sessions(key)                     → Get all fields of a hash
search_sessions(query)                → Search hash values
count_sessions()                      → Count matching hashes
set_sessions(key, data={...})         → Set hash fields (write mode)
```

### List Keys

```
list_queues(pattern="queues:*")     → List keys with their elements
get_queues(key, start=0, stop=-1)   → Get list elements
push_queues(key, value, side)       → Push to list (write mode)
```

### Set Keys

```
list_tags(pattern="tags:*")     → List sets with members
get_tags(key)                    → Get all members
add_tags(key, member)            → Add to set (write mode)
```

### Sorted Set Keys

```
list_leaderboard(pattern="leaderboard:*")  → List sorted sets
get_leaderboard(key, start=0, stop=-1)      → Get with scores
add_leaderboard(key, member, score)          → Add with score (write mode)
```

### Always Generated

```
redis_info()           → Server info, db size, keyspace stats
publish_message(channel, message)  → Publish to a Pub/Sub channel
channel_list(pattern)              → List active channels
channel_subscribers(channel)       → Count subscribers on a channel
```

---

## Example: Complete Walkthrough

### 1. You have a Redis instance with keys

```
users:1       → hash {name: "Alice", email: "alice@co.com"}
users:2       → hash {name: "Bob", email: "bob@co.com"}
cache:page1   → string "<!DOCTYPE html>..."
queue:emails  → list ["msg1", "msg2"]
tags:popular  → set {"redis", "mcp", "ai"}
```

### 2. Generate the server

```bash
mcp-maker init redis://localhost:6379/0 --ops read,insert
```

```
⚒️ MCP-Maker                                         v0.3.0

  ✅ Connected to redis source

  ┌──────────────────────────────────────────────────────────┐
  │ 📊 Discovered Key Groups (4)                             │
  ├────────────┬────────────────────┬──────┬─────────────────┤
  │ Group      │ Type               │ Keys │ Sample Fields   │
  ├────────────┼────────────────────┼──────┼─────────────────┤
  │ users      │ hash               │    2 │ name, email     │
  │ cache      │ string             │    1 │ —               │
  │ queue      │ list               │    1 │ —               │
  │ tags       │ set                │    1 │ —               │
  └────────────┴────────────────────┴──────┴─────────────────┘

  🎉 Generated: mcp_server.py
```

### 3. Ask Claude

> **You:** "Search users for alice"
>
> **Claude:** *calls `search_users(query="alice")`*

> **You:** "What's in the tags:popular set?"
>
> **Claude:** *calls `get_tags(key="tags:popular")`*

---

## Key Grouping

MCP-Maker groups keys by **prefix** (everything before the first `:` or `.`):

```
users:1, users:2, users:3   → grouped as "users" (hash)
cache:page1, cache:page2     → grouped as "cache" (string)
myapp.sessions.abc           → grouped as "myapp" (hash)
```

If a key has no prefix delimiter, the full key name is used as its own group.

---

## Tips

- **Sampling**: MCP-Maker scans up to 1,000 keys to discover groups. Large databases with millions of keys will only show a subset.
- **Hash field discovery**: For hash keys, MCP-Maker inspects up to 10 sample keys to discover fields.
- **SSL**: Use `rediss://` for TLS-encrypted connections (e.g., Redis Cloud, AWS ElastiCache).
- **Glob patterns**: All `list_` tools accept a `pattern` argument for filtering keys.

---

## Troubleshooting

### "redis is required"

```bash
pip install mcp-maker[redis]
```

### "Cannot connect to Redis"

Make sure your Redis server is running:
```bash
redis-cli ping   # Should return PONG
```

### "No key groups found"

Your Redis database is empty. Add some keys first:
```bash
redis-cli SET "users:1" "Alice"
redis-cli HSET "session:abc" name "Bob" role "admin"
```
