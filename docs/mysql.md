# MySQL Connector

Connect to any MySQL or MariaDB database and auto-generate MCP tools for every table.

---

## Installation

```bash
pip install mcp-maker[mysql]
```

---

## Quick Start

```bash
mcp-maker init mysql://username:password@hostname:3306/database_name
mcp-maker serve
```

---

## URI Format

```
mysql://username:password@hostname:port/database_name
```

### Examples

```bash
# Local database
mcp-maker init mysql://root:password@localhost:3306/myapp

# Remote database
mcp-maker init mysql://admin:secret@db.example.com:3306/production

# Default port (3306)
mcp-maker init mysql://root:pass@localhost/mydb

# MariaDB (same format)
mcp-maker init mysql://user:pass@localhost:3306/mariadb_app
```

---

## Generated Tools

Same as SQLite and PostgreSQL — for each table:

### Read Tools

```
list_users(limit=50, offset=0)       → Paginated listing
get_users_by_id(id=1)                → Get by primary key
search_users(query="alice")           → Full-text search
count_users()                         → Row count
schema_users()                        → Column info
```

### Write Tools (with `--read-write`)

```bash
mcp-maker init mysql://user:pass@host/db --read-write
```

```
insert_users(name="Frank", email="frank@co.com")
update_users_by_id(id=1, name="Updated Name")
delete_users_by_id(id=1)
```

---

## Example

### Your MySQL database

```
wordpress_db
├── wp_posts (500 rows)         → ID, post_title, post_content, post_status
├── wp_users (50 rows)          → ID, user_login, user_email, display_name
└── wp_comments (2,000 rows)    → comment_ID, comment_content, comment_author
```

### Generate and run

```bash
mcp-maker init mysql://root:password@localhost:3306/wordpress_db
mcp-maker serve
```

### Ask Claude

> **You:** "How many published posts do we have?"
>
> **Claude:** *calls `search_wp_posts(query="publish")`*
> "You have 320 published posts."

> **You:** "Find comments by 'John'"
>
> **Claude:** *calls `search_wp_comments(query="John", limit=10)`*
> "Here are 10 comments by John..."

---

## Supported MySQL Types

| MySQL Type | Mapped To |
|-----------|----------|
| `int`, `bigint`, `smallint`, `tinyint`, `mediumint` | Integer |
| `float`, `double`, `decimal`, `numeric` | Float |
| `varchar`, `text`, `char`, `longtext`, `mediumtext` | String |
| `tinyint(1)`, `boolean` | Boolean |
| `date` | Date |
| `datetime`, `timestamp` | DateTime |
| `json` | JSON |
| `blob`, `longblob`, `binary`, `varbinary` | Binary |
| `enum`, `set` | String |

---

## Troubleshooting

### "pymysql not installed"

```bash
pip install mcp-maker[mysql]
```

### "Access denied"

- Verify username and password
- Check that the user has access from your host: `GRANT SELECT ON mydb.* TO 'user'@'%';`
- Flush privileges: `FLUSH PRIVILEGES;`

### "Can't connect to MySQL server"

- Check that MySQL is running: `mysqladmin ping`
- Verify hostname and port
- Check firewall settings for remote connections

### "Unknown character set"

Try adding charset to the URI:

```bash
mcp-maker init "mysql://user:pass@host:3306/db?charset=utf8mb4"
```
