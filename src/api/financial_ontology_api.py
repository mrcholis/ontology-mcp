"""
Financial Signal Extraction & Ontology API

Enhanced API that returns both JSON signals and RDF triples.

Run with: python -m src.api.financial_ontology_api
"""

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Signal extraction imports
from src.signals.financial_signals import FinancialSignalType
from src.signals.financial_signal_extraction import FinancialSignalExtractionPipeline

# Ontology mapping imports
from src.ontology.financial_ontology_mapper import FinancialSignalToRDFMapper

# Initialize
app = FastAPI(
    title="Financial Signal Extraction & Ontology API",
    description="Extract signals from ISO 20022 and map to RDF ontology",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipelines
signal_pipeline = FinancialSignalExtractionPipeline()

# Find ontology file
ontology_path = os.path.join(
    os.path.dirname(__file__),
    '..',
    'ontology',
    'schema',
    'financial_ontology.ttl'
)
ontology_mapper = FinancialSignalToRDFMapper(ontology_file=ontology_path)


# Models
class RawDataRequest(BaseModel):
    """Request for signal extraction"""
    data: Union[str, Dict[str, Any]]
    data_format: Optional[str] = "auto"
    source_system: Optional[str] = None
    output_format: Optional[str] = Field(
        "json",
        description="Output format: 'json' for signals, 'rdf' for triples"
    )


class HealthResponse(BaseModel):
    """Health check"""
    status: str
    version: str
    timestamp: str
    features: List[str]


# Helper function
def signal_to_dict(signal: Any) -> Dict[str, Any]:
    """Convert signal object to dictionary for JSON response"""
    from src.signals.financial_signals import (
        PaymentCancellationSignal,
        PaymentInitiationSignal
    )
    
    base = {
        "signal_type": signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type),
        "timestamp": signal.timestamp.isoformat() if signal.timestamp else datetime.now().isoformat(),
        "message_id": signal.message_id,
        "source_system": signal.source_system,
        "confidence": signal.confidence
    }
    
    # Add type-specific fields
    if isinstance(signal, PaymentCancellationSignal):
        base["case_id"] = signal.case_id
        base["original_transaction_id"] = signal.original_transaction_id
        base["original_message_id"] = signal.original_message_id
        base["original_end_to_end_id"] = signal.original_end_to_end_id
        base["cancellation_reason_code"] = signal.cancellation_reason_code
        
        if signal.amount:
            base["amount"] = {
                "value": signal.amount.value,
                "currency": signal.amount.currency
            }
        
        base["settlement_date"] = signal.settlement_date
        
        if signal.assignor:
            base["assignor"] = {
                "bic": signal.assignor.bic,
                "institution_id": signal.assignor.institution_id,
                "name": signal.assignor.name
            }
        
        if signal.assignee:
            base["assignee"] = {
                "bic": signal.assignee.bic,
                "institution_id": signal.assignee.institution_id,
                "name": signal.assignee.name
            }
    
    elif isinstance(signal, PaymentInitiationSignal):
        base["transaction_id"] = signal.transaction_id
        base["end_to_end_id"] = signal.end_to_end_id
        
        if signal.amount:
            base["amount"] = {
                "value": signal.amount.value,
                "currency": signal.amount.currency
            }
        
        base["settlement_method"] = signal.settlement_method
        base["settlement_date"] = signal.settlement_date
        
        if signal.debtor_agent:
            base["debtor_agent"] = {
                "bic": signal.debtor_agent.bic,
                "institution_id": signal.debtor_agent.institution_id
            }
        
        if signal.creditor_agent:
            base["creditor_agent"] = {
                "bic": signal.creditor_agent.bic,
                "institution_id": signal.creditor_agent.institution_id
            }
    
    return base


# Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "signal_extraction",
            "ontology_mapping",
            "rdf_export",
            "sparql_query"
        ]
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "signal_extraction",
            "ontology_mapping",
            "rdf_export",
            "multiple_formats"
        ]
    }


