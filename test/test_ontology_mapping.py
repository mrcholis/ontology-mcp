"""
Test Financial Ontology Mapping

Demonstrates converting financial signals to RDF triples.
"""

import sys
sys.path.insert(0, '/mnt/user-data/outputs')

from financial_signal_extraction import FinancialSignalExtractionPipeline
from financial_ontology_mapper import FinancialSignalToRDFMapper


def test_with_sample_xml():
    """Test ontology mapping with sample payment cancellation"""
    
    print("\n" + "=" * 80)
    print("FINANCIAL ONTOLOGY MAPPING TEST")
    print("=" * 80)
    
    # Sample ISO 20022 camt.056 XML
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Message xmlns="urn:issettled"
    xmlns:ispcr="urn:iso:std:iso:20022:tech:xsd:camt.056.001.10">
    <FIToFIPmtCxlReq>
        <ispcr:Assgnmt>
            <ispcr:Id>CANCEL_TEST_001</ispcr:Id>
            <ispcr:Assgnr>
                <ispcr:Agt>
                    <ispcr:FinInstnId>
                        <ispcr:BICFI>BLUEUSNY001</ispcr:BICFI>
                        <ispcr:Othr>
                            <ispcr:Id>bluebank</ispcr:Id>
                        </ispcr:Othr>
                    </ispcr:FinInstnId>
                </ispcr:Agt>
            </ispcr:Assgnr>
            <ispcr:Assgne>
                <ispcr:Agt>
                    <ispcr:FinInstnId>
                        <ispcr:BICFI>GRENCHZZ002</ispcr:BICFI>
                        <ispcr:Othr>
                            <ispcr:Id>greenbank</ispcr:Id>
                        </ispcr:Othr>
                    </ispcr:FinInstnId>
                </ispcr:Agt>
            </ispcr:Assgne>
            <ispcr:CreDtTm>2024-01-20T14:30:00</ispcr:CreDtTm>
        </ispcr:Assgnmt>
        <ispcr:Case>
            <ispcr:Id>CASE_TEST_001</ispcr:Id>
        </ispcr:Case>
        <ispcr:Undrlyg>
            <ispcr:OrgnlGrpInfAndCxl>
                <ispcr:OrgnlMsgId>MSG_ORIGINAL_001</ispcr:OrgnlMsgId>
            </ispcr:OrgnlGrpInfAndCxl>
            <ispcr:TxInf>
                <ispcr:OrgnlTxId>TXN_ABC123</ispcr:OrgnlTxId>
                <ispcr:OrgnlEndToEndId>E2E_XYZ789</ispcr:OrgnlEndToEndId>
                <ispcr:OrgnlIntrBkSttlmAmt Ccy="USD">75000</ispcr:OrgnlIntrBkSttlmAmt>
                <ispcr:OrgnlIntrBkSttlmDt>2024-01-20</ispcr:OrgnlIntrBkSttlmDt>
                <ispcr:CxlRsnInf>
                    <ispcr:Rsn>
                        <ispcr:Cd>CUST</ispcr:Cd>
                    </ispcr:Rsn>
                </ispcr:CxlRsnInf>
            </ispcr:TxInf>
        </ispcr:Undrlyg>
    </FIToFIPmtCxlReq>
