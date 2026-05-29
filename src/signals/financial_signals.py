"""
Financial Domain Signals

Same architecture as agricultural signals, but for banking/finance domain.
Extracts signals from ISO 20022 financial messages.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class FinancialSignalType(Enum):
    """Types of financial domain signals"""
    PAYMENT_INITIATION = "payment_initiation"
    PAYMENT_CANCELLATION = "payment_cancellation"
    PAYMENT_SETTLEMENT = "payment_settlement"
    ACCOUNT_TRANSACTION = "account_transaction"
    FRAUD_ALERT = "fraud_alert"
    COMPLIANCE_EVENT = "compliance_event"
    LIQUIDITY_EVENT = "liquidity_event"
    FX_TRANSACTION = "fx_transaction"
    INVESTIGATION_RESOLUTION = "investigation_resolution"  # camt.029
    UNABLE_TO_APPLY = "unable_to_apply"  # camt.026
    ACCOUNT_STATEMENT = "account_statement"  # camt.053


@dataclass
class Amount:
    """Financial amount with currency"""
    value: float
    currency: str
    
    def __repr__(self):
        return f"{self.currency} {self.value:,.2f}"


@dataclass
class FinancialInstitution:
    """Financial institution identifier"""
    bic: Optional[str] = None  # BIC/SWIFT code
    institution_id: Optional[str] = None
    name: Optional[str] = None
    
    def __repr__(self):
        return self.bic or self.institution_id or self.name or "UNKNOWN"


@dataclass
class FinancialSignal:
    """Base class for all financial signals"""
    signal_type: FinancialSignalType
    timestamp: datetime
    message_id: str
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PaymentInitiationSignal(FinancialSignal):
    """Signal for payment initiation (pacs.008)"""
    signal_type: FinancialSignalType = FinancialSignalType.PAYMENT_INITIATION
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    transaction_id: str = "UNKNOWN"
    end_to_end_id: Optional[str] = None
    amount: Optional[Amount] = None
    debtor_agent: Optional[FinancialInstitution] = None
    creditor_agent: Optional[FinancialInstitution] = None
    settlement_method: Optional[str] = None
    settlement_date: Optional[str] = None
    instruction_id: Optional[str] = None
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class PaymentCancellationSignal(FinancialSignal):
    """Signal for payment cancellation request (camt.056)"""
    signal_type: FinancialSignalType = FinancialSignalType.PAYMENT_CANCELLATION
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    case_id: str = "UNKNOWN"
    original_message_id: str = "UNKNOWN"
    original_transaction_id: str = "UNKNOWN"
    original_end_to_end_id: Optional[str] = None
    original_instruction_id: Optional[str] = None
    amount: Optional[Amount] = None
    settlement_date: Optional[str] = None
    cancellation_reason_code: Optional[str] = None
    assignor: Optional[FinancialInstitution] = None
    assignee: Optional[FinancialInstitution] = None
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None
    

@dataclass
class PaymentSettlementSignal(FinancialSignal):
    """Signal for payment settlement confirmation"""
    signal_type: FinancialSignalType = FinancialSignalType.PAYMENT_SETTLEMENT
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    transaction_id: str = "UNKNOWN"
    amount: Optional[Amount] = None
    settlement_date: Optional[str] = None
    settlement_method: Optional[str] = None
    debtor_agent: Optional[FinancialInstitution] = None
    creditor_agent: Optional[FinancialInstitution] = None
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class AccountTransactionSignal(FinancialSignal):
    """Signal for account transaction (camt.053/camt.054)"""
    signal_type: FinancialSignalType = FinancialSignalType.ACCOUNT_TRANSACTION
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    transaction_id: str = "UNKNOWN"
    account_id: str = "UNKNOWN"
    amount: Optional[Amount] = None
    transaction_type: str = "UNKNOWN"  # DEBIT, CREDIT
    value_date: Optional[str] = None
    booking_date: Optional[str] = None
    debtor: Optional[str] = None
    creditor: Optional[str] = None
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class FraudAlertSignal(FinancialSignal):
    """Signal for potential fraud detection"""
    signal_type: FinancialSignalType = FinancialSignalType.FRAUD_ALERT
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    alert_type: str = "UNKNOWN"
    severity: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    transaction_id: Optional[str] = None
    amount: Optional[Amount] = None
    suspicious_pattern: str = "UNKNOWN"
    affected_institution: Optional[FinancialInstitution] = None
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceEventSignal(FinancialSignal):
    """Signal for compliance/regulatory events"""
    signal_type: FinancialSignalType = FinancialSignalType.COMPLIANCE_EVENT
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    event_type: str = "UNKNOWN"  # AML, KYC, SANCTIONS
    severity: str = "MEDIUM"
    transaction_id: Optional[str] = None
    affected_party: str = "UNKNOWN"
    regulation: str = "UNKNOWN"  # Which regulation triggered this
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class InvestigationResolutionSignal(FinancialSignal):
    """Signal for resolution of investigation (camt.029)"""
    signal_type: FinancialSignalType = FinancialSignalType.INVESTIGATION_RESOLUTION
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    assignment_id: str = "UNKNOWN"
    status_code: str = "UNKNOWN"  # RJCR (Rejected), ACCP (Accepted), etc.
    status_description: Optional[str] = None
    original_message_id: Optional[str] = None
    original_message_type: Optional[str] = None  # pacs.008, camt.056, etc.
    original_instruction_id: Optional[str] = None
    original_end_to_end_id: Optional[str] = None   # join key across lifecycle
    cancellation_accepted: Optional[bool] = None
    assignor: Optional[FinancialInstitution] = None
    assignee: Optional[FinancialInstitution] = None
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class UnableToApplySignal(FinancialSignal):
    """Signal for unable to apply notification (camt.026)"""
    signal_type: FinancialSignalType = FinancialSignalType.UNABLE_TO_APPLY
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    assignment_id: str = "UNKNOWN"
    original_instruction_id: Optional[str] = None
    original_end_to_end_id: Optional[str] = None   # join key across lifecycle
    amount: Optional[Amount] = None
    justification_code: Optional[str] = None  # e.g., "IN39"
    justification_description: Optional[str] = None
    missing_info: Optional[List[str]] = None
    incorrect_info: Optional[List[str]] = None
    assignor: Optional[FinancialInstitution] = None  # Who found the problem
    assignee: Optional[FinancialInstitution] = None  # Who needs to fix it
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class StatementEntry:
    """Individual entry in an account statement"""
    amount: Amount
    credit_debit_indicator: str  # CRDT or DBIT
    entry_reference: Optional[str] = None
    booking_date: Optional[str] = None
    value_date: Optional[str] = None
    bank_transaction_code: Optional[str] = None
    additional_info: Optional[str] = None


@dataclass
class AccountStatementSignal(FinancialSignal):
    """Signal for account statement (camt.053)"""
    signal_type: FinancialSignalType = FinancialSignalType.ACCOUNT_STATEMENT
    timestamp: datetime = None
    message_id: str = "UNKNOWN"
    statement_id: str = "UNKNOWN"
    account_id: Optional[str] = None
    opening_balance: Optional[Amount] = None
    closing_balance: Optional[Amount] = None
    entries: Optional[List[StatementEntry]] = None
    balance_valid: bool = True  # Calculated: does opening + entries = closing?
    balance_discrepancy: Optional[float] = None
    source_system: str = "unknown"
    confidence: float = 1.0
    raw_data: Optional[Dict[str, Any]] = None


# Message type to signal type mapping
ISO20022_MESSAGE_TYPES = {
    "pacs.008": FinancialSignalType.PAYMENT_INITIATION,
    "pacs.009": FinancialSignalType.PAYMENT_SETTLEMENT,
    "camt.053": FinancialSignalType.ACCOUNT_STATEMENT,
    "camt.054": FinancialSignalType.ACCOUNT_TRANSACTION,
    "camt.056": FinancialSignalType.PAYMENT_CANCELLATION,
    "camt.029": FinancialSignalType.INVESTIGATION_RESOLUTION,
    "camt.026": FinancialSignalType.UNABLE_TO_APPLY,
}