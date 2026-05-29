"""
Financial Ontology Mapping - Live Demo

This demonstrates the complete flow:
  ISO 20022 XML → Financial Signal → RDF Triples → SPARQL Queries

Run this to see your data transformed into semantic RDF!
"""

import sys
import os
from pathlib import Path

# Add project root to path (works from anywhere)
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

from src.signals.financial_signal_extraction import FinancialSignalExtractionPipeline
from src.ontology.financial_ontology_mapper import FinancialSignalToRDFMapper
from datetime import datetime


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def demo_complete_flow(xml_file_path=None):
    """
    Demonstrate the complete ontology mapping flow.
    
    Args:
        xml_file_path: Path to ISO 20022 XML file (optional)
    """
    
    print_section("FINANCIAL ONTOLOGY MAPPING - LIVE DEMO")
    print("\nThis demo shows: ISO 20022 XML → Signals → RDF Triples → SPARQL\n")
    
    # Use provided file or sample data
    if xml_file_path:
        print(f"📥 Using your file: {xml_file_path}")
        with open(xml_file_path, 'r') as f:
            xml_data = f.read()
    else:
        print("📥 Using sample payment cancellation")
        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<Message xmlns="urn:issettled"
    xmlns:ispcr="urn:iso:std:iso:20022:tech:xsd:camt.056.001.10">
    <FIToFIPmtCxlReq>
        <ispcr:Assgnmt>
            <ispcr:Id>DEMO_CANCEL_20260121</ispcr:Id>
            <ispcr:Assgnr>
                <ispcr:Agt>
                    <ispcr:FinInstnId>
                        <ispcr:BICFI>BLUEUSNY001</ispcr:BICFI>
                        <ispcr:Othr><ispcr:Id>bluebank</ispcr:Id></ispcr:Othr>
                    </ispcr:FinInstnId>
                </ispcr:Agt>
            </ispcr:Assgnr>
            <ispcr:Assgne>
                <ispcr:Agt>
                    <ispcr:FinInstnId>
                        <ispcr:BICFI>GRENCHZZ002</ispcr:BICFI>
                        <ispcr:Othr><ispcr:Id>greenbank</ispcr:Id></ispcr:Othr>
                    </ispcr:FinInstnId>
                </ispcr:Agt>
            </ispcr:Assgne>
            <ispcr:CreDtTm>2026-01-21T20:00:00</ispcr:CreDtTm>
        </ispcr:Assgnmt>
        <ispcr:Case>
            <ispcr:Id>CASE_DEMO_001</ispcr:Id>
        </ispcr:Case>
        <ispcr:Undrlyg>
            <ispcr:OrgnlGrpInfAndCxl>
                <ispcr:OrgnlMsgId>MSG_ORIGINAL_12345</ispcr:OrgnlMsgId>
            </ispcr:OrgnlGrpInfAndCxl>
            <ispcr:TxInf>
                <ispcr:OrgnlTxId>TXN_ABC123XYZ</ispcr:OrgnlTxId>
                <ispcr:OrgnlEndToEndId>E2E_999888777</ispcr:OrgnlEndToEndId>
                <ispcr:OrgnlIntrBkSttlmAmt Ccy="USD">250000</ispcr:OrgnlIntrBkSttlmAmt>
                <ispcr:OrgnlIntrBkSttlmDt>2026-01-21</ispcr:OrgnlIntrBkSttlmDt>
                <ispcr:CxlRsnInf>
                    <ispcr:Rsn><ispcr:Cd>CUST</ispcr:Cd></ispcr:Rsn>
                </ispcr:CxlRsnInf>
            </ispcr:TxInf>
        </ispcr:Undrlyg>
    </FIToFIPmtCxlReq>