</Message>"""
    
    print("\n📥 Step 1: Extract Signal from ISO 20022 XML")
    print("-" * 80)
    
    # Extract signal
    pipeline = FinancialSignalExtractionPipeline()
    signals = pipeline.extract(sample_xml)
    
    if not signals:
        print("❌ No signals extracted!")
        return
    
    signal = signals[0]
    print(f"✅ Extracted: {signal.signal_type.value}")
    print(f"   Case ID: {signal.case_id}")
    print(f"   Amount: {signal.amount}")
    print(f"   From: {signal.assignor}")
    print(f"   To: {signal.assignee}")
    print(f"   Reason: {signal.cancellation_reason_code}")
    
    print("\n📊 Step 2: Map Signal to RDF Triples")
    print("-" * 80)
    
    # Map to RDF
    mapper = FinancialSignalToRDFMapper(ontology_file="/mnt/user-data/outputs/financial_ontology.ttl")
    graph = mapper.map_signal(signal)
    
    # Get stats
    stats = mapper.get_stats()
    print(f"✅ Created {stats['total_triples']} RDF triples")
    print(f"   Subjects: {stats['subjects']}")
    print(f"   Predicates: {stats['predicates']}")
    print(f"   Objects: {stats['objects']}")
    
    print("\n🔍 Step 3: View RDF Triples (Turtle Format)")
    print("-" * 80)
    
    # Serialize to Turtle format
    turtle = mapper.serialize(format="turtle")
    print(turtle)
    
    print("\n💾 Step 4: Save to File")
    print("-" * 80)
    
    # Save to file
    output_file = "/mnt/user-data/outputs/sample_payment_cancellation.ttl"
    mapper.save(output_file, format="turtle")
    print(f"✅ Saved RDF graph to: {output_file}")
    
    print("\n🔎 Step 5: SPARQL Query Example")
    print("-" * 80)
    
    # Example SPARQL query
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    PREFIX inst: <http://example.org/financial/instance#>
    
    SELECT ?signal ?amount ?currency ?from ?to
    WHERE {
        ?signal a fin:PaymentCancellation .
        ?signal fin:hasAmount ?amountObj .
        ?amountObj fin:value ?amount .
        ?amountObj fin:currency ?currency .
        ?signal fin:fromInstitution ?fromInst .
        ?fromInst fin:bic ?from .
        ?signal fin:toInstitution ?toInst .
        ?toInst fin:bic ?to .
    }
    """
    
    print("Query:")
    print(query)
    
    results = mapper.query(query)
    print("\nResults:")
    for row in results:
        print(f"  Signal: {row.signal}")
        print(f"  Amount: {row.currency} {row.amount}")
        print(f"  From: {row['from']}")
        print(f"  To: {row.to}")
    
    print("\n" + "=" * 80)
    print("✅ ONTOLOGY MAPPING COMPLETE!")
    print("=" * 80)
    print("\nArchitecture Flow:")
    print("  ISO 20022 XML → Financial Signal → RDF Triples → Knowledge Graph")
    print("\nYou now have:")
    print("  1. ✅ Signal extraction (XML → Signals)")
    print("  2. ✅ Ontology mapping (Signals → RDF)")
    print("  3. ⏳ Next: Knowledge graph storage (RDF → Neo4j/GraphDB)")
    print("=" * 80 + "\n")


def test_with_uploaded_file(filepath: str):
    """Test with user's uploaded file"""
    
    print("\n" + "=" * 80)
    print("TESTING WITH YOUR UPLOADED FILE")
    print("=" * 80)
    
    # Read file
    with open(filepath, 'r') as f:
        xml_content = f.read()
    
    print(f"\n📥 File: {filepath}")
    
    # Extract signal
    pipeline = FinancialSignalExtractionPipeline()
    signals = pipeline.extract(xml_content)
    
    if not signals:
        print("❌ No signals extracted")
        return
    
    print(f"✅ Extracted {len(signals)} signal(s)")
    
    # Map to RDF
    mapper = FinancialSignalToRDFMapper(ontology_file="/mnt/user-data/outputs/financial_ontology.ttl")
    mapper.map_signals(signals)
    
    stats = mapper.get_stats()
    print(f"\n📊 RDF Graph Stats:")
    print(f"   Total triples: {stats['total_triples']}")
    
    # Save
    output_file = "/mnt/user-data/outputs/your_payment_cancellation.ttl"
    mapper.save(output_file, format="turtle")
    
    print(f"\n✅ Saved to: {output_file}")
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    # Test with sample data
    test_with_sample_xml()
    
    # Test with uploaded file if provided
    if len(sys.argv) > 1:
        test_with_uploaded_file(sys.argv[1])
