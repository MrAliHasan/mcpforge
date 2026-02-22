# Semantic Search Guide

Search your data by **meaning**, not just keywords. Powered by ChromaDB vector search.

---

## Installation

```bash
pip install mcp-maker[semantic]
```

---

## Quick Start

```bash
# Generate a server with semantic search
mcp-maker init sqlite:///my.db --semantic

# Combine with other flags
mcp-maker init sqlite:///contacts.db --semantic --read-write
mcp-maker init postgres://user:pass@host/db --semantic --tables users,products
```

---

## What It Does

Regular search matches keywords. Semantic search matches **meaning**:

| Query | Keyword Search | Semantic Search |
|-------|---------------|----------------|
| "artificial intelligence" | ❌ Only finds records containing "artificial intelligence" | ✅ Also finds "machine learning", "deep learning", "neural networks" |
| "revenue growth" | ❌ Only exact matches | ✅ Also finds "sales increase", "profit improvement", "turnover rise" |
| "customer complaints" | ❌ Only exact matches | ✅ Also finds "user issues", "support tickets", "negative feedback" |

---

## Generated Tools

With `--semantic`, you get **two extra tools per table**:

| Tool | What It Does |
|------|-------------|
| `semantic_search_{table}(query, limit)` | Search by meaning, returns results ranked by similarity (0-1) |
| `rebuild_index_{table}()` | Force rebuild the vector index after data changes |

These are **in addition to** all the normal tools (`list`, `search`, `count`, `schema`, etc.).

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  First request to semantic_search_contacts("AI engineers")  │
│                                                             │
│  1. Reads all records from the data source                  │
│  2. Combines text fields into searchable documents          │
│  3. Embeds them using ChromaDB's default model              │
│     (all-MiniLM-L6-v2)                                      │
│  4. Stores vectors in local .chroma/ directory              │
│  5. Searches by cosine similarity                           │
│  6. Returns results ranked by score                         │
└─────────────────────────────────────────────────────────────┘

Subsequent searches → instant (index is already built and persisted)
```

The index is **built lazily** — only on the first semantic search call. After that, it's loaded from disk (`.chroma/` directory).

---

## Example

### Your database

```sql
-- contacts table
| id | name             | role            | company      |
|----|------------------|-----------------|--------------|
| 1  | Alice Johnson    | ML Engineer     | DeepMind     |
| 2  | Bob Smith        | Data Scientist  | OpenAI       |
| 3  | Carol Williams   | Sales Manager   | Salesforce   |
| 4  | Dave Brown       | Backend Dev     | Google       |
| 5  | Eve Davis        | NLP Researcher  | Anthropic    |
```

### Generate

```bash
mcp-maker init sqlite:///contacts.db --semantic
```

### Ask Claude

> **You:** "Find people who work in artificial intelligence"
>
> **Claude:** *calls `semantic_search_contacts(query="artificial intelligence")`*
> "Found 3 contacts related to AI:
> 1. Eve Davis — NLP Researcher at Anthropic (similarity: 0.92)
> 2. Alice Johnson — ML Engineer at DeepMind (similarity: 0.88)
> 3. Bob Smith — Data Scientist at OpenAI (similarity: 0.85)"

Note: None of these records contain "artificial intelligence" — but semantic search found them by **meaning**.

> **You:** "Search for frontend developers"
>
> **Claude:** First tries *`semantic_search_contacts(query="frontend developers")`*
> "No strong matches found for frontend developers. Your contacts are mostly in AI/ML and sales roles."

> **You:** "The data changed, rebuild the search index"
>
> **Claude:** *calls `rebuild_index_contacts()`*
> "Rebuilt the semantic search index for contacts. 5 records indexed."

---

## Keyword vs Semantic: When to Use Which

| Scenario | Use |
|----------|-----|
| Find "Alice" by name | `search_contacts(query="Alice")` — keyword |
| Find AI researchers | `semantic_search_contacts(query="AI research")` — semantic |
| Find exact email | `search_contacts(query="alice@acme.com")` — keyword |
| Find "people who handle money" | `semantic_search_contacts(query="finance")` — semantic |

Both tools are available simultaneously. Claude will pick the right one based on your question.

---

## Output Format

```json
[
  {
    "id": "5",
    "name": "Eve Davis",
    "role": "NLP Researcher",
    "company": "Anthropic",
    "similarity_score": 0.9234,
    "_document": "id: 5 | name: Eve Davis | role: NLP Researcher | company: Anthropic"
  },
  {
    "id": "1",
    "name": "Alice Johnson",
    "role": "ML Engineer",
    "company": "DeepMind",
    "similarity_score": 0.8812
  }
]
```

- `similarity_score` — 0 to 1, higher = more relevant
- `_document` — the text that was embedded (for debugging)

---

## Works With All Connectors

```bash
mcp-maker init sqlite:///my.db --semantic
mcp-maker init postgres://user:pass@host/db --semantic
mcp-maker init mysql://user:pass@host/db --semantic
mcp-maker init airtable://appXXXXX --semantic
mcp-maker init gsheet://SPREADSHEET_ID --semantic
mcp-maker init notion://DB_ID --semantic
mcp-maker init ./data/ --semantic
```

---

## Troubleshooting

### "chromadb not installed"

```bash
pip install mcp-maker[semantic]
```

### "Index seems outdated"

If your underlying data changed, rebuild the index:

```
Ask Claude: "Rebuild the search index for contacts"
```

Or programmatically: `rebuild_index_contacts()`

### ".chroma/ directory is large"

The `.chroma/` directory stores the vector index. For most datasets (< 100K records), it's a few MB. You can safely delete it — it will be rebuilt on the next semantic search.

### "First search is slow"

The first semantic search builds the index, which requires:
1. Reading all records from the source
2. Embedding them (using the local model)

Subsequent searches are instant. For large datasets, the first call may take 10-30 seconds.