</Message>"""
    
    # STEP 1: Extract Signal
    print_section("STEP 1: Extract Financial Signal from XML")
    
    pipeline = FinancialSignalExtractionPipeline()
    signals = pipeline.extract(xml_data)
    
    if not signals:
        print("❌ No signals extracted!")
        return
    
    signal = signals[0]
    
    print(f"\n✅ Extracted Signal:")
    print(f"   Type: {signal.signal_type.value}")
    print(f"   Case ID: {signal.case_id}")
    print(f"   Amount: {signal.amount}")
    print(f"   From: {signal.assignor.bic} ({signal.assignor.institution_id})")
    print(f"   To: {signal.assignee.bic} ({signal.assignee.institution_id})")
    print(f"   Reason: {signal.cancellation_reason_code}")
    print(f"   Timestamp: {signal.timestamp}")
    
    # STEP 2: Map to RDF
    print_section("STEP 2: Map Signal to RDF Triples (Ontology)")
    
    # Use project root to find ontology
    ontology_path = project_root / "src" / "ontology" / "schema" / "financial_ontology.ttl"
    mapper = FinancialSignalToRDFMapper(ontology_file=str(ontology_path))
    
    graph = mapper.map_signal(signal)
    stats = mapper.get_stats()
    
    print(f"\n✅ RDF Graph Created:")
    print(f"   Total Triples: {stats['total_triples']}")
    print(f"   Subjects: {stats['subjects']}")
    print(f"   Predicates: {stats['predicates']}")
    print(f"   Objects: {stats['objects']}")
    
    # STEP 3: Show RDF Sample
    print_section("STEP 3: RDF Triples (Turtle Format) - Sample")
    
    turtle = mapper.serialize(format="turtle")
    
    # Show relevant part (not the whole ontology)
    print("\n💎 Key Triples (your payment cancellation):\n")
    lines = turtle.split('\n')
    
    # Find and show the payment cancellation instance
    in_payment = False
    shown_lines = 0
    max_lines = 40
    
    for line in lines:
        if 'inst:payment_cancellation' in line:
            in_payment = True
        
        if in_payment:
            print(line)
            shown_lines += 1
            if shown_lines >= max_lines or (line.strip() == '' and shown_lines > 10):
                break
    
    print("\n... (full RDF saved to file)")
    
    # STEP 4: SPARQL Queries
    print_section("STEP 4: Query with SPARQL")
    
    # Query 1: Get payment details
    print("\n🔍 Query 1: Get all payment cancellation details\n")
    
    query1 = """
    PREFIX fin: <http://example.org/financial/ontology#>
    PREFIX inst: <http://example.org/financial/instance#>
    
    SELECT ?signal ?caseId ?amount ?currency ?reasonCode
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:caseId ?caseId .
        ?signal fin:hasAmount ?amountObj .
        ?amountObj fin:value ?amount .
        ?amountObj fin:currency ?currency .
        ?signal fin:hasReason ?reason .
        ?reason fin:reasonCode ?reasonCode .
    }
    """
    
    results1 = mapper.query(query1)
    
    print("Results:")
    for row in results1:
        print(f"  Case ID: {row.caseId}")
        print(f"  Amount: {row.currency} {row.amount:,.2f}")
        print(f"  Reason: {row.reasonCode}")
    
    # Query 2: Get institutions
    print("\n🔍 Query 2: Get financial institutions involved\n")
    
    query2 = """
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
    
    results2 = mapper.query(query2)
    
    print("Results:")
    for row in results2:
        print(f"  From: {row.fromBIC}")
        print(f"  To: {row.toBIC}")
    
    # Query 3: Get transaction info
    print("\n🔍 Query 3: Get original transaction details\n")
    
    query3 = """
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
    
    results3 = mapper.query(query3)
    
    print("Results:")
    for row in results3:
        print(f"  Transaction ID: {row.txId}")
        print(f"  End-to-End ID: {row.endToEndId}")
        print(f"  Message ID: {row.msgId}")
    
    # STEP 5: Save Files
    print_section("STEP 5: Save RDF Output")
    
    # Save in multiple formats (relative to project root)
    output_dir = project_root / "output"
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Turtle (human-readable)
    turtle_file = output_dir / f"payment_cancellation_{timestamp}.ttl"
    mapper.save(str(turtle_file), format="turtle")
    print(f"\n✅ Saved Turtle: {turtle_file}")
    
    # JSON-LD (for JavaScript apps)
    jsonld_file = output_dir / f"payment_cancellation_{timestamp}.jsonld"
    mapper.save(str(jsonld_file), format="json-ld")
    print(f"✅ Saved JSON-LD: {jsonld_file}")
    
    # RDF/XML (for Java tools)
    xml_file = output_dir / f"payment_cancellation_{timestamp}.rdf"
    mapper.save(str(xml_file), format="xml")
    print(f"✅ Saved RDF/XML: {xml_file}")
    
    # SUMMARY
    print_section("SUMMARY - Complete Semantic Pipeline")
    
    print("""
    ✅ Your ISO 20022 XML has been transformed into semantic RDF!
    
    What happened:
    ┌─────────────────────────────────────────────────────────────┐
    │  1. ISO 20022 XML (banking message)                         │
    │     ↓                                                        │
    │  2. Financial Signal (Python object)                        │
    │     ↓                                                        │
    │  3. RDF Triples (semantic web format)                       │
    │     ↓                                                        │
    │  4. SPARQL Queries (semantic queries)                       │
    │     ↓                                                        │
    │  5. Multiple formats (Turtle, JSON-LD, RDF/XML)            │
    └─────────────────────────────────────────────────────────────┘
    
    Your data is now:
    • Machine-readable with semantic meaning
    • Queryable with SPARQL
    • Linked to financial ontology
    • Ready for knowledge graph storage
    • Compatible with semantic web tools
    
    Next steps:
    • Load RDF into Neo4j or GraphDB
    • Build reasoning rules
    • Connect to other knowledge graphs
    • Visualize relationships
    """)
    
    print_section("FILES GENERATED")
    print(f"""
    Check these files in the '{output_dir}/' directory:
    
    1. {os.path.basename(turtle_file)}
       → Human-readable format
       → Best for viewing/debugging
    
    2. {os.path.basename(jsonld_file)}
       → JSON format for web apps
       → Easy to parse in JavaScript
    
    3. {os.path.basename(xml_file)}
       → XML format for enterprise tools
       → Compatible with Java/Apache Jena
    """)
    
    print("=" * 80 + "\n")


def show_api_examples():
    """Show how to use the API for ontology mapping"""
    
    print_section("BONUS: Using the API for Ontology Mapping")
    
    print("""
    You can also get RDF via the API:
    
    🌐 Start the ontology API:
    
        python -m src.api.financial_ontology_api
    
    📡 Get RDF via HTTP:
    
        # Get as Turtle
        curl -X POST http://localhost:8000/ontology/map \\
          -H "Content-Type: application/json" \\
          -d '{"data": "<Message>...</Message>"}' \\
          > payment.ttl
        
        # Get as JSON-LD
        curl -X POST http://localhost:8000/ontology/map \\
          -H "Content-Type: application/json" \\
          -d '{
            "data": "<Message>...</Message>",
            "data_format": "json-ld"
          }' > payment.jsonld
        
        # Get ontology schema
        curl http://localhost:8000/ontology/schema > schema.ttl
    
    📊 Interactive docs:
    
        http://localhost:8000/docs
    """)


if __name__ == "__main__":
    
    # Check if user provided a file
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
        print(f"\n🎯 Testing with your file: {xml_file}\n")
        demo_complete_flow(xml_file)
    else:
        # Run with sample data
        demo_complete_flow()
    
    # Show API examples
    show_api_examples()
    
    print("\n✨ Demo complete! Your financial data is now semantic RDF! ✨\n")