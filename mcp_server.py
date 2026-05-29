"""
Ontology MCP Server  v2.0
#
# Exposes the financial ontology pipeline as MCP tools for AI agents.

New in v2:
  - Persistent storage via pyoxigraph (survives server restarts)
  - pacs.008 / pacs.009 message support (full payment chain)
  - WebSocket streaming server (start_stream_server / push_stream_message)

All 8 original tools + 2 streaming tools.

Usage (stdio MCP server):
  python mcp_server.py

Claude Desktop config: see mcp_config.json
"""

import sys
import os
import json
import threading
import asyncio
from pathlib import Path
from typing import Optional

# ── project root on path ───────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server.fastmcp import FastMCP
from rdflib import Graph, Namespace, RDF, Literal, URIRef, XSD

from src.signals.financial_signal_extraction import FinancialSignalExtractionPipeline
from src.ontology.financial_ontology_mapper import FinancialSignalToRDFMapper

# ── namespaces ─────────────────────────────────────────────────────────────
FIN  = Namespace("http://example.org/financial/ontology#")
INST = Namespace("http://example.org/financial/instance#")
ISO  = Namespace("http://example.org/iso20022/ontology#")

# ── persistent store (Oxigraph) ────────────────────────────────────────────
STORE_PATH = PROJECT_ROOT / "graph_store"

try:
    import pyoxigraph as ox

    _ox_store = ox.Store(str(STORE_PATH))
    _USE_OXIGRAPH = True

    def _graph_triple_count() -> int:
        return sum(1 for _ in _ox_store.quads_for_pattern(None, None, None, None))

    def _graph_query_sparql(sparql: str):
        """Run a SPARQL SELECT against the Oxigraph store, return list of dicts."""
        result = _ox_store.query(sparql)
        rows = []
        variables = result.variables  # list of pyoxigraph.Variable (names include '?')
        var_names = [str(v).lstrip('?') for v in variables]
        for row in result:
            d = {}
            for i, name in enumerate(var_names):
                val = row[i]
                if val is not None:
                    d[name] = str(val)
            rows.append(d)
        return rows

    def _add_rdflib_graph_to_store(g: Graph):
        """Merge an rdflib Graph into the Oxigraph store."""
        turtle = g.serialize(format="turtle")
        _ox_store.load(turtle.encode(), format=ox.RdfFormat.TURTLE)

    def _load_ttl_file_to_store(path: str):
        with open(path, "rb") as f:
            _ox_store.load(f.read(), format=ox.RdfFormat.TURTLE)

except ImportError:
    _USE_OXIGRAPH = False
    # Fallback: pure rdflib in-memory graph
    _fallback_graph: Graph = Graph()
    _fallback_graph.bind("fin", FIN)
    _fallback_graph.bind("inst", INST)
    _fallback_graph.bind("iso20022", ISO)

    def _graph_triple_count() -> int:
        return len(_fallback_graph)

    def _graph_query_sparql(sparql: str):
        preamble = _sparql_preamble()
        result = _fallback_graph.query(preamble + sparql if "PREFIX fin:" not in sparql else sparql)
        return [{str(var): str(row[var]) for var in result.vars if row[var] is not None} for row in result]

    def _add_rdflib_graph_to_store(g: Graph):
        for triple in g:
            _fallback_graph.add(triple)

    def _load_ttl_file_to_store(path: str):
        _fallback_graph.parse(path, format="turtle")


def _sparql_preamble() -> str:
    return """
PREFIX rdf:      <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:     <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:      <http://www.w3.org/2002/07/owl#>
PREFIX xsd:      <http://www.w3.org/2001/XMLSchema#>
PREFIX fin:      <http://example.org/financial/ontology#>
PREFIX inst:     <http://example.org/financial/instance#>
PREFIX iso20022: <http://example.org/iso20022/ontology#>
"""

# ── pipeline + mapper ──────────────────────────────────────────────────────
_pipeline = FinancialSignalExtractionPipeline()
_ontology_path = PROJECT_ROOT / "src" / "ontology" / "schema" / "financial_ontology.ttl"
_mapper = FinancialSignalToRDFMapper(
    ontology_file=str(_ontology_path) if _ontology_path.exists() else None
)

# ── streaming state ────────────────────────────────────────────────────────
_stream_server_thread: Optional[threading.Thread] = None
_stream_server_port: int = 8765
_stream_messages_received: int = 0

