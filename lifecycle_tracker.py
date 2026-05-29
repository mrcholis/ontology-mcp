"""
Payment Lifecycle Tracker

Analyzes RDF files to show complete payment lifecycle and relationships between messages.

Usage:
    python lifecycle_tracker.py output/
    python lifecycle_tracker.py output/ --export
"""

import sys
import argparse
from pathlib import Path
from rdflib import Graph, Namespace
from datetime import datetime
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import json


# Namespaces
FIN = Namespace("http://example.org/financial/ontology#")
INST = Namespace("http://example.org/financial/instance#")


class MessageNode:
    """Represents a financial message"""
    
    def __init__(self, uri: str, message_type: str, timestamp: datetime, data: Dict[str, Any]):
        self.uri = uri
        self.message_type = message_type
        self.timestamp = timestamp
        self.data = data
        self.related_to: List['MessageNode'] = []
    
    def __repr__(self):
        return f"<{self.message_type} at {self.timestamp}>"


def load_all_rdf_files(directory: Path) -> Graph:
    """Load all TTL files from directory into one graph"""
    
    print(f"📂 Loading RDF files from: {directory}")
    
    combined_graph = Graph()
    combined_graph.bind("fin", FIN)
    combined_graph.bind("inst", INST)
    
    ttl_files = list(directory.glob("*.ttl"))
    
    if not ttl_files:
        print(f"❌ No .ttl files found in {directory}")
        return None
    
    print(f"📥 Found {len(ttl_files)} RDF file(s):\n")
    
    for ttl_file in ttl_files:
        print(f"   • {ttl_file.name}")
        try:
            combined_graph.parse(ttl_file, format="turtle")
        except Exception as e:
            print(f"     ⚠️  Error loading: {e}")
    
    print(f"\n✅ Loaded {len(combined_graph)} total triples\n")
    
    return combined_graph


def extract_messages(graph: Graph) -> List[MessageNode]:
    """Extract all messages from the graph"""
    
    # Query for all signal types
    query = """
    PREFIX fin: <http://example.org/financial/ontology#>
    PREFIX inst: <http://example.org/financial/instance#>
    
    SELECT ?signal ?type ?timestamp ?messageId ?caseId ?assignmentId ?statementId
           ?amount ?currency ?statusCode ?justificationCode ?balanceValid
           ?fromBIC ?toBIC
    WHERE {
        ?signal a ?type .
        FILTER(?type IN (
            fin:PaymentCancellation,
            fin:InvestigationResolution,
            fin:UnableToApply,
            fin:AccountStatement
        ))
        
        OPTIONAL { ?signal fin:timestamp ?timestamp }
        OPTIONAL { ?signal fin:messageId ?messageId }
        OPTIONAL { ?signal fin:caseId ?caseId }
        OPTIONAL { ?signal fin:assignmentId ?assignmentId }
        OPTIONAL { ?signal fin:statementId ?statementId }
        OPTIONAL { ?signal fin:statusCode ?statusCode }
        OPTIONAL { ?signal fin:justificationCode ?justificationCode }
        OPTIONAL { ?signal fin:balanceValid ?balanceValid }
        
        OPTIONAL {
            ?signal fin:hasAmount ?amountObj .
            ?amountObj fin:value ?amount .
            ?amountObj fin:currency ?currency .
        }
        
        OPTIONAL {
            ?signal fin:fromInstitution ?from .
            ?from fin:bic ?fromBIC .
        }
        
        OPTIONAL {
            ?signal fin:toInstitution ?to .
            ?to fin:bic ?toBIC .
        }
    }
    ORDER BY ?timestamp
    """
    
    results = graph.query(query)
    
    messages = []
    
    for row in results:
        # Determine message type
        type_str = str(row.type).split('#')[-1]
        
        # Parse timestamp
        timestamp = None
        if row.timestamp:
            try:
                timestamp = datetime.fromisoformat(str(row.timestamp))
            except:
                timestamp = datetime.now()
        
        # Build data dict
        data = {
            'message_id': str(row.messageId) if row.messageId else None,
            'case_id': str(row.caseId) if row.caseId else None,
            'assignment_id': str(row.assignmentId) if row.assignmentId else None,
            'statement_id': str(row.statementId) if row.statementId else None,
            'amount': float(row.amount) if row.amount else None,
            'currency': str(row.currency) if row.currency else None,
            'status_code': str(row.statusCode) if row.statusCode else None,
            'justification_code': str(row.justificationCode) if row.justificationCode else None,
            'balance_valid': str(row.balanceValid) if row.balanceValid else None,
            'from_bic': str(row.fromBIC) if row.fromBIC else None,
            'to_bic': str(row.toBIC) if row.toBIC else None,
        }
        
        node = MessageNode(
            uri=str(row.signal),
            message_type=type_str,
            timestamp=timestamp,
            data=data
        )
        
        messages.append(node)
    
    return messages


