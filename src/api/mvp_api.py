"""
MVP Payment Intelligence API

Demonstrates full extraction pipeline:
XML → Signal Extraction → RDF Ontology Mapping → Insights

Uses existing ontology API to show semantic capabilities.
No database - everything in-memory.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
from datetime import datetime
from rdflib import Graph, Namespace
import os

# Import your existing components
from src.signals.financial_signal_extraction import FinancialSignalExtractionPipeline
from src.ontology.financial_ontology_mapper import FinancialSignalToRDFMapper
from src.signals.financial_signals import (
    PaymentCancellationSignal,
    InvestigationResolutionSignal,
    UnableToApplySignal,
    AccountStatementSignal
)

# Namespaces for RDF querying
FIN = Namespace("http://example.org/financial/ontology#")
INST = Namespace("http://example.org/financial/instance#")


app = FastAPI(
    title="Payment Intelligence MVP",
    description="Analyze ISO 20022 payment messages",
    version="0.1.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (serves app.js, etc.)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Initialize extraction pipeline and RDF mapper
pipeline = FinancialSignalExtractionPipeline()
mapper = FinancialSignalToRDFMapper()

# Load ontology schema for the mapper
try:
    ontology_path = "src/ontology/schema/financial_ontology.ttl"
    if os.path.exists(ontology_path):
        mapper = FinancialSignalToRDFMapper(ontology_file=ontology_path)
        print(f"✅ Loaded ontology from {ontology_path}")
    else:
        print(f"⚠️  Ontology file not found at {ontology_path}, using mapper without schema")
except Exception as e:
    print(f"⚠️  Could not load ontology: {e}")


# ============================================================================
# Helper Functions
# ============================================================================

def get_icon(signal) -> str:
    """Get emoji icon for signal type"""
    icons = {
        "PaymentCancellation": "📤",
        "InvestigationResolution": "✅",
        "UnableToApply": "⚠️",
        "AccountStatement": "📊"
    }
    
    # Special case: rejected resolution
    if isinstance(signal, InvestigationResolutionSignal):
        if signal.status_code == "RJCR":
            return "❌"
        elif signal.status_code == "ACCP":
            return "✅"
    
    return icons.get(signal.__class__.__name__, "📄")


def get_title(signal) -> str:
    """Get display title for signal"""
    titles = {
        "PaymentCancellation": "Payment Cancellation Request",
        "InvestigationResolution": "Investigation Resolution",
        "UnableToApply": "Unable to Apply",
        "AccountStatement": "Account Statement"
    }
    return titles.get(signal.__class__.__name__, "Financial Message")


def get_description(signal) -> str:
    """Get detailed description for signal"""
    
    if isinstance(signal, PaymentCancellationSignal):
        amount_str = f"${signal.amount.value:,.2f} {signal.amount.currency}" if signal.amount else "Unknown amount"
        reason = signal.cancellation_reason_code or "Unspecified"
        return f"{amount_str} • Reason: {reason} • {signal.assignor.bic} → {signal.assignee.bic}"
    
    elif isinstance(signal, InvestigationResolutionSignal):
        status_text = {
            "RJCR": "REJECTED - Payment will proceed",
            "ACCP": "ACCEPTED - Payment cancelled",
            "PDNG": "PENDING - Under review"
        }.get(signal.status_code, signal.status_code)
        return f"Status: {status_text} • {signal.assignor.bic} → {signal.assignee.bic}"
    
    elif isinstance(signal, UnableToApplySignal):
        amount_str = f"${signal.amount.value:,.2f} {signal.amount.currency}" if signal.amount else "Unknown amount"
        issue = signal.justification_code or "Unknown issue"
        return f"{amount_str} • Issue: {issue} • {signal.assignor.bic} → {signal.assignee.bic}"
    
    elif isinstance(signal, AccountStatementSignal):
        status = "✅ Valid" if signal.balance_valid else "❌ Mismatch"
        if not signal.balance_valid and signal.balance_discrepancy:
            return f"Balance check: {status} • Discrepancy: ${abs(signal.balance_discrepancy):,.2f}"
        return f"Balance check: {status}"
    
    return "Financial signal"


def get_severity(signal) -> str:
    """Get severity level for UI styling"""
    
    # Critical issues
    if isinstance(signal, AccountStatementSignal) and not signal.balance_valid:
        return "critical"
    
    # Errors
    if isinstance(signal, InvestigationResolutionSignal) and signal.status_code == "RJCR":
        return "error"
    
    if isinstance(signal, UnableToApplySignal):
        return "error"
    
    # Warnings
    if isinstance(signal, PaymentCancellationSignal):
        if signal.amount and signal.amount.value > 100000:
            return "warning"
    
    return "info"


def build_timeline_response(signals: List) -> List[Dict[str, Any]]:
    """Convert signals to timeline format for UI"""
    timeline = []
    
    for signal in sorted(signals, key=lambda s: s.timestamp if s.timestamp else datetime.min):
        timeline.append({
            "time": signal.timestamp.strftime("%Y-%m-%d %H:%M:%S") if signal.timestamp else "Unknown time",
            "short_time": signal.timestamp.strftime("%H:%M:%S") if signal.timestamp else "??:??:??",
            "type": signal.__class__.__name__,
            "icon": get_icon(signal),
            "title": get_title(signal),
            "description": get_description(signal),
            "severity": get_severity(signal)
        })
    
    return timeline


def generate_alerts(signals: List) -> List[Dict[str, Any]]:
    """Generate alerts from signals"""
    alerts = []
    
    for signal in signals:
        # High value transactions
        if hasattr(signal, 'amount') and signal.amount and signal.amount.value > 100000:
            alerts.append({
                "severity": "warning",
                "icon": "🟡",
                "title": "High Value Transaction",
                "message": f"Transaction amount: ${signal.amount.value:,.2f} {signal.amount.currency}"
            })
        
        # Rejected cancellations
        if isinstance(signal, InvestigationResolutionSignal) and signal.status_code == "RJCR":
            alerts.append({
                "severity": "error",
                "icon": "🟠",
                "title": "Cancellation Rejected",
                "message": "Payment cancellation request was rejected - payment will proceed"
            })
        
        # Accepted cancellations
        if isinstance(signal, InvestigationResolutionSignal) and signal.status_code == "ACCP":
            alerts.append({
                "severity": "info",
                "icon": "🔵",
                "title": "Cancellation Accepted",
                "message": "Payment cancellation request was accepted - payment stopped"
            })
        
        # Unable to apply
        if isinstance(signal, UnableToApplySignal):
            alerts.append({
                "severity": "error",
                "icon": "🟠",
                "title": "Payment Processing Issue",
                "message": f"Payment cannot be processed: {signal.justification_description or signal.justification_code}"
            })
        
        # Balance mismatch (CRITICAL)
        if isinstance(signal, AccountStatementSignal) and not signal.balance_valid:
            alerts.append({
                "severity": "critical",
                "icon": "🔴",
                "title": "Balance Mismatch Detected",
                "message": f"Account balance discrepancy: ${abs(signal.balance_discrepancy):,.2f}"
            })
    
    return alerts


def calculate_summary(signals: List) -> Dict[str, Any]:
    """Calculate summary statistics"""
    
    total_amount = 0
    institutions = set()
    message_types = set()
    
    for signal in signals:
        # Sum amounts
        if hasattr(signal, 'amount') and signal.amount:
            total_amount += signal.amount.value
        
        # Collect institutions
        if hasattr(signal, 'assignor') and signal.assignor:
            institutions.add(signal.assignor.bic)
        if hasattr(signal, 'assignee') and signal.assignee:
            institutions.add(signal.assignee.bic)
        
        # Message types
        message_types.add(signal.__class__.__name__)
    
    # Date range
    timestamps = [s.timestamp for s in signals if s.timestamp]
    date_range = None
    if timestamps:
        min_date = min(timestamps)
        max_date = max(timestamps)
        if min_date.date() == max_date.date():
            date_range = min_date.strftime("%Y-%m-%d")
        else:
            date_range = f"{min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
    
    return {
        "message_count": len(signals),
        "total_amount": total_amount,
        "institutions": list(institutions),
        "institution_count": len(institutions),
        "message_types": list(message_types),
        "date_range": date_range
    }


def detect_simple_relationships(signals: List) -> int:
    """Simple relationship count for MVP"""
    # Count signals that share institutions or amounts
    relationships = 0
    
    for i, sig1 in enumerate(signals):
        for sig2 in signals[i+1:]:
            # Same institutions (reversed)
            if (hasattr(sig1, 'assignor') and hasattr(sig2, 'assignor') and
                hasattr(sig1, 'assignee') and hasattr(sig2, 'assignee')):
                if (sig1.assignor.bic == sig2.assignee.bic and
                    sig1.assignee.bic == sig2.assignor.bic):
                    relationships += 1
            
            # Similar amounts
            if (hasattr(sig1, 'amount') and hasattr(sig2, 'amount') and
                sig1.amount and sig2.amount):
                if abs(sig1.amount.value - sig2.amount.value) < 1000:
                    relationships += 1
    
    return relationships


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Serve the frontend HTML"""
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Payment Intelligence MVP"}


