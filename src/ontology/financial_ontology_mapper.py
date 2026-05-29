"""
Financial Signal to RDF Mapper

Converts financial signals into RDF triples according to the financial ontology.
"""

from typing import List, Optional, Dict, Any
from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, OWL, XSD
from datetime import datetime
import uuid

from src.signals.financial_signals import (
    FinancialSignal,
    PaymentCancellationSignal,
    PaymentInitiationSignal,
    PaymentSettlementSignal,
    AccountTransactionSignal,
    InvestigationResolutionSignal,
    UnableToApplySignal,
    AccountStatementSignal,
    StatementEntry,
    Amount,
    FinancialInstitution
)


# Define namespaces
FIN = Namespace("http://example.org/financial/ontology#")
ISO20022 = Namespace("http://example.org/iso20022/ontology#")
INST = Namespace("http://example.org/financial/instance#")


class FinancialSignalToRDFMapper:
    """
    Maps financial signals to RDF triples according to the financial ontology.
    
    Architecture:
        Financial Signal → RDF Triples → Knowledge Graph
    """
    
    def __init__(self, ontology_file: Optional[str] = None):
        """
        Initialize mapper with ontology.
        
        Args:
            ontology_file: Path to financial_ontology.ttl (optional)
        """
        self.graph = Graph()
        
        # Bind namespaces
        self.graph.bind("fin", FIN)
        self.graph.bind("iso20022", ISO20022)
        self.graph.bind("inst", INST)
        self.graph.bind("rdf", RDF)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("owl", OWL)
        self.graph.bind("xsd", XSD)
        
        # Load ontology if provided
        if ontology_file:
            try:
                self.graph.parse(ontology_file, format="turtle")
                print(f"✅ Loaded ontology from {ontology_file}")
            except Exception as e:
                print(f"⚠️  Could not load ontology: {e}")
    
    def map_signal(self, signal: FinancialSignal) -> Graph:
        """
        Map a financial signal to RDF triples.
        
        Args:
            signal: Financial signal to map
            
        Returns:
            RDF graph containing the mapped triples
        """
        # Dispatch to specific mapper based on signal type
        if isinstance(signal, PaymentCancellationSignal):
            return self._map_payment_cancellation(signal)
        elif isinstance(signal, InvestigationResolutionSignal):
            return self._map_investigation_resolution(signal)
        elif isinstance(signal, UnableToApplySignal):
            return self._map_unable_to_apply(signal)
        elif isinstance(signal, AccountStatementSignal):
            return self._map_account_statement(signal)
        elif isinstance(signal, PaymentInitiationSignal):
            return self._map_payment_initiation(signal)
        elif isinstance(signal, PaymentSettlementSignal):
            return self._map_payment_settlement(signal)
        elif isinstance(signal, AccountTransactionSignal):
            return self._map_account_transaction(signal)
        else:
            return self._map_generic_signal(signal)
    
    def map_signals(self, signals: List[FinancialSignal]) -> Graph:
        """
        Map multiple financial signals to RDF triples.
        
        Args:
            signals: List of financial signals
            
        Returns:
            RDF graph containing all mapped triples
        """
        for signal in signals:
            signal_graph = self.map_signal(signal)
            # Merge into main graph
            for triple in signal_graph:
                self.graph.add(triple)
        
        return self.graph
    
    def _map_payment_cancellation(self, signal: PaymentCancellationSignal) -> Graph:
        """Map payment cancellation signal to RDF"""
        g = Graph()
        
        # Bind namespaces
        g.bind("fin", FIN)
        g.bind("inst", INST)
        g.bind("xsd", XSD)
        
        # Create unique URI for this signal
        signal_uri = self._create_uri("payment_cancellation", signal.case_id)
        
        # Signal is a PaymentCancellation
        g.add((signal_uri, RDF.type, FIN.PaymentCancellation))
        g.add((signal_uri, RDF.type, ISO20022.camt_056))
        
        # Basic properties
        g.add((signal_uri, FIN.messageId, Literal(signal.message_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.caseId, Literal(signal.case_id, datatype=XSD.string)))
        
        if signal.timestamp:
            g.add((signal_uri, FIN.timestamp, Literal(signal.timestamp, datatype=XSD.dateTime)))
        
        g.add((signal_uri, FIN.confidence, Literal(signal.confidence, datatype=XSD.decimal)))
        g.add((signal_uri, FIN.sourceSystem, Literal(signal.source_system, datatype=XSD.string)))
        
        # Settlement date
        if signal.settlement_date:
            g.add((signal_uri, FIN.settlementDate, Literal(signal.settlement_date, datatype=XSD.date)))
        
        # Amount
        if signal.amount:
            amount_uri = self._create_uri("amount", signal.case_id)
            g.add((signal_uri, FIN.hasAmount, amount_uri))
            g = self._add_amount_triples(g, amount_uri, signal.amount)
        
        # Original transaction — also promote e2e to signal level
        if signal.original_transaction_id:
            tx_uri = self._create_uri("transaction", signal.original_transaction_id)
            g.add((signal_uri, FIN.originalTransaction, tx_uri))
            g.add((tx_uri, RDF.type, FIN.Transaction))
            g.add((tx_uri, FIN.transactionId, Literal(signal.original_transaction_id, datatype=XSD.string)))
            
            if signal.original_message_id:
                g.add((tx_uri, FIN.messageId, Literal(signal.original_message_id, datatype=XSD.string)))
            
            if signal.original_end_to_end_id:
                g.add((tx_uri, FIN.endToEndId, Literal(signal.original_end_to_end_id, datatype=XSD.string)))
                # Also write on signal directly — first-class join key
                g.add((signal_uri, FIN.endToEndId, Literal(signal.original_end_to_end_id, datatype=XSD.string)))
        
        # Cancellation reason
        if signal.cancellation_reason_code:
            reason_uri = self._create_uri("reason", signal.cancellation_reason_code)
            g.add((signal_uri, FIN.hasReason, reason_uri))
            g.add((reason_uri, RDF.type, FIN.CancellationReason))
            g.add((reason_uri, FIN.reasonCode, Literal(signal.cancellation_reason_code, datatype=XSD.string)))
        
        # Institutions
        if signal.assignor:
            assignor_uri = self._create_institution_uri(signal.assignor)
            g.add((signal_uri, FIN.fromInstitution, assignor_uri))
            g = self._add_institution_triples(g, assignor_uri, signal.assignor)
        
        if signal.assignee:
            assignee_uri = self._create_institution_uri(signal.assignee)
            g.add((signal_uri, FIN.toInstitution, assignee_uri))
            g = self._add_institution_triples(g, assignee_uri, signal.assignee)
        
        return g
    
    def _map_payment_initiation(self, signal: PaymentInitiationSignal) -> Graph:
        """Map payment initiation signal (pacs.008) to RDF — full transaction chain support."""
        g = Graph()
        g.bind("fin", FIN)
        g.bind("inst", INST)
        g.bind("xsd", XSD)

        uid = signal.transaction_id or signal.message_id
        signal_uri = self._create_uri("payment_initiation", uid)

        g.add((signal_uri, RDF.type, FIN.PaymentInitiation))
        g.add((signal_uri, RDF.type, ISO20022.pacs_008))

        g.add((signal_uri, FIN.messageId, Literal(signal.message_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.transactionId, Literal(signal.transaction_id, datatype=XSD.string)))

        if signal.end_to_end_id:
            g.add((signal_uri, FIN.endToEndId, Literal(signal.end_to_end_id, datatype=XSD.string)))
        if signal.instruction_id:
            g.add((signal_uri, FIN.instructionId, Literal(signal.instruction_id, datatype=XSD.string)))
        if signal.timestamp:
            g.add((signal_uri, FIN.timestamp, Literal(signal.timestamp, datatype=XSD.dateTime)))
        if signal.settlement_date:
            g.add((signal_uri, FIN.settlementDate, Literal(signal.settlement_date, datatype=XSD.string)))
        if signal.settlement_method:
            g.add((signal_uri, FIN.settlementMethod, Literal(signal.settlement_method, datatype=XSD.string)))

        g.add((signal_uri, FIN.confidence, Literal(signal.confidence, datatype=XSD.decimal)))
        g.add((signal_uri, FIN.sourceSystem, Literal(signal.source_system, datatype=XSD.string)))

        if signal.amount:
            amount_uri = self._create_uri("amount", uid)
            g.add((signal_uri, FIN.hasAmount, amount_uri))
            g = self._add_amount_triples(g, amount_uri, signal.amount)

        if signal.debtor_agent:
            d_uri = self._create_institution_uri(signal.debtor_agent)
            g.add((signal_uri, FIN.fromInstitution, d_uri))
            g = self._add_institution_triples(g, d_uri, signal.debtor_agent)

        if signal.creditor_agent:
            c_uri = self._create_institution_uri(signal.creditor_agent)
            g.add((signal_uri, FIN.toInstitution, c_uri))
            g = self._add_institution_triples(g, c_uri, signal.creditor_agent)

        return g

    def _map_payment_settlement(self, signal: PaymentSettlementSignal) -> Graph:
        """Map payment settlement signal (pacs.009) to RDF — full transaction chain support."""
        g = Graph()
        g.bind("fin", FIN)
        g.bind("inst", INST)
        g.bind("xsd", XSD)

        uid = signal.transaction_id or signal.message_id
        signal_uri = self._create_uri("payment_settlement", uid)

        g.add((signal_uri, RDF.type, FIN.PaymentSettlement))
        g.add((signal_uri, RDF.type, ISO20022.pacs_009))

        g.add((signal_uri, FIN.messageId, Literal(signal.message_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.transactionId, Literal(signal.transaction_id, datatype=XSD.string)))

        if signal.timestamp:
            g.add((signal_uri, FIN.timestamp, Literal(signal.timestamp, datatype=XSD.dateTime)))
        if signal.settlement_date:
            g.add((signal_uri, FIN.settlementDate, Literal(signal.settlement_date, datatype=XSD.string)))
        if signal.settlement_method:
            g.add((signal_uri, FIN.settlementMethod, Literal(signal.settlement_method, datatype=XSD.string)))

        g.add((signal_uri, FIN.confidence, Literal(signal.confidence, datatype=XSD.decimal)))
        g.add((signal_uri, FIN.sourceSystem, Literal(signal.source_system, datatype=XSD.string)))

        if signal.amount:
            amount_uri = self._create_uri("amount", uid)
            g.add((signal_uri, FIN.hasAmount, amount_uri))
            g = self._add_amount_triples(g, amount_uri, signal.amount)

        if signal.debtor_agent:
            d_uri = self._create_institution_uri(signal.debtor_agent)
            g.add((signal_uri, FIN.fromInstitution, d_uri))
            g = self._add_institution_triples(g, d_uri, signal.debtor_agent)

        if signal.creditor_agent:
            c_uri = self._create_institution_uri(signal.creditor_agent)
            g.add((signal_uri, FIN.toInstitution, c_uri))
            g = self._add_institution_triples(g, c_uri, signal.creditor_agent)

        return g
    
    def _map_account_transaction(self, signal: AccountTransactionSignal) -> Graph:
        """Map account transaction signal (camt.054) to RDF."""
        g = Graph()
        g.bind("fin", FIN)
        g.bind("inst", INST)
        g.bind("xsd", XSD)

        uid = signal.transaction_id or signal.message_id
        signal_uri = self._create_uri("account_transaction", uid)

        g.add((signal_uri, RDF.type, FIN.AccountTransaction))
        g.add((signal_uri, RDF.type, ISO20022.camt_054))

        g.add((signal_uri, FIN.messageId,      Literal(signal.message_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.transactionId,  Literal(signal.transaction_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.accountId,      Literal(signal.account_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.transactionType, Literal(signal.transaction_type, datatype=XSD.string)))

        if signal.timestamp:
            g.add((signal_uri, FIN.timestamp, Literal(signal.timestamp, datatype=XSD.dateTime)))
        if signal.booking_date:
            g.add((signal_uri, FIN.bookingDate, Literal(signal.booking_date, datatype=XSD.string)))
        if signal.value_date:
            g.add((signal_uri, FIN.valueDate, Literal(signal.value_date, datatype=XSD.string)))

        g.add((signal_uri, FIN.confidence,   Literal(signal.confidence, datatype=XSD.decimal)))
        g.add((signal_uri, FIN.sourceSystem, Literal(signal.source_system, datatype=XSD.string)))

        if signal.amount:
            amount_uri = self._create_uri("amount", uid)
            g.add((signal_uri, FIN.hasAmount, amount_uri))
            g = self._add_amount_triples(g, amount_uri, signal.amount)

        # endToEndId as first-class join key (extracted from NtryDtls/TxDtls/Refs in camt.054)
        # The extractor stores it in raw_data; we surface it here from the signal's raw_data
        e2e = None
        if signal.raw_data and isinstance(signal.raw_data, dict):
            e2e = signal.raw_data.get('end_to_end_id')
        if e2e:
            g.add((signal_uri, FIN.endToEndId, Literal(e2e, datatype=XSD.string)))

        return g

    def _map_generic_signal(self, signal: FinancialSignal) -> Graph:
        """Map generic financial signal to RDF"""
        g = Graph()
        g.bind("fin", FIN)
        g.bind("inst", INST)
        
        signal_uri = self._create_uri("signal", signal.message_id)
        
        g.add((signal_uri, RDF.type, FIN.FinancialSignal))
        g.add((signal_uri, FIN.messageId, Literal(signal.message_id, datatype=XSD.string)))
        
        if signal.timestamp:
            g.add((signal_uri, FIN.timestamp, Literal(signal.timestamp, datatype=XSD.dateTime)))
        
        return g
    
    def _add_amount_triples(self, g: Graph, amount_uri: URIRef, amount: Amount) -> Graph:
        """Add amount triples to graph"""
        g.add((amount_uri, RDF.type, FIN.Amount))
        g.add((amount_uri, FIN.value, Literal(amount.value, datatype=XSD.decimal)))
        g.add((amount_uri, FIN.currency, Literal(amount.currency, datatype=XSD.string)))
        return g
    
    def _add_institution_triples(self, g: Graph, inst_uri: URIRef, institution: FinancialInstitution) -> Graph:
        """Add financial institution triples to graph"""
        g.add((inst_uri, RDF.type, FIN.FinancialInstitution))
        
        if institution.bic:
            g.add((inst_uri, FIN.bic, Literal(institution.bic.strip(), datatype=XSD.string)))
        
        if institution.institution_id:
            cleaned_id = institution.institution_id.strip()
            if cleaned_id:
                g.add((inst_uri, FIN.institutionId, Literal(cleaned_id, datatype=XSD.string)))
        
        if institution.name:
            g.add((inst_uri, FIN.institutionName, Literal(institution.name, datatype=XSD.string)))
        
        return g
    
    def _create_uri(self, entity_type: str, identifier: str) -> URIRef:
        """Create a URI for an entity"""
        # Clean identifier
        clean_id = identifier.replace(" ", "_").replace("\n", "").strip()
        return INST[f"{entity_type}_{clean_id}"]
    
    def _create_institution_uri(self, institution: FinancialInstitution) -> URIRef:
        """Create URI for financial institution"""
        if institution.bic:
            return INST[f"institution_{institution.bic.strip()}"]
        elif institution.institution_id:
            clean_id = institution.institution_id.strip().replace(" ", "_").replace("\n", "")
            if clean_id:
                return INST[f"institution_{clean_id}"]
        return INST[f"institution_{uuid.uuid4().hex[:8]}"]
    
    def serialize(self, format: str = "turtle") -> str:
        """
        Serialize the RDF graph to string.
        
        Args:
            format: Serialization format (turtle, xml, n3, nt, json-ld)
            
        Returns:
            Serialized RDF graph
        """
        return self.graph.serialize(format=format)
    
    def save(self, filepath: str, format: str = "turtle"):
        """
        Save the RDF graph to file.
        
        Args:
            filepath: Path to save the file
            format: Serialization format
        """
        self.graph.serialize(destination=filepath, format=format)
        print(f"✅ Saved RDF graph to {filepath}")
    
    def query(self, sparql_query: str):
        """
        Execute SPARQL query on the graph.
        
        Args:
            sparql_query: SPARQL query string
            
        Returns:
            Query results
        """
        return self.graph.query(sparql_query)
    
    def _map_investigation_resolution(self, signal: InvestigationResolutionSignal) -> Graph:
        """Map investigation resolution signal (camt.029) to RDF"""
        g = Graph()
        
        # Create signal URI
        signal_id = f"investigation_resolution_{signal.assignment_id}_{signal.timestamp.strftime('%Y%m%d%H%M%S') if signal.timestamp else 'unknown'}"
        signal_uri = INST[signal_id]
        
        # Type
        g.add((signal_uri, RDF.type, FIN.InvestigationResolution))
        g.add((signal_uri, RDF.type, ISO20022.camt_029))
        
        # Properties
        g.add((signal_uri, FIN.messageId, Literal(signal.message_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.assignmentId, Literal(signal.assignment_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.statusCode, Literal(signal.status_code, datatype=XSD.string)))
        
        if signal.status_description:
            g.add((signal_uri, FIN.statusDescription, Literal(signal.status_description, datatype=XSD.string)))
        
        if signal.cancellation_accepted is not None:
            g.add((signal_uri, FIN.cancellationAccepted, Literal(signal.cancellation_accepted, datatype=XSD.boolean)))
        
        if signal.original_message_id:
            g.add((signal_uri, FIN.originalMessageId, Literal(signal.original_message_id, datatype=XSD.string)))
        
        if signal.original_message_type:
            g.add((signal_uri, FIN.originalMessageType, Literal(signal.original_message_type, datatype=XSD.string)))

        if getattr(signal, 'original_end_to_end_id', None):
            g.add((signal_uri, FIN.endToEndId, Literal(signal.original_end_to_end_id, datatype=XSD.string)))
        
        if signal.timestamp:
            g.add((signal_uri, FIN.timestamp, Literal(signal.timestamp, datatype=XSD.dateTime)))
        
        g.add((signal_uri, FIN.sourceSystem, Literal(signal.source_system, datatype=XSD.string)))
        g.add((signal_uri, FIN.confidence, Literal(signal.confidence, datatype=XSD.decimal)))
        
        # Institutions
        if signal.assignor:
            assignor_uri = self._create_institution_uri(signal.assignor)
            g.add((signal_uri, FIN.fromInstitution, assignor_uri))
            g = self._add_institution_triples(g, assignor_uri, signal.assignor)
        
        if signal.assignee:
            assignee_uri = self._create_institution_uri(signal.assignee)
            g.add((signal_uri, FIN.toInstitution, assignee_uri))
            g = self._add_institution_triples(g, assignee_uri, signal.assignee)
        
        return g
    
    def _map_unable_to_apply(self, signal: UnableToApplySignal) -> Graph:
        """Map unable to apply signal (camt.026) to RDF"""
        g = Graph()
        
        # Create signal URI
        signal_id = f"unable_to_apply_{signal.assignment_id}_{signal.timestamp.strftime('%Y%m%d%H%M%S') if signal.timestamp else 'unknown'}"
        signal_uri = INST[signal_id]
        
        # Type
        g.add((signal_uri, RDF.type, FIN.UnableToApply))
        g.add((signal_uri, RDF.type, ISO20022.camt_026))
        
        # Properties
        g.add((signal_uri, FIN.messageId, Literal(signal.message_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.assignmentId, Literal(signal.assignment_id, datatype=XSD.string)))
        
        if signal.original_instruction_id:
            g.add((signal_uri, FIN.originalInstructionId, Literal(signal.original_instruction_id, datatype=XSD.string)))
        
        if getattr(signal, 'original_end_to_end_id', None):
            g.add((signal_uri, FIN.endToEndId, Literal(signal.original_end_to_end_id, datatype=XSD.string)))
        
        if signal.justification_code:
            g.add((signal_uri, FIN.justificationCode, Literal(signal.justification_code, datatype=XSD.string)))
        
        if signal.justification_description:
            g.add((signal_uri, FIN.justificationDescription, Literal(signal.justification_description, datatype=XSD.string)))
        
        if signal.timestamp:
            g.add((signal_uri, FIN.timestamp, Literal(signal.timestamp, datatype=XSD.dateTime)))
        
        g.add((signal_uri, FIN.sourceSystem, Literal(signal.source_system, datatype=XSD.string)))
        g.add((signal_uri, FIN.confidence, Literal(signal.confidence, datatype=XSD.decimal)))
        
        # Amount
        if signal.amount:
            amount_uri = self._create_uri("amount", signal.assignment_id)
            g.add((signal_uri, FIN.hasAmount, amount_uri))
            g = self._add_amount_triples(g, amount_uri, signal.amount)
        
        # Institutions
        if signal.assignor:
            assignor_uri = self._create_institution_uri(signal.assignor)
            g.add((signal_uri, FIN.fromInstitution, assignor_uri))
            g = self._add_institution_triples(g, assignor_uri, signal.assignor)
        
        if signal.assignee:
            assignee_uri = self._create_institution_uri(signal.assignee)
            g.add((signal_uri, FIN.toInstitution, assignee_uri))
            g = self._add_institution_triples(g, assignee_uri, signal.assignee)
        
        return g
    
    def _map_account_statement(self, signal: AccountStatementSignal) -> Graph:
        """Map account statement signal (camt.053) to RDF"""
        g = Graph()
        
        # Create signal URI
        signal_id = f"account_statement_{signal.statement_id}_{signal.timestamp.strftime('%Y%m%d%H%M%S') if signal.timestamp else 'unknown'}"
        signal_uri = INST[signal_id]
        
        # Type
        g.add((signal_uri, RDF.type, FIN.AccountStatement))
        g.add((signal_uri, RDF.type, ISO20022.camt_053))
        
        # Properties
        g.add((signal_uri, FIN.messageId, Literal(signal.message_id, datatype=XSD.string)))
        g.add((signal_uri, FIN.statementId, Literal(signal.statement_id, datatype=XSD.string)))
        
        if signal.account_id:
            g.add((signal_uri, FIN.accountId, Literal(signal.account_id, datatype=XSD.string)))
        
        g.add((signal_uri, FIN.balanceValid, Literal(signal.balance_valid, datatype=XSD.boolean)))
        
        if signal.balance_discrepancy is not None:
            g.add((signal_uri, FIN.balanceDiscrepancy, Literal(signal.balance_discrepancy, datatype=XSD.decimal)))
        
        if signal.timestamp:
            g.add((signal_uri, FIN.timestamp, Literal(signal.timestamp, datatype=XSD.dateTime)))
        
        g.add((signal_uri, FIN.sourceSystem, Literal(signal.source_system, datatype=XSD.string)))
        g.add((signal_uri, FIN.confidence, Literal(signal.confidence, datatype=XSD.decimal)))
        
        # Opening balance
        if signal.opening_balance:
            opening_uri = INST[f"opening_balance_{signal.statement_id}"]
            g.add((opening_uri, RDF.type, FIN.Amount))
            g.add((opening_uri, FIN.value, Literal(signal.opening_balance.value, datatype=XSD.decimal)))
            g.add((opening_uri, FIN.currency, Literal(signal.opening_balance.currency, datatype=XSD.string)))
            g.add((signal_uri, FIN.openingBalance, opening_uri))
        
        # Closing balance
        if signal.closing_balance:
            closing_uri = INST[f"closing_balance_{signal.statement_id}"]
            g.add((closing_uri, RDF.type, FIN.Amount))
            g.add((closing_uri, FIN.value, Literal(signal.closing_balance.value, datatype=XSD.decimal)))
            g.add((closing_uri, FIN.currency, Literal(signal.closing_balance.currency, datatype=XSD.string)))
            g.add((signal_uri, FIN.closingBalance, closing_uri))
        
        # Entries
        if signal.entries:
            for i, entry in enumerate(signal.entries):
                entry_uri = INST[f"entry_{signal.statement_id}_{i}"]
                g.add((entry_uri, RDF.type, FIN.StatementEntry))
                g.add((entry_uri, FIN.creditDebitIndicator, Literal(entry.credit_debit_indicator, datatype=XSD.string)))
                
                # Entry amount
                entry_amount_uri = INST[f"entry_amount_{signal.statement_id}_{i}"]
                g.add((entry_amount_uri, RDF.type, FIN.Amount))
                g.add((entry_amount_uri, FIN.value, Literal(entry.amount.value, datatype=XSD.decimal)))
                g.add((entry_amount_uri, FIN.currency, Literal(entry.amount.currency, datatype=XSD.string)))
                g.add((entry_uri, FIN.hasAmount, entry_amount_uri))
                
                g.add((signal_uri, FIN.hasEntry, entry_uri))
        
        return g
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about the RDF graph"""
        return {
            "total_triples": len(self.graph),
            "subjects": len(set(self.graph.subjects())),
            "predicates": len(set(self.graph.predicates())),
            "objects": len(set(self.graph.objects()))
        }