def detect_relationships(messages: List[MessageNode]) -> List[MessageNode]:
    """Detect relationships between messages based on IDs, amounts, institutions"""
    
    print("🔗 Detecting relationships...\n")
    
    # Index messages by various keys for quick lookup
    by_message_id = defaultdict(list)
    by_amount = defaultdict(list)
    by_institutions = defaultdict(list)
    
    for msg in messages:
        if msg.data['message_id']:
            by_message_id[msg.data['message_id']].append(msg)
        
        if msg.data['amount']:
            # Round to avoid floating point issues
            amount_key = f"{msg.data['currency']}_{round(msg.data['amount'])}"
            by_amount[amount_key].append(msg)
        
        if msg.data['from_bic'] and msg.data['to_bic']:
            # Create bidirectional institution pair key
            institutions = tuple(sorted([msg.data['from_bic'], msg.data['to_bic']]))
            by_institutions[institutions].append(msg)
    
    # Detect relationships
    relationships_found = 0
    
    for msg in messages:
        # Find related messages by different criteria
        
        # 1. Same amount and institutions (likely related transactions)
        if msg.data['amount'] and msg.data['from_bic']:
            amount_key = f"{msg.data['currency']}_{round(msg.data['amount'])}"
            institutions = tuple(sorted([msg.data['from_bic'], msg.data['to_bic']])) if msg.data['to_bic'] else None
            
            for other in messages:
                if other is msg:
                    continue
                
                # Check if related by amount AND institutions
                if other.data['amount']:
                    other_amount_key = f"{other.data['currency']}_{round(other.data['amount'])}"
                    other_institutions = tuple(sorted([other.data['from_bic'], other.data['to_bic']])) if other.data['to_bic'] else None
                    
                    # Similar amounts and same institutions = likely related
                    if (abs(msg.data['amount'] - other.data['amount']) < 1000 and 
                        institutions == other_institutions):
                        
                        if other not in msg.related_to:
                            msg.related_to.append(other)
                            relationships_found += 1
        
        # 2. Resolution relates to cancellation (by timeline proximity)
        if msg.message_type == "InvestigationResolution":
            # Find cancellation requests from similar time
            for other in messages:
                if other.message_type == "PaymentCancellation":
                    # Within 10 minutes and same institutions
                    if msg.timestamp and other.timestamp:
                        time_diff = abs((msg.timestamp - other.timestamp).total_seconds())
                        if (time_diff < 600 and  # 10 minutes
                            msg.data['from_bic'] == other.data['to_bic'] and
                            msg.data['to_bic'] == other.data['from_bic']):
                            
                            if other not in msg.related_to:
                                msg.related_to.append(other)
                                relationships_found += 1
    
    print(f"✅ Found {relationships_found} relationships\n")
    
    return messages


