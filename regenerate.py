#!/usr/bin/env python3
"""
Ontology Direct Batch Regenerator
================================
Regenerates all TTL files in output/ directly from xml_files/ without
needing the HTTP API running. Also rebuilds the Oxigraph store from scratch.

Usage:
    ./venv311/bin/python regenerate.py             # regenerate all xml_files/
    ./venv311/bin/python regenerate.py --xml-only  # skip store rebuild
    ./venv311/bin/python regenerate.py --store-only # just rebuild store from output/

All output goes to output/ and the Oxigraph store is rebuilt clean.
"""

import sys
import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.signals.financial_signal_extraction import FinancialSignalExtractionPipeline
from src.ontology.financial_ontology_mapper import FinancialSignalToRDFMapper

ONTOLOGY_PATH = PROJECT_ROOT / "src" / "ontology" / "schema" / "financial_ontology.ttl"
XML_DIR       = PROJECT_ROOT / "xml_files"
OUTPUT_DIR    = PROJECT_ROOT / "output"
STORE_PATH    = PROJECT_ROOT / "graph_store"


def regenerate_ttls(xml_dir: Path, output_dir: Path) -> list[dict]:
    """Convert all XML files to fresh TTL files. Returns results list."""
    output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = FinancialSignalExtractionPipeline()
    mapper   = FinancialSignalToRDFMapper(
        ontology_file=str(ONTOLOGY_PATH) if ONTOLOGY_PATH.exists() else None
    )

    xml_files = sorted(xml_dir.glob("*.xml"))
    if not xml_files:
        print(f"  No XML files found in {xml_dir}")
        return []

    results = []
    for xml_path in xml_files:
        try:
            xml_content = xml_path.read_text(encoding="utf-8")
            signals     = pipeline.extract(xml_content)

            if not signals:
                results.append({"file": xml_path.name, "status": "no_signals"})
                print(f"  SKIP  {xml_path.name:50s}  (no ISO 20022 signals detected)")
                continue

            # Map all signals into one graph
            from rdflib import Graph
            combined = Graph()
            for sig in signals:
                g = mapper.map_signal(sig)
                if g:
                    for triple in g:
                        combined.add(triple)

            # Derive output filename  e.g. pacs008_payment_initiation.xml → pacs008_payment_initiation_rdf.ttl
            stem     = xml_path.stem
            out_name = f"{stem}_rdf.ttl"
            out_path = output_dir / out_name
            combined.serialize(destination=str(out_path), format="turtle")

            results.append({
                "file":    xml_path.name,
                "output":  out_name,
                "status":  "ok",
                "signals": len(signals),
                "triples": len(combined),
                "types":   [s.signal_type.value for s in signals],
            })
            print(f"  OK    {xml_path.name:50s}  "
                  f"{len(signals)} signal(s)  {len(combined):3d} triples  → {out_name}")

        except Exception as e:
            results.append({"file": xml_path.name, "status": "error", "error": str(e)})
            print(f"  ERR   {xml_path.name:50s}  {e}")

    return results


def rebuild_store(output_dir: Path, store_path: Path) -> int:
    """Wipe and rebuild the Oxigraph store from all TTLs in output_dir."""
    try:
        import pyoxigraph as ox
    except ImportError:
        print("  pyoxigraph not installed — store rebuild skipped")
        return 0

    # Wipe existing store
    if store_path.exists():
        shutil.rmtree(store_path)
        print(f"  Wiped existing store at {store_path}")

    store    = ox.Store(str(store_path))
    ttl_files = sorted(output_dir.glob("*.ttl"))
    loaded   = 0

    for ttl in ttl_files:
        try:
            store.load(ttl.read_bytes(), format=ox.RdfFormat.TURTLE)
            count = sum(1 for _ in store.quads_for_pattern(None, None, None, None))
            print(f"  LOAD  {ttl.name:50s}  store now {count} triples")
            loaded += 1
        except Exception as e:
            print(f"  ERR   {ttl.name}: {e}")

    total = sum(1 for _ in store.quads_for_pattern(None, None, None, None))
    return total


