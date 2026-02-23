# HubSpot Data-Bridge (mcp-maker)

The HubSpot connector allows your AI agent (like Claude Desktop) to natively interact with your HubSpot CRM. Unlike generic generic connectors, this operates as an **Enterprise Data-Bridge**:

1.  **Deep Schema-Awareness**: It reads your *exact* Custom Properties and UI Labels, so the AI understands your specific business terminology across Contacts, Companies, Deals, Tasks, Meetings, Calls, and Notes.
2.  **Context Maximization**: It maps `owner_ids` to human emails, pulls your actual Sales Pipeline stages, and reads your Audience Segmentation Lists automatically natively.
3.  **Compound Tools**: It uses advanced APIs like `search` and `batch_upsert` for high-speed, token-efficient data syncing.
4.  **Cross-Origin Sync**: You can connect HubSpot and a local SQL database simultaneously, allowing the AI to synchronize data between them.

## 🥊 Why MCP-Maker vs. Cloud Actors (like Apify)?

If you've seen cloud-hosted MCP servers that connect your AI to HubSpot, here is why `mcp-maker`'s Enterprise Data-Bridge is structurally superior:

*   **Zero Vendor Lock-in (Local First):** Cloud actors require you to send your highly sensitive HubSpot Private App Token through their 3rd-party servers, and usually charge per-API call. `mcp-maker` runs 100% locally on your machine. Your token never leaves your device.
*   **11+ Objects vs 4:** Commercial actors typically hardcode 4 standard objects (Contacts, Companies, Leads, Tasks). `mcp-maker` executes a Deep Auto-Discovery scan that maps **11+ items** (Deals, Tickets, Products, Quotes, Notes, Meetings, Calls, Emails) AND dynamically discovers all of your **Custom Objects**.
*   **High-Volume Context:** Commercial wrappers only do basic 1-by-1 reads and writes. Our `batch_upsert` and Context Maximization (`hubspot_get_owners`, `pipelines`) tools expose the actual enterprise CRM logic to your AI natively.

## 1. Authentication (Private App Tokens)

MCP-Maker uses **Private App Access Tokens (PATs)** for authentication. This is the most secure and frictionless way to connect, keeping your data entirely local to your machine without OAuth redirects.

### How to get your Token:
1. Log into HubSpot and click the **Settings icon** (⚙️) in the main navigation bar.
2. In the left sidebar, navigate to **Integrations > Private Apps**.
3. Click **Create a private app**.
4. Name your app (e.g., `Local MCP Bridge`).
5. Go to the **Scopes** tab and check the following required scopes:
   - `crm.objects.contacts.read` & `.write`
   - `crm.objects.companies.read` & `.write`
   - `crm.objects.deals.read` & `.write`
   - `crm.objects.custom.read` & `.write` (Optional, for custom objects)
   - `crm.schemas.contacts.read` & `.write` (Required for auto-mapping custom properties)
   - **Context Scopes (Recommended)**: 
     - `crm.objects.owners.read` (Maps internal IDs to Human User Emails)
     - `crm.lists.read` (Allows AI to read Audience Segments)
     - `tickets` (Required if you use Service Hub)
6. Click **Create app** and copy the generated token.

## 2. Generating the Server

You can authenticate in two ways.

**Option A: Environment Variable (Recommended for security)**

```bash
# Save your token securely
mcp-maker env set HUBSPOT_ACCESS_TOKEN pat-na1-xxxx-xxxx-xxxx

# Initialize the server
mcp-maker init hubspot://
```

**Option B: Direct URI string**

```bash
mcp-maker init hubspot://pat=pat-na1-xxxx-xxxx-xxxx
```

## 3. High-Value Compound Tools Generated

MCP-Maker generates native REST wrappers leveraging the standard `requests` library. Your AI will automatically gain access to:

-   `list_{table}` / `get_{table}_by_id` : Standard retrieve capabilities.
-   `create_{table}` / `update_{table}_by_id` : Single-record mutations.
-   `delete_{table}_by_id` : Archive records.

**Enterprise "Data-Bridge" Features:**
-   **`hubspot_search_crm_objects`**: Exposes the full HubSpot `filterGroups` JSON schema, allowing the AI to query complex logic (e.g. "Find all Deals closed last month > $5000").
-   **`batch_upsert_{table}`**: Exposes HubSpot's bulk update endpoints. By passing an array of contacts and an `id_property` (e.g. `email`), the AI can synchronize dozens of local database records into HubSpot in a single API round trip.
-   **`hubspot_associate_objects`**: Allows the AI to programmatically link standard and custom objects together.
-   **`hubspot_log_timeline_event`**: Exposes the Behavioral Events API so the AI can leave custom milestones directly on a Contact's timeline.

**Context Maximization Tools:**
-   **`hubspot_get_owners`**: Returns human names and emails so the AI knows who `owner_id: 12345` is.
-   **`hubspot_get_deal_pipelines`**: Pulls your actual Sales pipelines, stage names, and win probabilities directly into context.
-   **`hubspot_get_lists`**: Returns your CRM Audience Segments so you can command the AI to operate on specific groups (e.g. "Sync all contacts in the 'VIP Buyers' list").

## 4. Rate Limiting Protection

Free/Starter HubSpot tiers allow a maximum of 10-15 API calls per second. MCP-Maker automatically injects a `TokenBucketRateLimiter` configured for **4 requests per second** natively into the generated `mcp_server.py`.

This guarantees your LLM will not trigger a temporary API ban (`429 Too Many Requests`) when executing highly parallel tool calls.

## Example: Building a Data-Sync Bridge

By combining connectors, you can instruct your LLM to perform data harmonization.

**Setup:**
```bash
mcp-maker init sqlite:///local_leads.db hubspot://
mcp-maker config --install
```

**Prompting Claude:**
> *"Read all leads lacking a 'Synced' status from SQLite. For each lead, execute a `batch_upsert_contacts` using their email as the unique ID to push them into HubSpot. Then, update the SQLite database to mark them as Synced."*