def display_timeline(messages: List[MessageNode]):
    """Display chronological timeline of all messages"""
    
    print("\n" + "=" * 80)
    print("  PAYMENT LIFECYCLE TIMELINE")
    print("=" * 80 + "\n")
    
    if not messages:
        print("No messages found.")
        return
    
    # Sort by timestamp
    sorted_messages = sorted(messages, key=lambda m: m.timestamp if m.timestamp else datetime.min)
    
    for i, msg in enumerate(sorted_messages, 1):
        # Format timestamp
        time_str = msg.timestamp.strftime("%Y-%m-%d %H:%M:%S") if msg.timestamp else "Unknown time"
        
        print(f"[{i}] {time_str}")
        print("─" * 80)
        
        # Message type and icon
        icons = {
            "PaymentCancellation": "📤",
            "InvestigationResolution": "✅" if msg.data.get('status_code') == 'ACCP' else "❌",
            "UnableToApply": "⚠️ ",
            "AccountStatement": "📊"
        }
        icon = icons.get(msg.message_type, "📄")
        
        # Format message type
        type_display = {
            "PaymentCancellation": "Payment Cancellation Request (camt.056)",
            "InvestigationResolution": "Investigation Resolution (camt.029)",
            "UnableToApply": "Unable to Apply (camt.026)",
            "AccountStatement": "Account Statement (camt.053)"
        }
        
        print(f"{icon} {type_display.get(msg.message_type, msg.message_type)}")
        
        # Display key info based on type
        if msg.message_type == "PaymentCancellation":
            print(f"   Case ID: {msg.data['case_id']}")
            if msg.data['amount']:
                print(f"   Amount: {msg.data['currency']} {msg.data['amount']:,.2f}")
            print(f"   Route: {msg.data['from_bic']} → {msg.data['to_bic']}")
            print(f"   📝 Customer requests cancellation")
        
        elif msg.message_type == "InvestigationResolution":
            status = msg.data['status_code']
            status_text = {
                'RJCR': 'REJECTED - Payment will proceed',
                'ACCP': 'ACCEPTED - Payment will be cancelled',
                'PDNG': 'PENDING - Under investigation'
            }.get(status, f'Status: {status}')
            
            print(f"   Status: {status_text}")
            print(f"   Route: {msg.data['from_bic']} → {msg.data['to_bic']}")
            
            if status == 'RJCR':
                print(f"   ⚠️  Cancellation denied - original payment continues")
            elif status == 'ACCP':
                print(f"   ✅ Cancellation approved - payment stopped")
        
        elif msg.message_type == "UnableToApply":
            print(f"   Assignment: {msg.data['assignment_id']}")
            if msg.data['amount']:
                print(f"   Amount: {msg.data['currency']} {msg.data['amount']:,.2f}")
            print(f"   Issue: {msg.data['justification_code']} (Incorrect/missing information)")
            print(f"   Route: {msg.data['from_bic']} → {msg.data['to_bic']}")
            print(f"   ⚠️  Payment cannot be processed")
        
        elif msg.message_type == "AccountStatement":
            print(f"   Statement: {msg.data['statement_id']}")
            balance_status = "✅ Valid" if msg.data['balance_valid'] == 'true' else "❌ Mismatch"
            print(f"   Balance Check: {balance_status}")
            if msg.data['balance_valid'] == 'false':
                print(f"   ⚠️  Balance discrepancy detected!")
        
        # Show relationships
        if msg.related_to:
            print(f"\n   🔗 Related to:")
            for related in msg.related_to:
                related_time = related.timestamp.strftime("%H:%M:%S") if related.timestamp else "?"
                related_type = type_display.get(related.message_type, related.message_type)
                print(f"      • {related_type} at {related_time}")
        
        print()
    
    print("=" * 80 + "\n")