def main():
    parser = argparse.ArgumentParser(description="Ontology batch regenerator")
    parser.add_argument("--xml-only",   action="store_true", help="Regenerate TTLs only, skip store rebuild")
    parser.add_argument("--store-only", action="store_true", help="Rebuild store from existing TTLs only")
    parser.add_argument("--xml-dir",    default=str(XML_DIR),    help=f"XML input dir (default: {XML_DIR})")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR), help=f"TTL output dir (default: {OUTPUT_DIR})")
    args = parser.parse_args()

    xml_dir    = Path(args.xml_dir)
    output_dir = Path(args.output_dir)

    print(f"\nOntology Direct Batch Regenerator")
    print(f"  XML input : {xml_dir}")
    print(f"  TTL output: {output_dir}")
    print(f"  Store     : {STORE_PATH}")
    print()

    results = []

    if not args.store_only:
        print("── Step 1: Regenerating TTL files ──────────────────────────")
        results = regenerate_ttls(xml_dir, output_dir)
        ok      = [r for r in results if r["status"] == "ok"]
        skipped = [r for r in results if r["status"] == "no_signals"]
        errors  = [r for r in results if r["status"] == "error"]
        print(f"\n  Done: {len(ok)} converted, {len(skipped)} skipped, {len(errors)} errors")
        print()

    if not args.xml_only:
        print("── Step 2: Rebuilding Oxigraph store ───────────────────────")
        total_triples = rebuild_store(output_dir, STORE_PATH)
        print(f"\n  Store rebuilt: {total_triples} total triples")
        print()

    print("── Summary ─────────────────────────────────────────────────")
    for r in results:
        if r["status"] == "ok":
            print(f"  ✓ {r['file']:45s} → {r['output']}  ({r['triples']} triples)")
        elif r["status"] == "no_signals":
            print(f"  - {r['file']:45s}   (no signals)")
        else:
            print(f"  ✗ {r['file']:45s}   ERROR: {r.get('error','?')}")

    if not args.xml_only:
        # Verify by querying the fresh store directly
        print()
        print("── Verification ─────────────────────────────────────────────")
        try:
            import pyoxigraph as ox, json
            store = ox.Store(str(STORE_PATH))
            total = sum(1 for _ in store.quads_for_pattern(None, None, None, None))
            print(f"  Triples  : {total}")

            # Count signal types
            type_q = """
SELECT ?type (COUNT(?s) AS ?count)
WHERE {
    VALUES ?type {
        <http://example.org/financial/ontology#PaymentCancellation>
        <http://example.org/financial/ontology#InvestigationResolution>
        <http://example.org/financial/ontology#UnableToApply>
        <http://example.org/financial/ontology#AccountStatement>
        <http://example.org/financial/ontology#PaymentInitiation>
        <http://example.org/financial/ontology#PaymentSettlement>
        <http://example.org/financial/ontology#AccountTransaction>
    }
    ?s a ?type .
} GROUP BY ?type
"""
            result  = store.query(type_q)
            vars_   = [str(v).lstrip('?') for v in result.variables]
            types   = {}
            for row in result:
                t = str(row[0]).split('#')[-1].rstrip('>')
                c = str(row[1])
                import re
                m = re.search(r'"(\d+)"', c)
                types[t] = int(m.group(1)) if m else int(c)
            print(f"  Signals  : {sum(types.values())} — {types}")

            # Count BICs
            bic_q  = "SELECT DISTINCT ?bic WHERE { ?i <http://example.org/financial/ontology#bic> ?bic } ORDER BY ?bic"
            bres   = store.query(bic_q)
            bics   = [str(row[0]).strip('"') for row in bres]
            print(f"  BICs     : {bics}")

            # Lifecycle query by e2e ID
            e2e_q = """
SELECT ?signal ?type ?timestamp ?fromBIC ?toBIC WHERE {
    VALUES ?type {
        <http://example.org/financial/ontology#PaymentCancellation>
        <http://example.org/financial/ontology#InvestigationResolution>
        <http://example.org/financial/ontology#UnableToApply>
        <http://example.org/financial/ontology#PaymentInitiation>
        <http://example.org/financial/ontology#PaymentSettlement>
    }
    ?signal a ?type .
    ?signal <http://example.org/financial/ontology#endToEndId> ?e2e .
    FILTER(CONTAINS(STR(?e2e), "8f01d8db"))
    OPTIONAL { ?signal <http://example.org/financial/ontology#timestamp> ?timestamp }
    OPTIONAL { ?signal <http://example.org/financial/ontology#fromInstitution> ?fi .
               ?fi    <http://example.org/financial/ontology#bic> ?fromBIC }
    OPTIONAL { ?signal <http://example.org/financial/ontology#toInstitution> ?ti .
               ?ti    <http://example.org/financial/ontology#bic> ?toBIC }
} ORDER BY ?timestamp
"""
            lc_res  = store.query(e2e_q)
            lc_vars = [str(v).lstrip('?') for v in lc_res.variables]
            msgs    = []
            for row in lc_res:
                d = {}
                for i, name in enumerate(lc_vars):
                    if row[i] is not None:
                        d[name] = str(row[i])
                msgs.append(d)

            print(f"\n  Lifecycle query (e2e=8f01d8db...): {len(msgs)} messages")
            for msg in msgs:
                t   = msg.get('type','?').split('#')[-1].rstrip('>')
                ts  = msg.get('timestamp','?')[:19].strip('"')
                frm = msg.get('fromBIC','?').strip('"')
                to_ = msg.get('toBIC','?').strip('"')
                print(f"    {ts}  {t:30s}  {frm} → {to_}")

        except Exception as e:
            print(f"  Verification error: {e}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
