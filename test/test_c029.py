"""
Test camt.029 (Resolution of Investigation) Extraction

Tests the new InvestigationResolutionSignal with your uploaded file.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.signals.financial_signal_extraction import FinancialSignalExtractionPipeline


def test_camt029():
    """Test camt.029 extraction"""
    
    print("\n" + "=" * 80)
    print("  Testing camt.029 - Resolution of Investigation")
    print("=" * 80 + "\n")
    
    # Read the camt.029 file
    camt029_file = "../xml_files/camt029_cancellation_rejected.xml"

    print(f"📥 Reading file: {camt029_file}")
    with open(camt029_file, 'r') as f:
        xml_content = f.read()
    
    print(f"✅ File size: {len(xml_content):,} bytes\n")
    
    # Extract signals
    print("🔍 Extracting signals...")
    pipeline = FinancialSignalExtractionPipeline()
    signals = pipeline.extract(xml_content)
    
    if not signals:
        print("❌ No signals extracted!")
        return
    
    print(f"✅ Extracted {len(signals)} signal(s)\n")
    
    # Display signal details
    for i, signal in enumerate(signals, 1):
        print("=" * 80)
        print(f"  Signal #{i}: {signal.signal_type.value}")
        print("=" * 80)
        
        print(f"\n📋 Basic Information:")
        print(f"   Message ID: {signal.message_id}")
        print(f"   Assignment ID: {signal.assignment_id}")
        print(f"   Timestamp: {signal.timestamp}")
        print(f"   Source System: {signal.source_system}")
        
        print(f"\n✅ Resolution Status:")
        print(f"   Status Code: {signal.status_code}")
        print(f"   Description: {signal.status_description}")
        print(f"   Cancellation Accepted: {signal.cancellation_accepted}")
        
        if signal.status_code == "RJCR":
            print(f"   ⚠️  REJECTED - Cancellation request was denied")
        elif signal.status_code == "ACCP":
            print(f"   ✅ ACCEPTED - Cancellation will be processed")
        
        print(f"\n🔗 Original Request:")
        print(f"   Original Message ID: {signal.original_message_id}")
        print(f"   Original Message Type: {signal.original_message_type}")
        print(f"   Original Instruction ID: {signal.original_instruction_id}")
        
        print(f"\n🏦 Institutions:")
        print(f"   From (Responding): {signal.assignor.bic} ({signal.assignor.institution_id})")
        print(f"   To (Requester): {signal.assignee.bic} ({signal.assignee.institution_id})")
        
        print(f"\n💡 What This Means:")
        if signal.status_code == "RJCR":
            print(f"   {signal.assignor.bic} has REJECTED the cancellation request")
            print(f"   from {signal.assignee.bic}. The original payment will proceed.")
        elif signal.status_code == "ACCP":
            print(f"   {signal.assignor.bic} has ACCEPTED the cancellation request")
            print(f"   from {signal.assignee.bic}. The original payment will be cancelled.")
        
        print(f"\n📊 Confidence: {signal.confidence}")
    
    print("\n" + "=" * 80)
    print("  ✅ Extraction Complete!")
    print("=" * 80)
    
    print("\n💡 Next Steps:")
    print("   1. Convert to RDF: python xml_to_rdf.py [path-to-file]")
    print("   2. Query relationships between camt.056 and camt.029")
    print("   3. See full cancellation lifecycle\n")


if __name__ == "__main__":
    test_camt029()