@app.post("/api/analyze")
async def analyze_payment(file: UploadFile = File(...)):
    """
    Analyze uploaded ISO 20022 XML file
    
    Full pipeline:
    1. Extract signals from XML
    2. Map to RDF ontology
    3. Generate timeline
    4. Create alerts
    5. Detect relationships
    
    Returns:
        - Summary statistics
        - Timeline of events
        - Alerts
        - Relationship count
        - RDF triple count (proving semantic mapping)
        - RDF preview (sample triples)
    """
    
    try:
        # Read file
        xml_content = await file.read()
        
        # Validate it's not empty
        if not xml_content:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Decode XML
        try:
            xml_string = xml_content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="Invalid file encoding - expected UTF-8")
        
        # STEP 1: Extract signals
        try:
            signals = pipeline.extract(xml_string)
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to parse XML: {str(e)}"
            )
        
        # Check if any signals extracted
        if not signals:
            raise HTTPException(
                status_code=400,
                detail="No ISO 20022 signals found in file. Please upload a valid camt.026, camt.029, camt.053, or camt.056 file."
            )
        
        # STEP 2: Map to RDF (THIS IS THE KEY!)
        global last_rdf_graph, last_filename
        
        try:
            rdf_graph = mapper.map_signals(signals)
            triple_count = len(rdf_graph)
            
            # Store for download
            last_rdf_graph = rdf_graph
            last_filename = file.filename
            
            # Get FULL RDF for scrollable display
            rdf_preview_text = rdf_graph.serialize(format='turtle')
            
        except Exception as e:
            print(f"Warning: RDF mapping failed: {e}")
            triple_count = 0
            rdf_preview_text = "RDF mapping unavailable"
        
        # STEP 3: Generate insights
        summary = calculate_summary(signals)
        timeline = build_timeline_response(signals)
        alerts = generate_alerts(signals)
        relationships = detect_simple_relationships(signals)
        
        return {
            "success": True,
            "filename": file.filename,
            "summary": summary,
            "timeline": timeline,
            "alerts": alerts,
            "relationships": relationships,
            
            # NEW: Show semantic capabilities!
            "semantic": {
                "signals_extracted": len(signals),
                "rdf_triples": triple_count,
                "rdf_preview": rdf_preview_text,
                "ontology_mapped": triple_count > 0
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        # Unexpected error
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/api/demo/full")
async def get_full_demo():
    """
    Process all 4 XML files together to show complete lifecycle
    This demonstrates the full power of relationship detection
    """
    
    xml_files = [
        "xml_files/camt026_unable_to_apply.xml",
        "xml_files/camt056_cancellation_request.xml", 
        "xml_files/camt029_cancellation_rejected.xml",
        "xml_files/camt053_account_statement.xml"
    ]
    
    all_signals = []
    
    # Process each file
    for xml_file in xml_files:
        try:
            if not os.path.exists(xml_file):
                continue
                
            with open(xml_file, 'r') as f:
                xml_content = f.read()
            
            # Extract signals
            signals = pipeline.extract(xml_content)
            all_signals.extend(signals)
            
        except Exception as e:
            print(f"Error processing {xml_file}: {e}")
            continue
    
    if not all_signals:
        raise HTTPException(status_code=404, detail="Demo XML files not found")
    
    # Map ALL signals to RDF at once
    global last_rdf_graph, last_filename
    
    try:
        combined_rdf_graph = mapper.map_signals(all_signals)
        total_triples = len(combined_rdf_graph)
        
        # Store for download
        last_rdf_graph = combined_rdf_graph
        last_filename = "complete_lifecycle.xml"
        
        # Get FULL RDF (not truncated) for scrollable display
        rdf_preview = combined_rdf_graph.serialize(format='turtle')
        
    except Exception as e:
        print(f"RDF mapping error: {e}")
        total_triples = 0
        rdf_preview = f"RDF mapping failed: {str(e)}"
    
    # Generate combined response
    summary = calculate_summary(all_signals)
    timeline = build_timeline_response(all_signals)
    alerts = generate_alerts(all_signals)
    relationships = detect_simple_relationships(all_signals)
    
    return {
        "success": True,
        "filename": "Complete Payment Lifecycle (4 Messages)",
        "summary": summary,
        "timeline": timeline,
        "alerts": alerts,
        "relationships": relationships,
        "semantic": {
            "signals_extracted": len(all_signals),
            "rdf_triples": total_triples,
            "rdf_preview": rdf_preview,
            "ontology_mapped": total_triples > 0
        }
    }


@app.get("/api/demo")
async def get_demo_data():
    """
    Return demo data for testing frontend without file upload
    """
    return {
        "success": True,
        "filename": "demo_payment.xml",
        "summary": {
            "message_count": 4,
            "total_amount": 249850.0,
            "institutions": ["BLUEUSNY001", "GRENCHZZ002"],
            "institution_count": 2,
            "message_types": ["PaymentCancellation", "InvestigationResolution", "UnableToApply", "AccountStatement"],
            "date_range": "2022-07-18"
        },
        "timeline": [
            {
                "time": "2022-07-18 13:27:55",
                "short_time": "13:27:55",
                "type": "UnableToApply",
                "icon": "⚠️",
                "title": "Unable to Apply",
                "description": "$124,850.00 USD • Issue: IN39 • GRENCHZZ002 → BLUEUSNY001",
                "severity": "error"
            },
            {
                "time": "2022-07-18 13:28:33",
                "short_time": "13:28:33",
                "type": "PaymentCancellation",
                "icon": "📤",
                "title": "Payment Cancellation Request",
                "description": "$125,000.00 USD • Reason: CUST • BLUEUSNY001 → GRENCHZZ002",
                "severity": "warning"
            },
            {
                "time": "2022-07-18 13:29:48",
                "short_time": "13:29:48",
                "type": "InvestigationResolution",
                "icon": "❌",
                "title": "Investigation Resolution",
                "description": "Status: REJECTED - Payment will proceed • GRENCHZZ002 → BLUEUSNY001",
                "severity": "error"
            },
            {
                "time": "2022-07-18 14:00:00",
                "short_time": "14:00:00",
                "type": "AccountStatement",
                "icon": "📊",
                "title": "Account Statement",
                "description": "Balance check: ❌ Mismatch • Discrepancy: $100.00",
                "severity": "critical"
            }
        ],
        "alerts": [
            {
                "severity": "warning",
                "icon": "🟡",
                "title": "High Value Transaction",
                "message": "Transaction amount: $125,000.00 USD"
            },
            {
                "severity": "error",
                "icon": "🟠",
                "title": "Cancellation Rejected",
                "message": "Payment cancellation request was rejected - payment will proceed"
            },
            {
                "severity": "error",
                "icon": "🟠",
                "title": "Payment Processing Issue",
                "message": "Payment cannot be processed: Incorrect information"
            },
            {
                "severity": "critical",
                "icon": "🔴",
                "title": "Balance Mismatch Detected",
                "message": "Account balance discrepancy: $100.00"
            }
        ],
        "relationships": 3,
        "semantic": {
            "signals_extracted": 4,
            "rdf_triples": 185,
            "rdf_preview": "@prefix fin: <http://example.org/financial/ontology#> .\n@prefix inst: <http://example.org/financial/instance#> .\n\ninst:payment_cancellation_CASE_001 a fin:PaymentCancellation ;\n    fin:hasAmount inst:amount_CASE_001 ;\n    fin:fromInstitution inst:institution_BLUEUSNY001 .\n...",
            "ontology_mapped": True
        }
    }


# Store last analyzed data for RDF download
last_rdf_graph = None
last_filename = None

@app.get("/api/download/rdf")
async def download_rdf():
    """
    Download the RDF from the last analyzed file
    Demonstrates the semantic output
    """
    global last_rdf_graph, last_filename
    
    if last_rdf_graph is None:
        raise HTTPException(status_code=404, detail="No file has been analyzed yet")
    
    # Serialize to Turtle format
    rdf_content = last_rdf_graph.serialize(format='turtle')
    
    # Create filename
    base_name = last_filename.replace('.xml', '') if last_filename else 'payment'
    rdf_filename = f"{base_name}_ontology.ttl"
    
    from fastapi.responses import Response
    
    return Response(
        content=rdf_content,
        media_type="text/turtle",
        headers={
            "Content-Disposition": f"attachment; filename={rdf_filename}"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("  🚀 Payment Intelligence MVP")
    print("=" * 60)
    print("\n📍 Server running at: http://localhost:8000")
    print("📍 API docs at: http://localhost:8000/docs")
    print("\n💡 Drag and drop XML files to analyze!\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)