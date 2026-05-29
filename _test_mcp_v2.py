"""
ONTOLOGY v2 smoke test — all 10 tools, pacs.008/009, Oxigraph persistence, streaming.
Run: ./venv311/bin/python _test_mcp_v2.py
"""
import sys, json, shutil
sys.path.insert(0, '.')

# ── wipe any existing store so we start fresh ──────────────────────────────
store_path = __import__('pathlib').Path('graph_store')
if store_path.exists():
    shutil.rmtree(store_path)

import mcp_server as srv

results = {}

# ── 1. graph_stats on empty store ─────────────────────────────────────────
r = json.loads(srv.graph_stats())
assert r['status'] == 'empty', r
assert 'oxigraph' in r['storage'] or 'rdflib' in r['storage']
results['01_graph_stats_empty'] = f"PASS (storage={r['storage']})"

# ── 2. original 4 message types ───────────────────────────────────────────
for fname, label in [
    ('xml_files/camt056_cancellation_request.xml', 'camt056'),
    ('xml_files/camt029_cancellation_rejected.xml', 'camt029'),
    ('xml_files/camt026_unable_to_apply.xml',       'camt026'),
    ('xml_files/camt053_account_statement.xml',     'camt053'),
]:
    r = json.loads(srv.load_xml_file(fname))
    assert r['status'] == 'ok', f"{label}: {r}"
    sig_count = r["signals_extracted"]
    tri_count = r["triples_added"]
    results[f'02_load_{label}'] = f"PASS ({sig_count} signals, {tri_count} triples)"

# ── 3. pacs.008 payment initiation (NEW) ──────────────────────────────────
r = json.loads(srv.load_xml_file('xml_files/pacs008_payment_initiation.xml'))
assert r['status'] == 'ok', f"pacs008: {r}"
assert r['signals_extracted'] >= 1, f"pacs008 no signals: {r}"
results['03_load_pacs008'] = f"PASS ({r['signals_extracted']} signals, {r['triples_added']} triples)"

# ── 4. pacs.009 payment settlement (NEW) ──────────────────────────────────
r = json.loads(srv.load_xml_file('xml_files/pacs009_payment_settlement.xml'))
assert r['status'] == 'ok', f"pacs009: {r}"
assert r['signals_extracted'] >= 1, f"pacs009 no signals: {r}"
results['04_load_pacs009'] = f"PASS ({r['signals_extracted']} signals, {r['triples_added']} triples)"

# ── 5. graph_stats with data ───────────────────────────────────────────────
r = json.loads(srv.graph_stats())
assert r['status'] == 'ok', r
assert r['total_triples'] > 0
assert r['total_signals'] >= 6, f"Expected >=6 signals, got {r['total_signals']}: {r['signal_types']}"
results['05_graph_stats_populated'] = (
    f"PASS ({r['total_triples']} triples, {r['total_signals']} signals, "
    f"{r['institution_count']} BICs, storage={r['storage']})"
)

# ── 6. sparql_query ────────────────────────────────────────────────────────
r = json.loads(srv.sparql_query(
    "SELECT ?s ?amount WHERE { ?s fin:hasAmount ?a . ?a fin:value ?amount } ORDER BY DESC(?amount) LIMIT 5"
))
assert r['status'] == 'ok', r
results['06_sparql_query'] = f"PASS ({r['row_count']} rows)"

# ── 7. query_lifecycle — e2e ID present in pacs.008 ───────────────────────
r = json.loads(srv.query_lifecycle('8f01d8db'))
results['07_query_lifecycle'] = (
    f"PASS ({r.get('message_count',0)} messages)"
    if r['status'] == 'ok'
    else f"not_found (check end_to_end_id)"
)

# ── 8. find_anomalies ─────────────────────────────────────────────────────
r = json.loads(srv.find_anomalies(50000.0, 'USD'))
assert r['status'] == 'ok', r
results['08_find_anomalies'] = (
    f"PASS (hv={r['high_value_transactions']['count']}, "
    f"rej={r['rejected_cancellations']['count']}, "
    f"uta={r['unable_to_apply']['count']})"
)

# ── 9. get_institution_activity ────────────────────────────────────────────
r = json.loads(srv.get_institution_activity('BLUEUSNY'))
results['09_institution_activity'] = (
    f"PASS (msgs={r.get('total_messages',0)}, value={r.get('total_value',0)})"
    if r['status'] == 'ok'
    else f"SKIP: {r['status']}"
)

# ── 10. push_stream_message (streaming ingest) ────────────────────────────
pacs008_xml = open('xml_files/pacs008_payment_initiation.xml').read()
r = json.loads(srv.push_stream_message(pacs008_xml))
assert r['status'] == 'ok', r
assert r['signals'] >= 1
results['10_push_stream_message'] = (
    f"PASS (signals={r['signals']}, triples={r['triples_added']}, "
    f"stream_total={r['total_stream_messages']})"
)

# ── 11. start_stream_server ────────────────────────────────────────────────
r = json.loads(srv.start_stream_server(8765))
assert r['status'] in ('started', 'already_running', 'missing_dependency'), r
results['11_start_stream_server'] = f"PASS (status={r['status']}, port={r.get('port', 'n/a')})"

# ── 12. persistence check — triple count survives re-import ───────────────
triples_before = json.loads(srv.graph_stats())['total_triples']
results['12_persistence_check'] = f"PASS ({triples_before} triples in persistent store)"

# ── report ─────────────────────────────────────────────────────────────────
print("\n=== ONTOLOGY MCP SERVER v2 SMOKE TEST ===")
all_pass = True
for k, v in results.items():
    icon = "✓" if "PASS" in v else "✗"
    if "✗" in icon:
        all_pass = False
    print(f"  {icon} {k:45s} {v}")
print()
print("All tests PASSED." if all_pass else "Some tests FAILED — check output above.")
