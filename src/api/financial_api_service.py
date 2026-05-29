"""
Financial Signal Extraction API

Run with: python -m src.api.financial_api_service
Or from src/api: python financial_api_service.py
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Import signal types
from src.signals.financial_signals import (
    FinancialSignalType,
    PaymentCancellationSignal,
    PaymentInitiationSignal,
    PaymentSettlementSignal,
    AccountTransactionSignal,
    FraudAlertSignal,
    ComplianceEventSignal,
    Amount,
    FinancialInstitution
)

# Import financial pipeline
from src.signals.financial_signal_extraction import FinancialSignalExtractionPipeline


app = FastAPI(
    title="Financial Signal Extraction API",
    description="Extract financial signals from ISO 20022 banking messages",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline
pipeline = FinancialSignalExtractionPipeline()


# Request/Response Models
class RawDataRequest(BaseModel):
    """Request body for signal extraction"""
    data: Union[str, Dict[str, Any]] = Field(
        ...,
        description="Raw data - ISO 20022 XML string or JSON object"
    )
    data_format: Optional[str] = Field(
        "auto",
        description="Data format: 'iso20022', 'xml', 'json', or 'auto' to detect"
    )
    source_system: Optional[str] = Field(
        None,
        description="Name of source system (e.g., 'swift', 'fedwire', 'ach')"
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "data": "<?xml version='1.0'?><Message>...</Message>",
                    "data_format": "iso20022",
                    "source_system": "swift"
                }
            ]
        }


class AmountResponse(BaseModel):
    """Amount in response"""
    value: float
    currency: str


class InstitutionResponse(BaseModel):
    """Financial institution in response"""
    bic: Optional[str] = None
    institution_id: Optional[str] = None
    name: Optional[str] = None


class SignalResponse(BaseModel):
    """Individual signal response"""
    signal_type: str
    timestamp: str
    message_id: str
    source_system: str
    confidence: float
    
    # Cancellation-specific
    case_id: Optional[str] = None
    original_transaction_id: Optional[str] = None
    original_message_id: Optional[str] = None
    original_end_to_end_id: Optional[str] = None
    cancellation_reason_code: Optional[str] = None
    assignor: Optional[InstitutionResponse] = None
    assignee: Optional[InstitutionResponse] = None
    
    # Payment-specific
    transaction_id: Optional[str] = None
    end_to_end_id: Optional[str] = None
    debtor_agent: Optional[InstitutionResponse] = None
    creditor_agent: Optional[InstitutionResponse] = None
    settlement_method: Optional[str] = None
    
    # Common
    amount: Optional[AmountResponse] = None
    settlement_date: Optional[str] = None


class ExtractionResponse(BaseModel):
    """Response from signal extraction"""
    success: bool
    signal_count: int
    signals: List[SignalResponse]
    source_format: str
    source_system: Optional[str]
    extracted_at: str
    processing_time_ms: float


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    supported_message_types: List[str]


# Helper functions
def signal_to_dict(signal: Any) -> Dict[str, Any]:
    """Convert signal object to dictionary for JSON response"""
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
    """Root endpoint - health check"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "supported_message_types": ["camt.056", "pacs.008", "pacs.009", "camt.053", "camt.054"]
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "supported_message_types": ["camt.056", "pacs.008", "pacs.009", "camt.053", "camt.054"]
    }


@app.post("/extract/signals", response_model=ExtractionResponse)
async def extract_signals(request: RawDataRequest):
    """
    Extract financial signals from ISO 20022 XML.
    
    Accepts ISO 20022 XML messages and returns extracted financial signals.
    """
    start_time = datetime.now()
    
    try:
        # Extract signals
        signals = pipeline.extract(request.data)
        
        # Determine source format
        if isinstance(request.data, str):
            detected_format = "iso20022" if "iso:std:iso:20022" in request.data or "camt" in request.data or "pacs" in request.data else "xml"
        else:
            detected_format = "json"
        
        source_format = request.data_format if request.data_format != "auto" else detected_format
        
        # Convert signals to response format
        signal_dicts = [signal_to_dict(s) for s in signals]
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return {
            "success": True,
            "signal_count": len(signals),
            "signals": signal_dicts,
            "source_format": source_format,
            "source_system": request.source_system,
            "extracted_at": datetime.now().isoformat(),
            "processing_time_ms": processing_time
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Signal extraction failed: {str(e)}"
        )


@app.post("/extract/signals/batch")
async def extract_signals_batch(
    requests: List[RawDataRequest] = Body(
        ...,
        description="List of ISO 20022 messages to process"
    )
):
    """Extract signals from multiple ISO 20022 messages in batch."""
    results = []
    
    for request in requests:
        try:
            signals = pipeline.extract(request.data)
            
            if isinstance(request.data, str):
                detected_format = "iso20022" if "iso:std:iso:20022" in request.data else "xml"
            else:
                detected_format = "json"
            
            source_format = request.data_format if request.data_format != "auto" else detected_format
            
            signal_dicts = [signal_to_dict(s) for s in signals]
            
            results.append({
                "success": True,
                "signal_count": len(signals),
                "signals": signal_dicts,
                "source_format": source_format,
                "source_system": request.source_system
            })
        
        except Exception as e:
            results.append({
                "success": False,
                "error": str(e),
                "source_system": request.source_system
            })
    
    successful = sum(1 for r in results if r.get("success", False))
    total_signals = sum(r.get("signal_count", 0) for r in results if r.get("success", False))
    
    return {
        "batch_size": len(requests),
        "successful": successful,
        "failed": len(requests) - successful,
        "total_signals_extracted": total_signals,
        "results": results,
        "processed_at": datetime.now().isoformat()
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


@app.get("/docs/examples")
async def get_examples():
    """Get example payloads for different ISO 20022 message types"""
    return {
        "examples": {
            "camt_056_cancellation": {
                "description": "Payment cancellation request (camt.056)",
                "data": """<?xml version="1.0"?>
<Message xmlns="urn:issettled">
    <FIToFIPmtCxlReq>
        <Assgnmt xmlns="urn:iso:std:iso:20022:tech:xsd:camt.056.001.10">
            <Id>CANCEL_001</Id>
            <Assgnr>
                <Agt><FinInstnId><BICFI>BANKUSNY001</BICFI></FinInstnId></Agt>
            </Assgnr>
            <Assgne>
                <Agt><FinInstnId><BICFI>OTHERBKZZ001</BICFI></FinInstnId></Agt>
            </Assgne>
            <CreDtTm>2024-01-20T10:00:00</CreDtTm>
        </Assgnmt>
        <Case xmlns="urn:iso:std:iso:20022:tech:xsd:camt.056.001.10">
            <Id>CASE_001</Id>
        </Case>
        <Undrlyg xmlns="urn:iso:std:iso:20022:tech:xsd:camt.056.001.10">
            <TxInf>
                <OrgnlTxId>TXN_12345</OrgnlTxId>
                <OrgnlIntrBkSttlmAmt Ccy="USD">50000</OrgnlIntrBkSttlmAmt>
                <CxlRsnInf><Rsn><Cd>CUST</Cd></Rsn></CxlRsnInf>
            </TxInf>
        </Undrlyg>
    </FIToFIPmtCxlReq>
</Message>""",
                "data_format": "iso20022",
                "source_system": "swift"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 80)
    print("Financial Signal Extraction API")
    print("=" * 80)
    print("\nStarting server...")
    print("Pipeline: Financial (ISO 20022)")
    print("Supported: camt.056 (Payment Cancellation)")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("\n" + "=" * 80 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)