"""
SPARQL Query Examples for Financial RDF Data

This script demonstrates how to query your financial RDF data using SPARQL.
Uses your actual payment cancellation data!
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rdflib import Graph


def load_rdf_file(filepath):
    """Load RDF file into a graph"""
    print(f"📥 Loading RDF file: {filepath}")
    g = Graph()
    g.parse(filepath, format="turtle")
    
    stats = {
        "triples": len(g),
        "subjects": len(set(g.subjects())),
        "predicates": len(set(g.predicates())),
        "objects": len(set(g.objects()))
    }
    
    print(f"✅ Loaded {stats['triples']} triples")
    print(f"   Subjects: {stats['subjects']}")
    print(f"   Predicates: {stats['predicates']}")
    print(f"   Objects: {stats['objects']}")
    
    return g


def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def query_1_payment_details(g):
    """Query 1: Get all payment cancellation details"""
    
    print_section("Query 1: Get Payment Cancellation Details")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    PREFIX inst: <http://example.org/financial/instance#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    
    SELECT ?signal ?caseId ?amount ?currency ?timestamp
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:caseId ?caseId .
        ?signal fin:hasAmount ?amountObj .
        ?amountObj fin:value ?amount .
        ?amountObj fin:currency ?currency .
        ?signal fin:timestamp ?timestamp .
    }
    """
    
    print("📊 Finding all payment cancellations...\n")
    
    results = g.query(query)
    
    for row in results:
        print(f"✅ Payment Cancellation Found:")
        print(f"   Case ID: {row.caseId}")
        print(f"   Amount: {row.currency} {float(row.amount):,.2f}")
        print(f"   Timestamp: {row.timestamp}")
        print(f"   Signal URI: {row.signal}")


def query_2_institutions(g):
    """Query 2: Get financial institutions involved"""
    
    print_section("Query 2: Get Financial Institutions")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT ?signal ?fromBIC ?toBIC
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:fromInstitution ?from .
        ?from fin:bic ?fromBIC .
        ?signal fin:toInstitution ?to .
        ?to fin:bic ?toBIC .
    }
    """
    
    print("🏦 Finding institutions involved...\n")
    
    results = g.query(query)
    
    for row in results:
        print(f"✅ Transaction Route:")
        print(f"   From: {row.fromBIC} (Initiating Bank)")
        print(f"   To: {row.toBIC} (Receiving Bank)")


def query_3_cancellation_reason(g):
    """Query 3: Get cancellation reason"""
    
    print_section("Query 3: Get Cancellation Reason")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT ?signal ?reasonCode ?reasonLabel ?reasonDescription
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:hasReason ?reason .
        ?reason fin:reasonCode ?reasonCode .
        
        # Get the definition from ontology
        OPTIONAL {
            ?reasonDef fin:reasonCode ?reasonCode .
            ?reasonDef rdfs:label ?reasonLabel .
            ?reasonDef rdfs:comment ?reasonDescription .
        }
    }
    """
    
    print("❓ Finding cancellation reason...\n")
    
    results = g.query(query)
    
    for row in results:
        print(f"✅ Cancellation Reason:")
        print(f"   Code: {row.reasonCode}")
        if row.reasonLabel:
            print(f"   Label: {row.reasonLabel}")
        if row.reasonDescription:
            print(f"   Description: {row.reasonDescription}")


def query_4_original_transaction(g):
    """Query 4: Get original transaction details"""
    
    print_section("Query 4: Get Original Transaction")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT ?signal ?txId ?endToEndId ?msgId
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:originalTransaction ?tx .
        ?tx fin:transactionId ?txId .
        ?tx fin:endToEndId ?endToEndId .
        ?tx fin:messageId ?msgId .
    }
    """
    
    print("🔗 Finding original transaction being cancelled...\n")
    
    results = g.query(query)
    
    for row in results:
        print(f"✅ Original Transaction:")
        print(f"   Transaction ID: {row.txId}")
        print(f"   End-to-End ID: {row.endToEndId}")
        print(f"   Message ID: {row.msgId}")


def query_5_high_value(g):
    """Query 5: Find high-value cancellations (>$100k)"""
    
    print_section("Query 5: High-Value Cancellations (>$100,000)")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT ?signal ?amount ?currency ?caseId
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:caseId ?caseId .
        ?signal fin:hasAmount ?amountObj .
        ?amountObj fin:value ?amount .
        ?amountObj fin:currency ?currency .
        FILTER(?amount > 100000)
    }
    ORDER BY DESC(?amount)
    """
    
    print("💰 Finding cancellations over $100,000...\n")
    
    results = g.query(query)
    
    count = 0
    for row in results:
        count += 1
        print(f"✅ High-Value Cancellation #{count}:")
        print(f"   Amount: {row.currency} {float(row.amount):,.2f}")
        print(f"   Case ID: {row.caseId}")
    
    if count == 0:
        print("   No high-value cancellations found.")
    else:
        print(f"\n   Total: {count} high-value cancellation(s)")