def display_summary(messages: List[MessageNode]):
    """Display summary statistics"""
    
    print("=" * 80)
    print("  SUMMARY")
    print("=" * 80 + "\n")
    
    # Count by type
    type_counts = defaultdict(int)
    for msg in messages:
        type_counts[msg.message_type] += 1
    
    print("📊 Message Types:")
    for msg_type, count in type_counts.items():
        type_display = {
            "PaymentCancellation": "Payment Cancellation (camt.056)",
            "InvestigationResolution": "Investigation Resolution (camt.029)",
            "UnableToApply": "Unable to Apply (camt.026)",
            "AccountStatement": "Account Statement (camt.053)"
        }.get(msg_type, msg_type)
        print(f"   • {type_display}: {count}")
    
    # Total relationships
    total_relationships = sum(len(msg.related_to) for msg in messages)
    print(f"\n🔗 Total Relationships: {total_relationships}")
    
    # Key findings
    print(f"\n💡 Key Findings:")
    
    rejected_count = sum(1 for m in messages 
                        if m.message_type == "InvestigationResolution" 
                        and m.data.get('status_code') == 'RJCR')
    if rejected_count > 0:
        print(f"   • {rejected_count} cancellation(s) rejected")
    
    accepted_count = sum(1 for m in messages 
                        if m.message_type == "InvestigationResolution" 
                        and m.data.get('status_code') == 'ACCP')
    if accepted_count > 0:
        print(f"   • {accepted_count} cancellation(s) accepted")
    
    unable_count = sum(1 for m in messages if m.message_type == "UnableToApply")
    if unable_count > 0:
        print(f"   • {unable_count} payment(s) unable to process")
    
    invalid_balance = sum(1 for m in messages 
                         if m.message_type == "AccountStatement" 
                         and m.data.get('balance_valid') == 'false')
    if invalid_balance > 0:
        print(f"   • {invalid_balance} statement(s) with balance mismatch ⚠️")
    
    print("\n" + "=" * 80 + "\n")


def export_to_json(messages: List[MessageNode], output_file: Path):
    """Export lifecycle data to JSON for external visualization"""
    
    data = {
        "nodes": [],
        "links": []
    }
    
    # Create nodes
    node_map = {}
    for i, msg in enumerate(messages):
        node_id = f"node_{i}"
        node_map[msg.uri] = node_id
        
        data["nodes"].append({
            "id": node_id,
            "type": msg.message_type,
            "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
            "data": msg.data
        })
    
    # Create links
    for msg in messages:
        source_id = node_map[msg.uri]
        for related in msg.related_to:
            target_id = node_map[related.uri]
            data["links"].append({
                "source": source_id,
                "target": target_id,
                "type": "related_to"
            })
    
    # Save
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"📁 Exported lifecycle data to: {output_file}")


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="Analyze payment lifecycle from RDF files"
    )
    
    parser.add_argument(
        'directory',
        help='Directory containing RDF (.ttl) files'
    )
    
    parser.add_argument(
        '--export',
        action='store_true',
        help='Export to JSON for visualization'
    )
    
    args = parser.parse_args()
    
    directory = Path(args.directory)
    
    if not directory.exists():
        print(f"❌ Directory not found: {directory}")
        return
    
    # Load all RDF files
    graph = load_all_rdf_files(directory)
    
    if graph is None:
        return
    
    # Extract messages
    print("🔍 Extracting messages...")
    messages = extract_messages(graph)
    print(f"✅ Found {len(messages)} message(s)\n")
    
    if not messages:
        print("No messages found in RDF files.")
        return
    
    # Detect relationships
    messages = detect_relationships(messages)
    
    # Display timeline
    display_timeline(messages)
    
    # Display summary
    display_summary(messages)
    
    # Export if requested
    if args.export:
        output_file = directory / "lifecycle_data.json"
        export_to_json(messages, output_file)
        print(f"\n💡 Use this JSON with D3.js, Gephi, or other visualization tools\n")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python lifecycle_tracker.py output/")
        print("Try: python lifecycle_tracker.py --help")
        sys.exit(1)
    
    main()