# ── MCP server ─────────────────────────────────────────────────────────────
mcp = FastMCP(
    name="ontology",
    instructions=(
        "Financial ontology server (v2). Converts ISO 20022 XML messages into a persistent RDF "
        "knowledge graph (Oxigraph) and lets you query it with SPARQL. "
        "Supports pacs.008 (payment initiation), pacs.009 (settlement), camt.026/029/053/056. "
        "Use extract_and_map or load_xml_file to ingest, then query_lifecycle / sparql_query / "
        "find_anomalies to reason over data. Use start_stream_server for live ingest."
    ),
)

# ── helpers ────────────────────────────────────────────────────────────────

def _signals_to_summary(signals) -> list:
    rows = []
    for s in signals:
        d = {
            "type": s.signal_type.value if hasattr(s.signal_type, "value") else str(s.signal_type),
            "message_id": getattr(s, "message_id", None),
            "timestamp": str(getattr(s, "timestamp", "")),
            "confidence": getattr(s, "confidence", 1.0),
        }
        for attr in ("case_id", "transaction_id", "end_to_end_id", "instruction_id",
                     "settlement_date", "settlement_method", "status_code",
                     "cancellation_reason_code", "account_id"):
            val = getattr(s, attr, None)
            if val:
                d[attr] = val
        if hasattr(s, "amount") and s.amount:
            d["amount"] = {"value": s.amount.value, "currency": s.amount.currency}
        for inst_attr, key in [("assignor", "from_bic"), ("assignee", "to_bic"),
                                ("debtor_agent", "from_bic"), ("creditor_agent", "to_bic")]:
            inst = getattr(s, inst_attr, None)
            if inst:
                d[key] = str(inst)
        rows.append(d)
    return rows


