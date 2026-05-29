"""
Test All ISO 20022 Message Types

Tests extraction for:
- camt.056 (Payment Cancellation Request)
- camt.029 (Resolution of Investigation)
- camt.026 (Unable to Apply)
- camt.053 (Account Statement)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.signals.financial_signal_extraction import FinancialSignalExtractionPipeline


def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_message(file_path, message_name):
    """Test a single message type"""
    
    print_section(f"Testing {message_name}")
    
    print(f"📥 Reading file: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            xml_content = f.read()
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        print(f"   Make sure the file exists in xml_files/\n")
        return None
    
    print(f"✅ File size: {len(xml_content):,} bytes\n")
    
    # Extract signals
    print("🔍 Extracting signals...")
    pipeline = FinancialSignalExtractionPipeline()
    signals = pipeline.extract(xml_content)
    
    if not signals:
        print("❌ No signals extracted!")
        return None
    
    print(f"✅ Extracted {len(signals)} signal(s)\n")
    
    return signals[0] if signals else None


def display_cancellation(signal):
    """Display camt.056 cancellation details"""
    print(f"📋 Cancellation Request (camt.056)")
    print(f"   Case ID: {signal.case_id}")
    print(f"   Amount: {signal.amount.currency} {signal.amount.value:,.2f}")
    print(f"   From: {signal.assignor.bic} → To: {signal.assignee.bic}")
    print(f"   Reason: {signal.cancellation_reason_code}")
    print(f"   Original Transaction: {signal.original_transaction_id}")


def display_resolution(signal):
    """Display camt.029 resolution details"""
    print(f"📋 Investigation Resolution (camt.029)")
    print(f"   Status: {signal.status_code} - {signal.status_description}")
    print(f"   Cancellation Accepted: {signal.cancellation_accepted}")
    print(f"   From: {signal.assignor.bic} → To: {signal.assignee.bic}")
    print(f"   Original Message: {signal.original_message_id}")
    
    if signal.status_code == "RJCR":
        print(f"   ⚠️  Payment will PROCEED (cancellation rejected)")
    elif signal.status_code == "ACCP":
        print(f"   ✅ Payment will be CANCELLED (cancellation accepted)")


def display_unable_to_apply(signal):
    """Display camt.026 unable to apply details"""
    print(f"📋 Unable to Apply (camt.026)")
    print(f"   Assignment ID: {signal.assignment_id}")
    
    if signal.amount:
        print(f"   Amount: {signal.amount.currency} {signal.amount.value:,.2f}")
    
    print(f"   Justification: {signal.justification_code} - {signal.justification_description}")
    print(f"   From: {signal.assignor.bic} → To: {signal.assignee.bic}")
    print(f"   Original Instruction: {signal.original_instruction_id}")
    print(f"   ⚠️  Payment cannot be processed - info incorrect/missing")


def display_statement(signal):
    """Display camt.053 statement details"""
    print(f"📋 Account Statement (camt.053)")
    print(f"   Statement ID: {signal.statement_id}")
    
    if signal.account_id:
        print(f"   Account: {signal.account_id}")
    
    if signal.opening_balance:
        print(f"   Opening Balance: {signal.opening_balance.currency} {signal.opening_balance.value:,.2f}")
    
    if signal.entries:
        print(f"   Entries: {len(signal.entries)}")
        for i, entry in enumerate(signal.entries, 1):
            indicator = "+" if entry.credit_debit_indicator == "CRDT" else "-"
            print(f"      {i}. {indicator} {entry.amount.currency} {entry.amount.value:,.2f}")
    
    if signal.closing_balance:
        print(f"   Closing Balance: {signal.closing_balance.currency} {signal.closing_balance.value:,.2f}")
    
    # Balance validation
    if signal.balance_valid:
        print(f"   ✅ Balance validation: PASSED")
    else:
        print(f"   ❌ Balance validation: FAILED")
        if signal.balance_discrepancy:
            print(f"   ⚠️  Discrepancy: {signal.balance_discrepancy:,.2f}")


def main():
    """Test all message types"""
    
    print("\n" + "=" * 80)
    print("  ISO 20022 Message Type Testing Suite")
    print("=" * 80)
    print("\n  Testing 4 message types with your files...")
    
    # Test each message type
    signals = {}
    
    # 1. camt.056 - Cancellation Request
    signal = test_message("../xml_files/camt056_cancellation_request.xml", "camt.056 - Cancellation Request")
    if signal:
        signals['camt056'] = signal
        display_cancellation(signal)
    
    # 2. camt.029 - Resolution
    signal = test_message("../xml_files/camt029_cancellation_rejected.xml", "camt.029 - Resolution")
    if signal:
        signals['camt029'] = signal
        display_resolution(signal)
    
    # 3. camt.026 - Unable to Apply
    signal = test_message("../xml_files/camt026_unable_to_apply.xml", "camt.026 - Unable to Apply")
    if signal:
        signals['camt026'] = signal
        display_unable_to_apply(signal)
    
    # 4. camt.053 - Account Statement
    signal = test_message("../xml_files/camt053_account_statement.xml", "camt.053 - Account Statement")
    if signal:
        signals['camt053'] = signal
        display_statement(signal)
    
    # Summary
    print_section("Summary")
    
    print(f"✅ Successfully extracted {len(signals)} message types:\n")
    
    if 'camt056' in signals:
        print(f"   ✅ camt.056 - Payment Cancellation Request")
    
    if 'camt029' in signals:
        print(f"   ✅ camt.029 - Resolution of Investigation")
    
    if 'camt026' in signals:
        print(f"   ✅ camt.026 - Unable to Apply")
    
    if 'camt053' in signals:
        print(f"   ✅ camt.053 - Account Statement")
    
    print("\n💡 Next Steps:")
    print("   1. Convert all to RDF: python xml_to_rdf.py xml_files/*.xml")
    print("   2. Build lifecycle tracker")
    print("   3. Create relationship visualizer\n")


if __name__ == "__main__":
    main()