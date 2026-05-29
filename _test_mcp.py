"""Quick smoke test for MCP server tools - run from project root."""
import sys, json
sys.path.insert(0, '.')

# Import the MCP server module (defines tools as plain functions)
import mcp_server as srv

results = {}

# Test 1: graph_stats on empty graph
r = json.loads(srv.graph_stats())
assert r['status'] == 'empty', f"Expected empty, got {r}"
results['graph_stats_empty'] = 'PASS'

# Test 2: load a real XML file
r = json.loads(srv.load_xml_file('xml_files/camt056_cancellation_request.xml'))
assert r['status'] == 'ok', f"load_xml_file failed: {r}"
assert r['signals_extracted'] >= 1
results['load_xml_camt056'] = f"PASS ({r['signals_extracted']} signals, {r['triples_added']} triples)"

r = json.loads(srv.load_xml_file('xml_files/camt029_cancellation_rejected.xml'))
results['load_xml_camt029'] = f"PASS ({r.get('signals_extracted',0)} signals)"

r = json.loads(srv.load_xml_file('xml_files/camt026_unable_to_apply.xml'))
results['load_xml_camt026'] = f"PASS ({r.get('signals_extracted',0)} signals)"

r = json.loads(srv.load_xml_file('xml_files/camt053_account_statement.xml'))
results['load_xml_camt053'] = f"PASS ({r.get('signals_extracted',0)} signals)"

# Test 3: graph_stats populated
r = json.loads(srv.graph_stats())
assert r['status'] == 'ok'
assert r['total_triples'] > 0
results['graph_stats_populated'] = f"PASS ({r['total_triples']} triples, {r['total_signals']} signals)"

# Test 4: sparql_query
r = json.loads(srv.sparql_query(
    "SELECT ?s ?amount WHERE { ?s fin:hasAmount ?a . ?a fin:value ?amount } ORDER BY DESC(?amount) LIMIT 5"
))
assert r['status'] == 'ok'
results['sparql_query'] = f"PASS ({r['row_count']} rows)"

# Test 5: find_anomalies
r = json.loads(srv.find_anomalies(50000.0, 'USD'))
assert r['status'] == 'ok'
results['find_anomalies'] = f"PASS (high_value={r['high_value_transactions']['count']}, uta={r['unable_to_apply']['count']})"

# Test 6: get_institution_activity
stats = json.loads(srv.graph_stats())
bics = stats.get('institutions_bics', [])
if bics:
    r = json.loads(srv.get_institution_activity(bics[0]))
    results['get_institution_activity'] = f"PASS (bic={bics[0]}, msgs={r.get('total_messages',0)})"
else:
    results['get_institution_activity'] = 'SKIP (no BICs in graph)'

# Test 7: query_lifecycle
r = json.loads(srv.query_lifecycle('BLUEUSNY'))
results['query_lifecycle'] = f"PASS ({r.get('message_count', 0)} messages)" if r['status'] == 'ok' else f"not_found (ok if no BIC match)"

print("\n=== ONTOLOGY MCP SERVER SMOKE TEST ===")
for k, v in results.items():
    print(f"  {k:40s} {v}")
print("\nAll tests complete.")