def query_6_all_amounts(g):
    """Query 6: List all amounts with their currencies"""
    
    print_section("Query 6: All Amounts")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT ?amount ?currency
    WHERE {
        ?amountObj a fin:Amount .
        ?amountObj fin:value ?amount .
        ?amountObj fin:currency ?currency .
    }
    """
    
    print("💵 Finding all amounts...\n")
    
    results = g.query(query)
    
    for row in results:
        print(f"   {row.currency} {float(row.amount):,.2f}")


def query_7_customer_requested(g):
    """Query 7: Customer-requested cancellations (reason = CUST)"""
    
    print_section("Query 7: Customer-Requested Cancellations")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT ?signal ?amount ?currency ?caseId
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:caseId ?caseId .
        ?signal fin:hasReason ?reason .
        ?reason fin:reasonCode "CUST" .
        ?signal fin:hasAmount ?amountObj .
        ?amountObj fin:value ?amount .
        ?amountObj fin:currency ?currency .
    }
    """
    
    print("👤 Finding customer-requested cancellations...\n")
    
    results = g.query(query)
    
    count = 0
    for row in results:
        count += 1
        print(f"✅ Customer Request #{count}:")
        print(f"   Case ID: {row.caseId}")
        print(f"   Amount: {row.currency} {float(row.amount):,.2f}")
    
    if count == 0:
        print("   No customer-requested cancellations found.")
    else:
        print(f"\n   Total: {count} customer-requested cancellation(s)")


def query_8_settlement_date(g):
    """Query 8: Cancellations by settlement date"""
    
    print_section("Query 8: Settlement Dates")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT ?signal ?settlementDate ?amount ?currency
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:settlementDate ?settlementDate .
        ?signal fin:hasAmount ?amountObj .
        ?amountObj fin:value ?amount .
        ?amountObj fin:currency ?currency .
    }
    ORDER BY ?settlementDate
    """
    
    print("📅 Finding settlement dates...\n")
    
    results = g.query(query)
    
    for row in results:
        print(f"✅ Settlement:")
        print(f"   Date: {row.settlementDate}")
        print(f"   Amount: {row.currency} {float(row.amount):,.2f}")


def query_9_all_institutions(g):
    """Query 9: List all financial institutions"""
    
    print_section("Query 9: All Financial Institutions")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT DISTINCT ?institution ?bic
    WHERE {
        ?institution a fin:FinancialInstitution .
        ?institution fin:bic ?bic .
    }
    ORDER BY ?bic
    """
    
    print("🏦 Finding all institutions...\n")
    
    results = g.query(query)
    
    count = 0
    for row in results:
        count += 1
        print(f"   {count}. {row.bic}")
    
    print(f"\n   Total: {count} institution(s)")


def query_10_summary(g):
    """Query 10: Summary statistics"""
    
    print_section("Query 10: Summary Statistics")
    
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT 
        (COUNT(?signal) as ?totalCancellations)
        (SUM(?amount) as ?totalAmount)
        (AVG(?amount) as ?avgAmount)
        (MAX(?amount) as ?maxAmount)
        (MIN(?amount) as ?minAmount)
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:hasAmount ?amountObj .
        ?amountObj fin:value ?amount .
    }
    """
    
    print("📊 Computing summary statistics...\n")
    
    results = g.query(query)
    
    for row in results:
        print(f"✅ Summary:")
        print(f"   Total Cancellations: {row.totalCancellations}")
        print(f"   Total Amount: ${float(row.totalAmount):,.2f}")
        print(f"   Average Amount: ${float(row.avgAmount):,.2f}")
        print(f"   Max Amount: ${float(row.maxAmount):,.2f}")
        print(f"   Min Amount: ${float(row.minAmount):,.2f}")


def run_custom_query(g, query_str):
    """Run a custom SPARQL query"""
    
    print_section("Custom Query")
    
    print("Query:")
    print(query_str)
    print("\nResults:")
    
    results = g.query(query_str)
    
    for i, row in enumerate(results, 1):
        print(f"\n{i}. {dict(row)}")


def main():
    """Run all query examples"""
    
    # Check if RDF file is provided
    if len(sys.argv) > 1:
        rdf_file = sys.argv[1]
    else:
        # Look for RDF files in output directory
        output_dir = Path("output")
        rdf_files = list(output_dir.glob("*.ttl"))
        
        if not rdf_files:
            print("❌ No RDF files found in output/ directory")
            print("   Run: python xml_to_rdf.py your_file.xml first")
            return
        
        # Use most recent file
        rdf_file = max(rdf_files, key=lambda p: p.stat().st_mtime)
        print(f"📁 Using most recent file: {rdf_file}")
    
    # Load RDF
    g = load_rdf_file(rdf_file)
    
    # Run all queries
    query_1_payment_details(g)
    query_2_institutions(g)
    query_3_cancellation_reason(g)
    query_4_original_transaction(g)
    query_5_high_value(g)
    query_6_all_amounts(g)
    query_7_customer_requested(g)
    query_8_settlement_date(g)
    query_9_all_institutions(g)
    query_10_summary(g)
    
    # Final message
    print_section("✅ All Queries Complete!")
    
    print("""
💡 Want to try your own queries?

Use this template:

    from rdflib import Graph
    
    g = Graph()
    g.parse("output/your_file.ttl", format="turtle")
    
    query = '''
    PREFIX fin: <http://example.org/financial/ontology#>
    
    SELECT ?variable
    WHERE {
        ?variable a fin:PaymentCancellation .
    }
    '''
    
    results = g.query(query)
    for row in results:
        print(row)

📚 SPARQL Tutorial: https://www.w3.org/TR/sparql11-query/
    """)


if __name__ == "__main__":
    main()