_KNOWN_TYPES_VALUES = " ".join([
    "<http://example.org/financial/ontology#PaymentCancellation>",
    "<http://example.org/financial/ontology#InvestigationResolution>",
    "<http://example.org/financial/ontology#UnableToApply>",
    "<http://example.org/financial/ontology#AccountStatement>",
    "<http://example.org/financial/ontology#PaymentInitiation>",
    "<http://example.org/financial/ontology#PaymentSettlement>",
    "<http://example.org/financial/ontology#AccountTransaction>",
])


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 1 — extract_and_map
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def extract_and_map(xml_content: str) -> str:
    """
    Parse an ISO 20022 XML string (pacs.008, pacs.009, camt.026/029/053/056),
    extract financial signals, map to RDF, and persist to the Oxigraph store.

    Returns a JSON summary of extracted signals and triple counts.
    The data is immediately queryable via sparql_query, query_lifecycle, etc.
    """
    try:
        signals = _pipeline.extract(xml_content)
        if not signals:
            return json.dumps({"status": "no_signals",
                               "message": "No ISO 20022 signals detected."})

        before = _graph_triple_count()
        for sig in signals:
            local_g = _mapper.map_signal(sig)
            if local_g:
                _add_rdflib_graph_to_store(local_g)
        after = _graph_triple_count()

        return json.dumps({
            "status": "ok",
            "storage": "oxigraph_persistent" if _USE_OXIGRAPH else "rdflib_memory",
            "signals_extracted": len(signals),
            "triples_added": after - before,
            "total_graph_triples": after,
            "signals": _signals_to_summary(signals),
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 2 — load_xml_file
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def load_xml_file(file_path: str) -> str:
    """
    Load an ISO 20022 XML file from disk, extract signals, and persist to the graph store.

    file_path: absolute or relative path (relative resolves from Ontology project root).
    Supports: pacs.008, pacs.009, camt.026, camt.029, camt.053, camt.056
    """
    try:
        p = Path(file_path)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        if not p.exists():
            return json.dumps({"status": "error", "error": f"File not found: {p}"})

        xml_content = p.read_text(encoding="utf-8")
        result = json.loads(extract_and_map(xml_content))
        result["file"] = str(p)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 3 — load_output_directory
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def load_output_directory(directory: str = "output") -> str:
    """
    Load all pre-generated .ttl RDF files from a directory into the persistent store.

    directory: path to folder with .ttl files (default: 'output').
    """
    try:
        d = Path(directory)
        if not d.is_absolute():
            d = PROJECT_ROOT / d
        if not d.exists():
            return json.dumps({"status": "error", "error": f"Directory not found: {d}"})

        ttl_files = list(d.glob("*.ttl"))
        if not ttl_files:
            return json.dumps({"status": "error", "error": f"No .ttl files in {d}"})

        before = _graph_triple_count()
        loaded, errors = [], []
        for f in ttl_files:
            try:
                _load_ttl_file_to_store(str(f))
                loaded.append(f.name)
            except Exception as e:
                errors.append({"file": f.name, "error": str(e)})

        return json.dumps({
            "status": "ok",
            "storage": "oxigraph_persistent" if _USE_OXIGRAPH else "rdflib_memory",
            "files_loaded": loaded,
            "errors": errors,
            "triples_added": _graph_triple_count() - before,
            "total_graph_triples": _graph_triple_count(),
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 4 — query_lifecycle
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def query_lifecycle(identifier: str) -> str:
    """
    Retrieve the full payment lifecycle for a case ID, transaction ID, message ID, or BIC.
    Returns all matching signals in chronological order with their key properties.

    identifier: case ID / transaction ID / message ID / BIC code (substring match).
    """
    try:
        if _graph_triple_count() == 0:
            return json.dumps({"status": "empty_graph",
                               "message": "No data loaded. Use load_xml_file first."})

        q = _sparql_preamble() + f"""
SELECT ?signal ?type ?timestamp ?messageId ?caseId ?transactionId
       ?amount ?currency ?fromBIC ?toBIC ?statusCode ?reasonCode
       ?settlementDate ?settlementMethod ?endToEndId
WHERE {{
    VALUES ?type {{ {_KNOWN_TYPES_VALUES} }}
    ?signal a ?type .
    OPTIONAL {{ ?signal fin:timestamp       ?timestamp       }}
    OPTIONAL {{ ?signal fin:messageId       ?messageId       }}
    OPTIONAL {{ ?signal fin:caseId          ?caseId          }}
    OPTIONAL {{ ?signal fin:transactionId   ?transactionId   }}
    OPTIONAL {{ ?signal fin:endToEndId      ?endToEndId      }}
    OPTIONAL {{ ?signal fin:statusCode      ?statusCode      }}
    OPTIONAL {{ ?signal fin:settlementDate  ?settlementDate  }}
    OPTIONAL {{ ?signal fin:settlementMethod ?settlementMethod }}
    OPTIONAL {{ ?signal fin:hasReason ?r . ?r fin:reasonCode ?reasonCode }}
    OPTIONAL {{
        ?signal fin:hasAmount ?amtNode .
        ?amtNode fin:value    ?amount .
        ?amtNode fin:currency ?currency .
    }}
    OPTIONAL {{ ?signal fin:fromInstitution ?fi . ?fi fin:bic ?fromBIC }}
    OPTIONAL {{ ?signal fin:toInstitution   ?ti . ?ti fin:bic ?toBIC   }}
    FILTER(
        CONTAINS(LCASE(STR(?caseId)),        LCASE("{identifier}")) ||
        CONTAINS(LCASE(STR(?transactionId)), LCASE("{identifier}")) ||
        CONTAINS(LCASE(STR(?messageId)),     LCASE("{identifier}")) ||
        CONTAINS(LCASE(STR(?endToEndId)),    LCASE("{identifier}")) ||
        CONTAINS(LCASE(STR(?fromBIC)),       LCASE("{identifier}")) ||
        CONTAINS(LCASE(STR(?toBIC)),         LCASE("{identifier}")) ||
        CONTAINS(LCASE(STR(?signal)),        LCASE("{identifier}"))
    )
}}
ORDER BY ?timestamp
"""
        rows = _graph_query_sparql(q)
        if not rows:
            return json.dumps({"status": "not_found", "identifier": identifier,
                               "message": "No messages matched."})

        return json.dumps({"status": "ok", "identifier": identifier,
                           "message_count": len(rows), "messages": rows}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 5 — sparql_query
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def sparql_query(query: str) -> str:
    """
    Execute an arbitrary SPARQL SELECT query against the persistent knowledge graph.

    Standard prefixes are pre-bound (fin, inst, iso20022, rdf, rdfs, owl, xsd).
    Returns JSON with columns and row array.

    Example:
      SELECT ?signal ?amount WHERE {
        ?signal a fin:PaymentInitiation ;
                fin:hasAmount ?a .
        ?a fin:value ?amount .
        FILTER(?amount > 50000)
      } ORDER BY DESC(?amount)
    """
    try:
        if _graph_triple_count() == 0:
            return json.dumps({"status": "empty_graph",
                               "message": "No data loaded. Use load_xml_file first."})

        full_q = (_sparql_preamble() + query
                  if "PREFIX fin:" not in query and "prefix fin:" not in query
                  else query)
        rows = _graph_query_sparql(full_q)

        # Extract column names from first row keys
        cols = list(rows[0].keys()) if rows else []
        return json.dumps({"status": "ok", "row_count": len(rows),
                           "columns": cols, "rows": rows}, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 6 — find_anomalies
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def find_anomalies(high_value_threshold: float = 100000.0, currency: str = "USD") -> str:
    """
    Scan the knowledge graph for anomalies:
      - High-value transactions above threshold
      - Rejected / non-accepted investigation resolutions (camt.029)
      - Unable-to-apply messages (camt.026)
      - Account statement balance mismatches (camt.053)

    high_value_threshold: flag amounts above this (default 100000).
    currency: filter by currency code, e.g. 'USD'. Pass '' for all currencies.
    """
    try:
        if _graph_triple_count() == 0:
            return json.dumps({"status": "empty_graph", "message": "No data loaded."})

        cur_filter = f'FILTER(STR(?currency) = "{currency}")' if currency else ""

        hv_q = _sparql_preamble() + f"""
SELECT ?signal ?type ?amount ?currency ?fromBIC ?toBIC ?timestamp
WHERE {{
    VALUES ?type {{ {_KNOWN_TYPES_VALUES} }}
    ?signal a ?type .
    ?signal fin:hasAmount ?amtNode .
    ?amtNode fin:value    ?amount .
    ?amtNode fin:currency ?currency .
    OPTIONAL {{ ?signal fin:timestamp ?timestamp }}
    OPTIONAL {{ ?signal fin:fromInstitution ?fi . ?fi fin:bic ?fromBIC }}
    OPTIONAL {{ ?signal fin:toInstitution   ?ti . ?ti fin:bic ?toBIC   }}
    FILTER(?amount > {high_value_threshold})
    {cur_filter}
}} ORDER BY DESC(?amount)
"""

        rej_q = _sparql_preamble() + """
SELECT ?signal ?statusCode ?caseId ?timestamp ?fromBIC
WHERE {
    ?signal a fin:InvestigationResolution .
    ?signal fin:statusCode ?statusCode .
    OPTIONAL { ?signal fin:caseId ?caseId }
    OPTIONAL { ?signal fin:timestamp ?timestamp }
    OPTIONAL { ?signal fin:fromInstitution ?fi . ?fi fin:bic ?fromBIC }
    FILTER(?statusCode NOT IN ("ACCP","ACSC","ACSP"))
}
"""

        uta_q = _sparql_preamble() + """
SELECT ?signal ?caseId ?timestamp ?justificationCode ?fromBIC
WHERE {
    ?signal a fin:UnableToApply .
    OPTIONAL { ?signal fin:caseId ?caseId }
    OPTIONAL { ?signal fin:timestamp ?timestamp }
    OPTIONAL { ?signal fin:justificationCode ?justificationCode }
    OPTIONAL { ?signal fin:fromInstitution ?fi . ?fi fin:bic ?fromBIC }
}
"""

        bal_q = _sparql_preamble() + """
SELECT ?signal ?statementId ?balanceValid
WHERE {
    ?signal a fin:AccountStatement .
    ?signal fin:balanceValid ?balanceValid .
    OPTIONAL { ?signal fin:statementId ?statementId }
    FILTER(STR(?balanceValid) = "false")
}
"""

        hv   = _graph_query_sparql(hv_q)
        rej  = _graph_query_sparql(rej_q)
        uta  = _graph_query_sparql(uta_q)
        bal  = _graph_query_sparql(bal_q)

        return json.dumps({
            "status": "ok",
            "total_anomalies": len(hv) + len(rej) + len(uta) + len(bal),
            "high_value_transactions": {"count": len(hv), "threshold": high_value_threshold,
                                        "currency_filter": currency or "all", "items": hv},
            "rejected_cancellations":  {"count": len(rej), "items": rej},
            "unable_to_apply":         {"count": len(uta), "items": uta},
            "balance_mismatches":      {"count": len(bal), "items": bal},
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 7 — get_institution_activity
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def get_institution_activity(bic: str) -> str:
    """
    Summarise all messages involving a specific bank by BIC code.
    Returns message counts by type, total value, and chronological list.

    bic: SWIFT/BIC code, e.g. 'BLUEUSNY001' (case-insensitive substring match).
    """
    try:
        if _graph_triple_count() == 0:
            return json.dumps({"status": "empty_graph", "message": "No data loaded."})

        q = _sparql_preamble() + f"""
SELECT ?signal ?type ?timestamp ?amount ?currency ?direction ?otherBIC
WHERE {{
    VALUES ?type {{ {_KNOWN_TYPES_VALUES} }}
    {{
        ?signal a ?type .
        ?signal fin:fromInstitution ?inst .
        ?inst fin:bic ?bic .
        BIND("outgoing" AS ?direction)
        OPTIONAL {{ ?signal fin:toInstitution ?oi . ?oi fin:bic ?otherBIC }}
    }} UNION {{
        ?signal a ?type .
        ?signal fin:toInstitution ?inst .
        ?inst fin:bic ?bic .
        BIND("incoming" AS ?direction)
        OPTIONAL {{ ?signal fin:fromInstitution ?oi . ?oi fin:bic ?otherBIC }}
    }}
    FILTER(CONTAINS(LCASE(STR(?bic)), LCASE("{bic}")))
    OPTIONAL {{ ?signal fin:timestamp ?timestamp }}
    OPTIONAL {{
        ?signal fin:hasAmount ?amtNode .
        ?amtNode fin:value    ?amount .
        ?amtNode fin:currency ?currency .
    }}
}} ORDER BY ?timestamp
"""
        rows = _graph_query_sparql(q)
        if not rows:
            return json.dumps({"status": "not_found", "bic": bic,
                               "message": "No messages found for this BIC."})

        type_counts: dict = {}
        total_value = 0.0
        for r in rows:
            t = r.get("type", "unknown").split("#")[-1]
            type_counts[t] = type_counts.get(t, 0) + 1
            try:
                total_value += float(r.get("amount", 0) or 0)
            except (ValueError, TypeError):
                pass

        return json.dumps({
            "status": "ok", "bic": bic,
            "total_messages": len(rows), "total_value": round(total_value, 2),
            "by_type": type_counts, "messages": rows,
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 8 — graph_stats
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def graph_stats() -> str:
    """
    Return statistics about the persistent RDF knowledge graph:
    triple count, signal type breakdown, BIC inventory, and storage backend.
    """
    try:
        triple_count = _graph_triple_count()
        if triple_count == 0:
            return json.dumps({
                "status": "empty",
                "storage": "oxigraph_persistent" if _USE_OXIGRAPH else "rdflib_memory",
                "store_path": str(STORE_PATH) if _USE_OXIGRAPH else "n/a",
                "message": "No data loaded. Use load_xml_file or load_output_directory.",
                "total_triples": 0,
            })

        type_q = _sparql_preamble() + f"""
SELECT ?type (COUNT(?s) AS ?count)
WHERE {{
    VALUES ?type {{ {_KNOWN_TYPES_VALUES} }}
    ?s a ?type .
}} GROUP BY ?type ORDER BY DESC(?count)
"""
        bic_q = _sparql_preamble() + """
SELECT DISTINCT ?bic WHERE { ?inst fin:bic ?bic } ORDER BY ?bic
"""
        type_rows = _graph_query_sparql(type_q)
        bic_rows  = _graph_query_sparql(bic_q)

        def _parse_int(val: str) -> int:
            """Parse Oxigraph typed literal like '"4"^^<xsd:integer>' or plain '4'."""
            import re
            m = re.search(r'"(\d+)"', val)
            return int(m.group(1)) if m else int(val)

        types_summary = {
            r["type"].split("#")[-1].rstrip(">"): _parse_int(r["count"])
            for r in type_rows if "type" in r and "count" in r
        }
        bics = [r["bic"].strip('"') for r in bic_rows if "bic" in r]

        return json.dumps({
            "status": "ok",
            "storage": "oxigraph_persistent" if _USE_OXIGRAPH else "rdflib_memory",
            "store_path": str(STORE_PATH) if _USE_OXIGRAPH else "n/a",
            "total_triples": triple_count,
            "signal_types": types_summary,
            "total_signals": sum(types_summary.values()),
            "institutions_bics": bics,
            "institution_count": len(bics),
            "stream_messages_received": _stream_messages_received,
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 9 — start_stream_server
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def start_stream_server(port: int = 8765) -> str:
    """
    Start a WebSocket server that accepts live ISO 20022 XML messages and
    ingests them directly into the persistent knowledge graph in real time.

    Clients connect to ws://localhost:<port> and send raw XML strings.
    Each message is extracted, mapped to RDF, and persisted automatically.

    port: WebSocket port to listen on (default 8765).

    Returns immediately — server runs in a background thread.
    Use graph_stats to see messages_received counter increase.
    """
    global _stream_server_thread, _stream_server_port

    if _stream_server_thread and _stream_server_thread.is_alive():
        return json.dumps({"status": "already_running", "port": _stream_server_port,
                           "message": f"Stream server already running on port {_stream_server_port}"})

    _stream_server_port = port

    def _run_ws_server():
        """WebSocket server in its own event loop (background thread)."""
        import asyncio
        try:
            import websockets
        except ImportError:
            return  # websockets not installed — handled below

        global _stream_messages_received

        async def _handle(websocket):
            global _stream_messages_received
            async for message in websocket:
                try:
                    signals = _pipeline.extract(message)
                    triples_added = 0
                    for sig in signals:
                        local_g = _mapper.map_signal(sig)
                        if local_g:
                            _add_rdflib_graph_to_store(local_g)
                            triples_added += len(local_g)
                    _stream_messages_received += 1
                    ack = json.dumps({
                        "status": "ok",
                        "signals": len(signals),
                        "triples_added": triples_added,
                        "total_received": _stream_messages_received,
                    })
                    await websocket.send(ack)
                except Exception as e:
                    await websocket.send(json.dumps({"status": "error", "error": str(e)}))

        async def _serve():
            async with websockets.serve(_handle, "localhost", port):
                await asyncio.Future()  # run forever

        asyncio.run(_serve())

    # Check websockets is available
    try:
        import websockets  # noqa
        ws_available = True
    except ImportError:
        ws_available = False

    if not ws_available:
        return json.dumps({
            "status": "missing_dependency",
            "message": "Install websockets: pip install websockets",
        })

    _stream_server_thread = threading.Thread(target=_run_ws_server, daemon=True)
    _stream_server_thread.start()

    return json.dumps({
        "status": "started",
        "port": port,
        "url": f"ws://localhost:{port}",
        "message": (
            f"WebSocket stream server started on ws://localhost:{port}. "
            "Send raw ISO 20022 XML to ingest in real time. "
            "Use graph_stats to monitor ingestion."
        ),
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# TOOL 10 — push_stream_message  (test / manual ingest without WebSocket client)
# ═══════════════════════════════════════════════════════════════════════════
@mcp.tool()
def push_stream_message(xml_content: str) -> str:
    """
    Directly ingest an ISO 20022 XML message into the persistent graph,
    simulating what the WebSocket stream server does for each live message.

    Useful for testing the streaming pipeline without a WebSocket client,
    or for one-off message ingestion from scripts.
    """
    global _stream_messages_received
    try:
        signals = _pipeline.extract(xml_content)
        if not signals:
            return json.dumps({"status": "no_signals", "message": "No signals detected."})

        triples_added = 0
        for sig in signals:
            local_g = _mapper.map_signal(sig)
            if local_g:
                _add_rdflib_graph_to_store(local_g)
                triples_added += len(local_g)

        _stream_messages_received += 1
        return json.dumps({
            "status": "ok",
            "signals": len(signals),
            "triples_added": triples_added,
            "total_stream_messages": _stream_messages_received,
            "total_graph_triples": _graph_triple_count(),
            "signal_types": [s.signal_type.value for s in signals],
        }, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# Entrypoint
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    backend = "Oxigraph (persistent)" if _USE_OXIGRAPH else "rdflib (in-memory fallback)"
    print(f"Ontology MCP Server v2.0 | storage: {backend}", file=sys.stderr)
    if _USE_OXIGRAPH:
        existing = _graph_triple_count()
        print(f"  Store path: {STORE_PATH}", file=sys.stderr)
        print(f"  Existing triples: {existing}", file=sys.stderr)

        # Auto-load output/ directory on startup if store is empty
        if existing == 0:
            output_dir = PROJECT_ROOT / "output"
            if output_dir.exists() and list(output_dir.glob("*.ttl")):
                print(f"  Auto-loading {output_dir} ...", file=sys.stderr)
                for ttl in output_dir.glob("*.ttl"):
                    try:
                        _load_ttl_file_to_store(str(ttl))
                        print(f"    loaded {ttl.name}", file=sys.stderr)
                    except Exception as e:
                        print(f"    SKIP {ttl.name}: {e}", file=sys.stderr)
                print(f"  Auto-load complete: {_graph_triple_count()} triples", file=sys.stderr)

    mcp.run(transport="stdio")
