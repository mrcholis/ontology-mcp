# Ontology MCP Server

**Turn ISO 20022 banking messages into a queryable knowledge graph — accessible to any AI agent via MCP.**

Banks, fintechs, and payment processors deal with thousands of ISO 20022 messages daily (pacs.008 payments, camt.056 cancellations, camt.029 responses). These XML files are dense, interconnected, and nearly impossible to query across — until now.

Ontology ingests ISO 20022 XML, extracts structured financial signals, builds an RDF knowledge graph, and exposes it as native tools that any MCP-compatible AI agent can use.

```bash
pip install ontology-mcp
python mcp_server.py
# Connect Claude Desktop, Cursor, or any MCP client
```

---

## Why This Exists

ISO 20022 is the global standard for financial messaging. Every payment, settlement, cancellation, and statement flows through it. But the data is trapped:

- **XML is not queryable** — finding "all transactions over $50K involving BLUEUSNY" means grepping through files
- **Messages are interconnected** — a camt.056 cancellation references a pacs.008 payment, but they live in separate XML files with no link
- **AI agents can't use it** — even with RAG, structured financial data resists naive chunking

Ontology solves all three by building a **typed, linked knowledge graph** with a natural-language interface.

---

## Quick Start

### 1. Install

```bash
pip install ontology-mcp
# Or with persistent storage:
pip install "ontology-mcp[oxigraph]"
```

### 2. Run the demo

```bash
python -m ontology_mcp.demo
```

This loads sample ISO 20022 messages and shows you what the graph looks like.

### 3. Fire up the server

```bash
python mcp_server.py
```

### 4. Connect to Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ontology": {
      "command": "python",
      "args": ["/path/to/ontology-mcp/mcp_server.py"]
    }
  }
}
```

Restart Claude. Now you can ask:

> *"Load the XML files from my messages folder and find all transactions above $50,000 involving BLUEUSNY"*

> *"What is the full lifecycle of cancellation case 20220718USDDSA9407803873?"*

> *"Are there any anomalies or balance mismatches in the loaded data?"*

---

## What You Can Do

| Tool | What it does |
|------|-------------|
| `extract_and_map` | Parse ISO 20022 XML → signals → RDF, merge into graph |
| `load_xml_file` | Load an XML file from disk and process it |
| `load_output_directory` | Load all pre-built .ttl files from a folder |
| `query_lifecycle` | Full message chain for a case ID / transaction ID / BIC |
| `sparql_query` | Run arbitrary SPARQL against the graph |
| `find_anomalies` | Flag high-value transactions, rejected cancellations, balance mismatches |
| `get_institution_activity` | All messages for a BIC code, with totals by type |
| `graph_stats` | Triple count, signal breakdown, BIC inventory |
| `start_stream_server` | Start a WebSocket server for streaming XML ingest |
| `push_stream_message` | Push an XML message over WebSocket in real-time |

### Supported Message Types

| Message | Description |
|---------|-------------|
| `pacs.008` | Payment initiation (FI → FI) |
| `pacs.009` | Payment settlement |
| `camt.053` | Account statement |
| `camt.054` | Debit/credit notification |
| `camt.056` | Cancellation request |
| `camt.026` | Unable to apply |
| `camt.029` | Cancellation response / resolution |

---

## Architecture

```
ISO 20022 XML
    |
    v
FinancialSignalExtractionPipeline   → extracts typed Python signal objects
    |
    v
FinancialSignalToRDFMapper          → maps signals to RDF triples
    |
    v
RDF Knowledge Graph (rdflib / Oxigraph)
    |  queryable via SPARQL
    v
MCP Tools (mcp_server.py)           → exposed over stdio transport
    |
    v
AI Agent / Claude Desktop
```

Persistent storage uses **Oxigraph** (RocksDB-backed). Falls back to in-memory rdflib if Oxigraph isn't installed.

---

## Examples

### Query a full payment lifecycle

```
User: What happened with cancellation case 20220718USDDSA9407803873BLUEUSNY001?

Agent: I found 4 messages in the lifecycle:

  1. pacs.008 — Payment initiated (BLUEUSNY → FEDNYUSS)
     $94,078.03 USD on 2022-07-18

  2. camt.056 — Cancellation requested by BLUEUSNY
     Reason: duplicate submission

  3. camt.029 — Cancellation rejected
     Reason: payment already settled

  4. camt.026 — Unable to apply notification sent to BLUEUSNY
```

### Find anomalies

```
User: Are there any unusual transactions?

Agent: Found 4 high-value transactions (>$50K):
  - TXN_20220718_001: $94,078.03 (BLUEUSNY → FEDNYUSS)
  ...

Found 1 rejected cancellation:
  - Case 20220718USDDSA9407803873: rejected (already settled)
```

---

## Development

```bash
git clone https://github.com/mrcholis/ontology-mcp
cd ontology-mcp
python3.11 -m venv venv311
source venv311/bin/activate
pip install -e ".[all]"

# Run tests
python _test_mcp_v2.py
```

---

## Roadmap

- [x] ISO 20022 message support (pacs.008/009, camt.053/054/056/026/029)
- [x] Persistent Oxigraph storage
- [x] WebSocket streaming ingest
- [ ] Production IRIs (replace `http://example.org/` namespaces)
- [ ] SPARQL HTTP endpoint
- [ ] `pain.001` / `pain.002` payment initiation messages
- [ ] Docker image for one-command deploy

---

## License

MIT