@app.post("/extract/signals")
async def extract_signals(request: RawDataRequest):
    """
    Extract signals and optionally convert to RDF.
    
    Set output_format to 'rdf' to get RDF triples instead of JSON signals.
    """
    try:
        # Extract signals
        signals = signal_pipeline.extract(request.data)
        
        if request.output_format == "rdf":
            # Map to RDF and return Turtle format
            mapper = FinancialSignalToRDFMapper(ontology_file=ontology_path)
            mapper.map_signals(signals)
            
            rdf_content = mapper.serialize(format="turtle")
            
            return Response(
                content=rdf_content,
                media_type="text/turtle",
                headers={
                    "Content-Disposition": "attachment; filename=signals.ttl"
                }
            )
        
        else:
            # Return JSON signals (original behavior)
            signal_dicts = [signal_to_dict(s) for s in signals]
            
            return {
                "success": True,
                "signal_count": len(signals),
                "signals": signal_dicts,
                "source_system": request.source_system,
                "extracted_at": datetime.now().isoformat()
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ontology/map")
async def map_to_ontology(request: RawDataRequest):
    """
    Extract signals and map to RDF ontology.
    
    Returns RDF triples in requested format (turtle, xml, json-ld, nt).
    """
    try:
        # Extract signals
        signals = signal_pipeline.extract(request.data)
        
        if not signals:
            return {
                "success": False,
                "error": "No signals extracted",
                "rdf_triples": 0
            }
        
        # Map to RDF
        mapper = FinancialSignalToRDFMapper(ontology_file=ontology_path)
        mapper.map_signals(signals)
        
        # Get stats
        stats = mapper.get_stats()
        
        # Determine format
        output_format = request.data_format if request.data_format != "auto" else "turtle"
        
        # Serialize
        rdf_content = mapper.serialize(format=output_format)
        
        # Map format to media type
        media_types = {
            "turtle": "text/turtle",
            "xml": "application/rdf+xml",
            "json-ld": "application/ld+json",
            "nt": "application/n-triples",
            "n3": "text/n3"
        }
        
        return Response(
            content=rdf_content,
            media_type=media_types.get(output_format, "text/turtle"),
            headers={
                "X-RDF-Triples": str(stats['total_triples']),
                "X-Signal-Count": str(len(signals))
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ontology/schema")
async def get_ontology_schema():
    """
    Get the financial ontology schema.
    
    Returns the ontology definition in Turtle format.
    """
    try:
        with open(ontology_path, "r") as f:
            ontology_content = f.read()
        
        return Response(
            content=ontology_content,
            media_type="text/turtle",
            headers={
                "Content-Disposition": "attachment; filename=financial_ontology.ttl"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs/ontology")
async def ontology_documentation():
    """Documentation about the financial ontology"""
    return {
        "ontology": {
            "name": "Financial Domain Ontology",
            "version": "1.0",
            "namespace": "http://example.org/financial/ontology#",
            "description": "Semantic representation of ISO 20022 financial signals"
        },
        "classes": [
            "FinancialSignal",
            "PaymentCancellation",
            "PaymentInitiation",
            "PaymentSettlement",
            "AccountTransaction",
            "FinancialInstitution",
            "Amount",
            "Transaction",
            "CancellationReason"
        ],
        "properties": {
            "object_properties": [
                "fromInstitution",
                "toInstitution",
                "hasAmount",
                "originalTransaction",
                "hasReason"
            ],
            "data_properties": [
                "messageId",
                "caseId",
                "transactionId",
                "timestamp",
                "settlementDate",
                "value",
                "currency",
                "bic",
                "reasonCode"
            ]
        },
        "supported_formats": [
            "turtle",
            "xml",
            "json-ld",
            "n-triples",
            "n3"
        ],
        "example_usage": {
            "extract_as_json": "POST /extract/signals with output_format=json",
            "extract_as_rdf": "POST /extract/signals with output_format=rdf",
            "map_to_ontology": "POST /ontology/map",
            "get_schema": "GET /ontology/schema"
        }
    }


@app.get("/signals/types")
async def get_signal_types():
    """Get all supported financial signal types"""
    return {
        "signal_types": [
            {
                "type": signal_type.value,
                "name": signal_type.name,
                "description": f"Signal representing {signal_type.value.replace('_', ' ')}"
            }
            for signal_type in FinancialSignalType
        ]
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 80)
    print("Financial Signal Extraction & Ontology API")
    print("=" * 80)
    print("\nFeatures:")
    print("  ✅ Signal extraction (ISO 20022 → Signals)")
    print("  ✅ Ontology mapping (Signals → RDF)")
    print("  ✅ Multiple RDF formats (Turtle, XML, JSON-LD)")
    print("\nEndpoints:")
    print("  POST /extract/signals - Extract signals (JSON or RDF)")
    print("  POST /ontology/map - Map to RDF ontology")
    print("  GET /ontology/schema - Get ontology definition")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("Ontology Docs: http://localhost:8000/docs/ontology")
    print("\n" + "=" * 80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)