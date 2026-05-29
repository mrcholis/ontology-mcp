"""
Financial Signal Extraction - Test Your Banking Data

Tests ISO 20022 financial messages with signal extraction.
"""

from financial_signal_extraction import FinancialSignalExtractionPipeline
import sys


def test_financial_file(filepath):
    """Test signal extraction with ISO 20022 financial file"""
    
    print("\n" + "=" * 80)
    print("FINANCIAL SIGNAL EXTRACTION - ISO 20022")
    print("=" * 80)
    
    # Read file
    print(f"\n📥 Reading file: {filepath}")
    try:
        with open(filepath, 'r') as f:
            xml_content = f.read()
        print(f"   ✅ File loaded ({len(xml_content)} bytes)")
    except Exception as e:
        print(f"   ❌ Error reading file: {e}")
        return
    
    # Show preview
    print(f"\n📄 File preview (first 300 chars):")
    print("-" * 80)
    print(xml_content[:300])
    if len(xml_content) > 300:
        print("...")
    print("-" * 80)
    
    # Extract signals
    print("\n🔍 Extracting financial signals...")
    pipeline = FinancialSignalExtractionPipeline()
    
    try:
        signals = pipeline.extract(xml_content)
        
        print(f"\n🎯 RESULTS: {len(signals)} signal(s) extracted")
        
        if not signals:
            print("\n⚠️  No signals extracted. Possible reasons:")
            print("   - File is not ISO 20022 format")
            print("   - Unsupported message type (currently supports camt.056)")
            print("   - Missing required elements")
            return
        
        # Display each signal
        for i, signal in enumerate(signals, 1):
            print(f"\n{'=' * 80}")
            print(f"Signal {i}/{len(signals)}: {signal.signal_type.value.upper()}")
            print(f"{'=' * 80}")
            
            print(f"  Message ID: {signal.message_id}")
            print(f"  Timestamp: {signal.timestamp}")
            print(f"  Source System: {signal.source_system}")
            print(f"  Confidence: {signal.confidence}")
            
            # Payment cancellation specific
            if hasattr(signal, 'case_id'):
                print(f"\n  Cancellation Details:")
                print(f"    Case ID: {signal.case_id}")
                print(f"    Original Transaction: {signal.original_transaction_id}")
                print(f"    Original Message: {signal.original_message_id}")
                print(f"    Amount: {signal.amount}")
                print(f"    Settlement Date: {signal.settlement_date}")
                print(f"    Reason Code: {signal.cancellation_reason_code}")
                print(f"    Requested By: {signal.assignor}")
                print(f"    Assigned To: {signal.assignee}")
            
            # Payment initiation specific
            if hasattr(signal, 'debtor_agent') and signal.debtor_agent:
                print(f"\n  Payment Details:")
                print(f"    Transaction ID: {signal.transaction_id}")
                print(f"    Amount: {signal.amount}")
                print(f"    Debtor Agent: {signal.debtor_agent}")
                print(f"    Creditor Agent: {signal.creditor_agent}")
                print(f"    Settlement Method: {signal.settlement_method}")
        
        print("\n" + "=" * 80)
        print("✅ EXTRACTION SUCCESSFUL!")
        print("=" * 80)
        print(f"\nSummary:")
        print(f"  - Total signals: {len(signals)}")
        print(f"  - Signal types: {list(set(s.signal_type.value for s in signals))}")
        
    except Exception as e:
        print(f"\n❌ ERROR during extraction:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def test_with_sample_data():
    """Test with built-in sample financial data"""
    
    print("\n" + "=" * 80)
    print("TESTING WITH SAMPLE ISO 20022 DATA")
    print("=" * 80)
    
    # Sample camt.056 - simplified version
    sample_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Message xmlns="urn:issettled">
    <FIToFIPmtCxlReq>
        <Assgnmt xmlns="urn:iso:std:iso:20022:tech:xsd:camt.056.001.10">
            <Id>SAMPLE_CANCELLATION_001</Id>
            <Assgnr>
                <Agt>
                    <FinInstnId>
                        <BICFI>BANKUSNY001</BICFI>
                        <Othr><Id>samplebank</Id></Othr>
                    </FinInstnId>
                </Agt>
            </Assgnr>
            <Assgne>
                <Agt>
                    <FinInstnId>
                        <BICFI>OTHERBKZZ001</BICFI>
                        <Othr><Id>otherbank</Id></Othr>
                    </FinInstnId>
                </Agt>
            </Assgne>
            <CreDtTm>2024-01-20T10:00:00</CreDtTm>
        </Assgnmt>
        <Case xmlns="urn:iso:std:iso:20022:tech:xsd:camt.056.001.10">
            <Id>CASE_001</Id>
        </Case>
        <Undrlyg xmlns="urn:iso:std:iso:20022:tech:xsd:camt.056.001.10">
            <OrgnlGrpInfAndCxl>
                <OrgnlMsgId>MSG_ORIGINAL_001</OrgnlMsgId>
            </OrgnlGrpInfAndCxl>
            <TxInf>
                <OrgnlTxId>TXN_12345</OrgnlTxId>
                <OrgnlEndToEndId>E2E_67890</OrgnlEndToEndId>
                <OrgnlIntrBkSttlmAmt Ccy="USD">50000</OrgnlIntrBkSttlmAmt>
                <OrgnlIntrBkSttlmDt>2024-01-20</OrgnlIntrBkSttlmDt>
                <CxlRsnInf>
                    <Rsn><Cd>DUPL</Cd></Rsn>
                </CxlRsnInf>
            </TxInf>
        </Undrlyg>
    </FIToFIPmtCxlReq>
</Message>"""
    
    print("\n📥 Using sample camt.056 payment cancellation")
    
    pipeline = FinancialSignalExtractionPipeline()
    signals = pipeline.extract(sample_xml)
    
    print(f"\n🎯 RESULTS: {len(signals)} signal(s) extracted")
    
    for i, signal in enumerate(signals, 1):
        print(f"\n  Signal {i}:")
        print(f"    Type: {signal.signal_type.value}")
        print(f"    Amount: {signal.amount}")
        print(f"    Reason: {signal.cancellation_reason_code}")
        print(f"    From: {signal.assignor}")
        print(f"    To: {signal.assignee}")
    
    print("\n✅ Sample data test complete!")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ISO 20022 FINANCIAL SIGNAL EXTRACTION TESTER")
    print("=" * 80)
    
    # Check if user provided a file
    if len(sys.argv) > 1:
        # Test with user's file
        filepath = sys.argv[1]
        test_financial_file(filepath)
    else:
        # No file provided - show usage and run sample
        print("\nUsage:")
        print("  python test_financial_data.py <path-to-iso20022-file>")
        print("\nExample:")
        print("  python test_financial_data.py camt_056_001_10.xml")
        print("\n" + "=" * 80)
        
        # Run with sample data
        test_with_sample_data()
        
        print("\n" + "=" * 80)
        print("💡 TIP: To test YOUR financial data, run:")
        print("   python test_financial_data.py your_file.xml")
        print("=" * 80 + "\n")