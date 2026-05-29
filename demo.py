#!/usr/bin/env python3
"""
Ontology MCP — Quick Demo

Loads sample ISO 20022 messages, extracts financial signals, builds an RDF
knowledge graph, and runs a SPARQL query — all in 30 seconds.

Usage:
    python demo.py
"""

import sys, json
from pathlib import Path


def main():
    here = Path(__file__).parent
    sys.path.insert(0, str(here))

    try:
        from src.signals.financial_signal_extraction import (
            FinancialSignalExtractionPipeline,
        )
        from src.ontology.financial_ontology_mapper import (
            FinancialSignalToRDFMapper,
        )
    except ImportError:
        print("❌ Could not import Ontology pipeline modules.")
        print("   Run from the project root or install: pip install ontology-mcp")
        return 1

    xml_dir = here / "xml_files"
    if not xml_dir.exists():
        print(f"❌ Sample XML directory not found at {xml_dir}")
        print("   Make sure you're running from the project root.")
        return 1

    print("╔══════════════════════════════════════════════════╗")
    print("║          Ontology MCP — Quick Demo              ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    # ── Step 1: Extract signals from sample XMLs ─────────────────────────
    print("1️⃣  Loading sample ISO 20022 messages...")
    xml_files = sorted(xml_dir.glob("*.xml"))
    print(f"     Found {len(xml_files)} message files:")
    for f in xml_files:
        print(f"       {f.name}")

    print()
    print("     Extracting financial signals...")
    pipeline = FinancialSignalExtractionPipeline()
    all_signals = []
    for f in xml_files:
        signals = pipeline.extract(f.read_text())
        all_signals.extend(signals)
        for sig in signals:
            kind = sig.__class__.__name__.replace("Signal", "")
            tid = getattr(sig, "transaction_id", "") or getattr(sig, "case_id", "") or ""
            amt = getattr(sig, "amount", "") or ""
            print(f"       {kind:25s} {str(tid):35s} {str(amt)}")
    print()

    # ── Step 2: Build knowledge graph ────────────────────────────────────
    print("2️⃣  Building RDF knowledge graph...")
    ontology_path = here / "src" / "ontology" / "schema" / "financial_ontology.ttl"
    mapper = FinancialSignalToRDFMapper(
        ontology_file=str(ontology_path) if ontology_path.exists() else None
    )
    graph = mapper.map_signals(all_signals)
    print(f"     → {len(graph)} triples across {len(all_signals)} signals")
    print()

    # ── Step 3: Show graph content ───────────────────────────────────────
    print("3️⃣  Knowledge graph breakdown:")
    from rdflib import RDF
    FIN = __import__("rdflib").Namespace("http://example.org/financial/ontology#")
    ISO = __import__("rdflib").Namespace("http://example.org/iso20022/ontology#")
    types = {}
    for s in graph.subjects(RDF.type):
        for obj in graph.objects(s, RDF.type):
            label = str(obj).split("/")[-1].split("#")[-1]
            types[label] = types.get(label, 0) + 1
    for t, count in sorted(types.items()):
        print(f"     {t:30s} {count} instance(s)")
    print()

    # ── Step 4: SPARQL query ─────────────────────────────────────────────
    print("4️⃣  Running SPARQL query — show all payment initiations with BICs...")
    q = """
    PREFIX fin: <http://example.org/financial/ontology#>
    SELECT ?txn ?msgId ?fromBic ?toBic ?amount ?currency WHERE {
        ?txn a fin:PaymentInitiation ;
             fin:messageId ?msgId ;
             fin:fromInstitution ?from ;
             fin:toInstitution ?to .
        OPTIONAL { ?txn fin:hasAmount ?amtNode .
                   ?amtNode fin:amountValue ?amount ;
                            fin:amountCurrency ?currency . }
        ?from fin:bic ?fromBic .
        ?to fin:bic ?toBic .
    }
    """
    results = list(graph.query(q))
    print(f"     → {len(results)} result(s)")
    for row in results:
        print(f"       {str(row.msgId):40s} {str(row.fromBic):15s} → {str(row.toBic):15s} {str(row.amount or '?'):>12s} {str(row.currency or ''):4s}")
    print()

    # ── Step 5: Lifecycle query ─────────────────────────────────────────
    print("5️⃣  Running lifecycle query — find complete message chains...")
    q2 = """
    PREFIX fin: <http://example.org/financial/ontology#>
    SELECT ?sig ?type ?msgId WHERE {
        ?sig a ?type .
        ?sig fin:messageId ?msgId .
        FILTER(?type != fin:FinancialSignal && ?type != owl:NamedIndividual)
    }
    ORDER BY ?msgId
    """
    from rdflib import OWL
    results2 = list(graph.query(q2, initNs={"owl": OWL}))
    chains = {}
    for row in results2:
        chain_key = str(row.msgId)[:20]
        if chain_key not in chains:
            chains[chain_key] = []
        chains[chain_key].append((str(row.type).split("#")[-1], str(row.msgId)))
    print(f"     → {len(chains)} message chain(s)")
    for key, msgs in sorted(chains.items()):
        for t, mid in msgs:
            print(f"       {t:30s} {mid[:45]}")
    print()

    print("✅ Demo complete.")
    print()
    print("   Next steps:")
    print("     python mcp_server.py          # Start the MCP server")
    print("     python _test_mcp_v2.py         # Full test suite (15 tests)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
