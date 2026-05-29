"""
ISO 20022 Signal Extractor

Extracts financial signals from ISO 20022 XML messages.
Same architecture as ISO11783Extractor, but for banking domain.
"""

from typing import List, Any, Optional
import xml.etree.ElementTree as ET
from datetime import datetime
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

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
    FinancialSignalType,
    Amount,
    FinancialInstitution,
    ISO20022_MESSAGE_TYPES
)


class ISO20022Extractor:
    """
    Extracts signals from ISO 20022 financial messages.
    
    Supports:
    - camt.056 (Payment Cancellation Request)
    - pacs.008 (Payment Initiation)
    - pacs.009 (Payment Settlement)
    - camt.053 (Bank Statement)
    - camt.054 (Debit/Credit Notification)
    """
    
    # Namespace handling for ISO 20022
    NAMESPACES = {
        'ispcr': 'urn:iso:std:iso:20022:tech:xsd:camt.056.001.10',
        'pacs': 'urn:iso:std:iso:20022:tech:xsd:pacs.008.001.09',
        'head': 'urn:iso:std:iso:20022:tech:xsd:head.001.001.03',
    }
    
    def can_handle(self, raw_data: Any) -> bool:
        """Check if this is ISO 20022 XML"""
        if not isinstance(raw_data, str):
            return False
        
        # Check for ISO 20022 indicators
        iso20022_indicators = [
            'iso:std:iso:20022',
            'camt.056',
            'camt.029',
            'camt.026',
            'camt.053',
            'camt.054',
            'pacs.008',
            'pacs.009',
            'FIToFIPmtCxlReq',
            'RsltnOfInvstgtn',
            'UblToApply',
            'BkToCstmrStmt',
            'BkToCstmrDbtCdtNtfctn',
            'FIToFICstmrCdtTrf',
            'FinInstToFinInstCdtTrf',
        ]
        
        return any(indicator in raw_data for indicator in iso20022_indicators)
    
    def extract_signals(self, raw_data: str) -> List[FinancialSignal]:
        """Extract financial signals from ISO 20022 XML"""
        try:
            root = ET.fromstring(raw_data)
        except ET.ParseError as e:
            print(f"Failed to parse XML: {e}")
            return []
        
        # Detect message type
        message_type = self._detect_message_type(root, raw_data)
        
        if message_type == "camt.056":
            return self._extract_cancellation_signals(root)
        elif message_type == "camt.029":
            return self._extract_resolution_signals(root)
        elif message_type == "camt.026":
            return self._extract_unable_to_apply_signals(root)
        elif message_type == "camt.053":
            return self._extract_account_statement_signals(root)
        elif message_type == "pacs.008":
            return self._extract_payment_initiation_signals(root)
        elif message_type == "pacs.009":
            return self._extract_settlement_signals(root)
        elif message_type == "camt.054":
            return self._extract_account_transaction_signals(root)
        
        return []
    
    def _detect_message_type(self, root: ET.Element, raw_xml: str) -> Optional[str]:
        """Detect which ISO 20022 message type this is"""
        # Check message definition identifier in header
        msg_def = root.find('.//head:MsgDefIdr', self.NAMESPACES)
        if msg_def is not None and msg_def.text:
            # Extract base message type (e.g., "camt.056.001.10" -> "camt.056")
            parts = msg_def.text.split('.')
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
        
        # Fallback: check for known root elements
        if root.find('.//FIToFIPmtCxlReq') is not None or 'camt.056' in raw_xml:
            return "camt.056"
        if root.find('.//RsltnOfInvstgtn') is not None or 'camt.029' in raw_xml:
            return "camt.029"
        if root.find('.//UblToApply') is not None or 'camt.026' in raw_xml:
            return "camt.026"
        if root.find('.//BkToCstmrStmt') is not None or 'camt.053' in raw_xml:
            return "camt.053"
        if root.find('.//FIToFICstmrCdtTrf') is not None or 'pacs.008' in raw_xml:
            return "pacs.008"
        if root.find('.//FinInstToFinInstCdtTrf') is not None or 'pacs.009' in raw_xml:
            return "pacs.009"
        if root.find('.//BkToCstmrDbtCdtNtfctn') is not None or 'camt.054' in raw_xml:
            return "camt.054"
        
        return None
    
    def _extract_cancellation_signals(self, root: ET.Element) -> List[PaymentCancellationSignal]:
        """Extract payment cancellation signals from camt.056"""
        signals = []
        
        # Find the cancellation request element (namespace-agnostic)
        cancel_req = None
        for elem in root.iter():
            if elem.tag.endswith('FIToFIPmtCxlReq'):
                cancel_req = elem
                break
        
        if cancel_req is None:
            return signals
        
        # Find assignment, case, and underlying (namespace-agnostic search)
        assignment = None
        case = None
        underlying = None
        
        for elem in cancel_req.iter():
            if elem.tag.endswith('Assgnmt') and assignment is None:
                assignment = elem
            elif elem.tag.endswith('Case') and case is None:
                case = elem
            elif elem.tag.endswith('Undrlyg') and underlying is None:
                underlying = elem
        
        if assignment is None or underlying is None:
            return signals
        
        # Get assignment details (namespace-agnostic)
        assignment_id = self._find_element_text(assignment, 'Id')
        creation_time = self._find_element_text(assignment, 'CreDtTm')
        
        # Get assignor (who is requesting cancellation)
        assignor_bic = None
        assignor_id = None
        for elem in assignment.iter():
            if elem.tag.endswith('Assgnr'):
                assignor_bic = self._find_element_text(elem, 'BICFI')
                assignor_id = self._find_element_text(elem, 'Id')
                break
        
        # Get assignee (who should process it)
        assignee_bic = None
        assignee_id = None
        for elem in assignment.iter():
            if elem.tag.endswith('Assgne'):
                assignee_bic = self._find_element_text(elem, 'BICFI')
                assignee_id = self._find_element_text(elem, 'Id')
                break
        
        # Get case ID
        case_id = self._find_element_text(case, 'Id') if case is not None else None
        
        # Get transaction info
        tx_info = None
        for elem in underlying.iter():
            if elem.tag.endswith('TxInf'):
                tx_info = elem
                break
        
        if tx_info is None:
            return signals
        
        # Extract transaction details
        original_msg_id = self._find_element_text(underlying, 'OrgnlMsgId')
        original_tx_id = self._find_element_text(tx_info, 'OrgnlTxId')
        original_end_to_end = self._find_element_text(tx_info, 'OrgnlEndToEndId')
        original_instr_id = self._find_element_text(tx_info, 'OrgnlInstrId')
        
        # Extract amount
        amount_elem = None
        for elem in tx_info.iter():
            if elem.tag.endswith('OrgnlIntrBkSttlmAmt'):
                amount_elem = elem
                break
        
        if amount_elem is not None:
            amount = Amount(
                value=float(amount_elem.text) if amount_elem.text else 0.0,
                currency=amount_elem.get('Ccy', 'USD')
            )
        else:
            amount = Amount(value=0.0, currency='USD')
        
        # Extract settlement date
        settlement_date = self._find_element_text(tx_info, 'OrgnlIntrBkSttlmDt')
        
        # Extract cancellation reason
        cancel_reason = self._find_element_text(tx_info, 'Cd')
        
        # Parse timestamp
        timestamp = self._parse_timestamp(creation_time) if creation_time else datetime.now()
        
        # Create signal
        signal = PaymentCancellationSignal(
            signal_type=FinancialSignalType.PAYMENT_CANCELLATION,
            timestamp=timestamp,
            message_id=assignment_id or "UNKNOWN",
            case_id=case_id or assignment_id or "UNKNOWN",
            original_message_id=original_msg_id or "UNKNOWN",
            original_transaction_id=original_tx_id or "UNKNOWN",
            original_end_to_end_id=original_end_to_end,
            original_instruction_id=original_instr_id,
            amount=amount,
            settlement_date=settlement_date,
            cancellation_reason_code=cancel_reason,
            assignor=FinancialInstitution(
                bic=assignor_bic,
                institution_id=assignor_id
            ),
            assignee=FinancialInstitution(
                bic=assignee_bic,
                institution_id=assignee_id
            ),
            source_system=assignor_id or assignor_bic or "UNKNOWN",
            raw_data={
                "message_type": "camt.056.001.10",
                "case_id": case_id,
                "original_message_id": original_msg_id
            }
        )
        
        signals.append(signal)
        return signals
    
    def _extract_resolution_signals(self, root: ET.Element) -> List[InvestigationResolutionSignal]:
        """Extract investigation resolution signals from camt.029"""
        signals = []
        
        # Find the resolution element (namespace-agnostic)
        resolution = None
        for elem in root.iter():
            if elem.tag.endswith('RsltnOfInvstgtn'):
                resolution = elem
                break
        
        if resolution is None:
            return signals
        
        # Find assignment
        assignment = None
        for elem in resolution.iter():
            if elem.tag.endswith('Assgnmt'):
                assignment = elem
                break
        
        if assignment is None:
            return signals
        
        # Get assignment details
        assignment_id = self._find_element_text(assignment, 'Id')
        creation_time = self._find_element_text(assignment, 'CreDtTm')
        
        # Get assignor (who is responding)
        assignor_bic = None
        assignor_id = None
        for elem in assignment.iter():
            if elem.tag.endswith('Assgnr'):
                assignor_bic = self._find_element_text(elem, 'BICFI')
                assignor_id = self._find_element_text(elem, 'Id')
                break
        
        # Get assignee (who requested)
        assignee_bic = None
        assignee_id = None
        for elem in assignment.iter():
            if elem.tag.endswith('Assgne'):
                assignee_bic = self._find_element_text(elem, 'BICFI')
                assignee_id = self._find_element_text(elem, 'Id')
                break
        
        # Get status
        status_code = None
        status_elem = None
        for elem in resolution.iter():
            if elem.tag.endswith('Sts'):
                status_elem = elem
                break
        
        if status_elem is not None:
            status_code = self._find_element_text(status_elem, 'Conf')
        
        # Determine if cancellation was accepted
        cancellation_accepted = None
        if status_code:
            # RJCR = Rejected, ACCP = Accepted, PDNG = Pending
            if status_code == "ACCP":
                cancellation_accepted = True
            elif status_code == "RJCR":
                cancellation_accepted = False
        
        # Get cancellation details
        original_msg_id = None
        original_msg_type = None
        original_instr_id = None
        original_e2e_id = None
        
        cxl_details = None
        for elem in resolution.iter():
            if elem.tag.endswith('CxlDtls'):
                cxl_details = elem
                break
        
        if cxl_details is not None:
            original_msg_id = self._find_element_text(cxl_details, 'OrgnlMsgId')
            original_msg_type = self._find_element_text(cxl_details, 'OrgnlMsgNmId')
            original_instr_id = self._find_element_text(cxl_details, 'OrgnlInstrId')
            # e2e ID may be nested under TxInf inside CxlDtls
            for elem in cxl_details.iter():
                if elem.tag.endswith('OrgnlEndToEndId'):
                    original_e2e_id = elem.text
                    break
        
        # Parse timestamp
        timestamp = self._parse_timestamp(creation_time) if creation_time else datetime.now()
        
        # Status descriptions
        status_descriptions = {
            "RJCR": "Rejected - Cancellation not allowed",
            "ACCP": "Accepted - Cancellation will be processed",
            "PDNG": "Pending - Under investigation",
            "PART": "Partially accepted"
        }
        
        # Create signal
        signal = InvestigationResolutionSignal(
            signal_type=FinancialSignalType.INVESTIGATION_RESOLUTION,
            timestamp=timestamp,
            message_id=assignment_id or "UNKNOWN",
            assignment_id=assignment_id or "UNKNOWN",
            status_code=status_code or "UNKNOWN",
            status_description=status_descriptions.get(status_code, "Unknown status"),
            original_message_id=original_msg_id,
            original_message_type=original_msg_type,
            original_instruction_id=original_instr_id,
            original_end_to_end_id=original_e2e_id,
            cancellation_accepted=cancellation_accepted,
            assignor=FinancialInstitution(
                bic=assignor_bic,
                institution_id=assignor_id
            ),
            assignee=FinancialInstitution(
                bic=assignee_bic,
                institution_id=assignee_id
            ),
            source_system=assignor_id or assignor_bic or "UNKNOWN",
            raw_data={
                "message_type": "camt.029.001.11",
                "assignment_id": assignment_id,
                "status_code": status_code,
                "original_message_id": original_msg_id
            }
        )
        
        signals.append(signal)
        return signals
    
    def _extract_unable_to_apply_signals(self, root: ET.Element) -> List[UnableToApplySignal]:
        """Extract unable to apply signals from camt.026"""
        signals = []
        
        # Find the unable to apply element
        unable_elem = None
        for elem in root.iter():
            if elem.tag.endswith('UblToApply'):
                unable_elem = elem
                break
        
        if unable_elem is None:
            return signals
        
        # Find assignment
        assignment = None
        for elem in unable_elem.iter():
            if elem.tag.endswith('Assgnmt'):
                assignment = elem
                break
        
        if assignment is None:
            return signals
        
        # Get assignment details
        assignment_id = self._find_element_text(assignment, 'Id')
        creation_time = self._find_element_text(assignment, 'CreDtTm')
        
        # Get assignor (who found the problem)
        assignor_bic = None
        assignor_id = None
        for elem in assignment.iter():
            if elem.tag.endswith('Assgnr'):
                assignor_bic = self._find_element_text(elem, 'BICFI')
                assignor_id = self._find_element_text(elem, 'Id')
                break
        
        # Get assignee (who needs to fix it)
        assignee_bic = None
        assignee_id = None
        for elem in assignment.iter():
            if elem.tag.endswith('Assgne'):
                assignee_bic = self._find_element_text(elem, 'BICFI')
                assignee_id = self._find_element_text(elem, 'Id')
                break
        
        # Get underlying transaction details
        underlying = None
        for elem in unable_elem.iter():
            if elem.tag.endswith('Undrlyg'):
                underlying = elem
                break
        
        original_instr_id = None
        amount = None
        
        if underlying is not None:
            original_instr_id = self._find_element_text(underlying, 'OrgnlInstrId')
            original_e2e_id = self._find_element_text(underlying, 'OrgnlEndToEndId')
            
            # Get amount
            amount_elem = None
            for elem in underlying.iter():
                if elem.tag.endswith('OrgnlInstdAmt'):
                    amount_elem = elem
                    break
            
            if amount_elem is not None:
                amount = Amount(
                    value=float(amount_elem.text) if amount_elem.text else 0.0,
                    currency=amount_elem.get('Ccy', 'USD')
                )
        
        # Get justification
        justification_code = None
        justification_description = None
        missing_info = []
        incorrect_info = []
        
        justification = None
        for elem in unable_elem.iter():
            if elem.tag.endswith('Justfn'):
                justification = elem
                break
        
        if justification is not None:
            # Check for missing or incorrect info
            for elem in justification.iter():
                if elem.tag.endswith('MssngOrIncrrctInf'):
                    # Look for incorrect info code
                    for subelem in elem.iter():
                        if subelem.tag.endswith('Cd'):
                            justification_code = subelem.text
                            incorrect_info.append(justification_code)
        
        # Justification descriptions
        justification_descriptions = {
            "IN39": "Incorrect information - beneficiary details",
            "MS03": "Missing information - beneficiary account",
            "MS02": "Missing information - creditor name",
            "IN01": "Incorrect information - account number"
        }
        
        if justification_code:
            justification_description = justification_descriptions.get(
                justification_code,
                f"Issue code: {justification_code}"
            )
        
        # Parse timestamp
        timestamp = self._parse_timestamp(creation_time) if creation_time else datetime.now()
        
        # Create signal
        signal = UnableToApplySignal(
            signal_type=FinancialSignalType.UNABLE_TO_APPLY,
            timestamp=timestamp,
            message_id=assignment_id or "UNKNOWN",
            assignment_id=assignment_id or "UNKNOWN",
            original_instruction_id=original_instr_id,
            original_end_to_end_id=original_e2e_id if 'original_e2e_id' in dir() else None,
            amount=amount,
            justification_code=justification_code,
            justification_description=justification_description,
            missing_info=missing_info if missing_info else None,
            incorrect_info=incorrect_info if incorrect_info else None,
            assignor=FinancialInstitution(
                bic=assignor_bic,
                institution_id=assignor_id
            ),
            assignee=FinancialInstitution(
                bic=assignee_bic,
                institution_id=assignee_id
            ),
            source_system=assignor_id or assignor_bic or "UNKNOWN",
            raw_data={
                "message_type": "camt.026.001.09",
                "assignment_id": assignment_id,
                "justification_code": justification_code
            }
        )
        
        signals.append(signal)
        return signals
    
    def _extract_account_statement_signals(self, root: ET.Element) -> List[AccountStatementSignal]:
        """Extract account statement signals from camt.053"""
        signals = []
        
        # Find the statement element
        stmt_elem = None
        for elem in root.iter():
            if elem.tag.endswith('Stmt'):
                stmt_elem = elem
                break
        
        if stmt_elem is None:
            return signals
        
        # Get statement ID
        statement_id = self._find_element_text(stmt_elem, 'Id')
        
        # Get account ID
        account_id = None
        acct_elem = None
        for elem in stmt_elem.iter():
            if elem.tag.endswith('Acct'):
                acct_elem = elem
                break
        
        if acct_elem is not None:
            account_id = self._find_element_text(acct_elem, 'Id')
        
        # Get balances
        opening_balance = None
        closing_balance = None
        
        for elem in stmt_elem.iter():
            if elem.tag.endswith('Bal'):
                # Get balance type
                bal_type = None
                for subelem in elem.iter():
                    if subelem.tag.endswith('Cd'):
                        bal_type = subelem.text
                        break
                
                # Get amount
                amount_elem = None
                for subelem in elem.iter():
                    if subelem.tag.endswith('Amt'):
                        amount_elem = subelem
                        break
                
                if amount_elem is not None:
                    amount = Amount(
                        value=float(amount_elem.text) if amount_elem.text else 0.0,
                        currency=amount_elem.get('Ccy', 'USD')
                    )
                    
                    if bal_type == 'OPBD':  # Opening Balance
                        opening_balance = amount
                    elif bal_type == 'CLBD':  # Closing Balance
                        closing_balance = amount
        
        # Get entries
        entries = []
        for elem in stmt_elem.iter():
            if elem.tag.endswith('Ntry'):
                # Get amount
                amount_elem = None
                for subelem in elem.iter():
                    if subelem.tag.endswith('Amt'):
                        amount_elem = subelem
                        break
                
                # Get credit/debit indicator
                cd_indicator = self._find_element_text(elem, 'CdtDbtInd')
                
                if amount_elem is not None and cd_indicator:
                    entry_amount = Amount(
                        value=float(amount_elem.text) if amount_elem.text else 0.0,
                        currency=amount_elem.get('Ccy', 'USD')
                    )
                    
                    entry = StatementEntry(
                        amount=entry_amount,
                        credit_debit_indicator=cd_indicator,
                        entry_reference=self._find_element_text(elem, 'AcctSvcrRef'),
                        booking_date=self._find_element_text(elem, 'BookgDt'),
                        value_date=self._find_element_text(elem, 'ValDt')
                    )
                    entries.append(entry)
        
        # Validate balance
        balance_valid = True
        balance_discrepancy = None
        
        if opening_balance and closing_balance and entries:
            # Calculate expected closing balance
            expected_closing = opening_balance.value
            
            for entry in entries:
                if entry.credit_debit_indicator == 'CRDT':
                    expected_closing += entry.amount.value
                elif entry.credit_debit_indicator == 'DBIT':
                    expected_closing -= entry.amount.value
            
            # Check if it matches
            discrepancy = closing_balance.value - expected_closing
            
            if abs(discrepancy) > 0.01:  # Allow for rounding errors
                balance_valid = False
                balance_discrepancy = discrepancy
        
        # Create signal
        signal = AccountStatementSignal(
            signal_type=FinancialSignalType.ACCOUNT_STATEMENT,
            timestamp=datetime.now(),
            message_id=statement_id or "UNKNOWN",
            statement_id=statement_id or "UNKNOWN",
            account_id=account_id,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            entries=entries,
            balance_valid=balance_valid,
            balance_discrepancy=balance_discrepancy,
            source_system="statement_system",
            raw_data={
                "message_type": "camt.053.001.08",
                "statement_id": statement_id,
                "entry_count": len(entries)
            }
        )
        
        signals.append(signal)
        return signals
    
    def _find_element_text(self, parent: ET.Element, tag_suffix: str) -> Optional[str]:
        """Find element by tag suffix (namespace-agnostic) and return its text"""
        for elem in parent.iter():
            if elem.tag.endswith(tag_suffix):
                return elem.text
        return None
    
    def _extract_payment_initiation_signals(self, root: ET.Element) -> List[PaymentInitiationSignal]:
        """Extract payment initiation signals from pacs.008 (FIToFICstmrCdtTrf)."""
        signals = []

        # Locate the top-level transfer element (namespace-agnostic)
        trf_elem = None
        for elem in root.iter():
            if elem.tag.endswith('FIToFICstmrCdtTrf'):
                trf_elem = elem
                break
        if trf_elem is None:
            return signals

        # --- Group header ---
        grp_hdr = None
        for elem in trf_elem.iter():
            if elem.tag.endswith('GrpHdr'):
                grp_hdr = elem
                break

        msg_id = self._find_element_text(grp_hdr, 'MsgId') if grp_hdr else None
        creation_time = self._find_element_text(grp_hdr, 'CreDtTm') if grp_hdr else None
        timestamp = self._parse_timestamp(creation_time) if creation_time else datetime.now()

        # Settlement info (shared across transactions)
        sttlm_mtd = None
        if grp_hdr is not None:
            for elem in grp_hdr.iter():
                if elem.tag.endswith('SttlmMtd'):
                    sttlm_mtd = elem.text
                    break

        # --- Per-transaction credit transfer info ---
        for tx_elem in trf_elem.iter():
            if not tx_elem.tag.endswith('CdtTrfTxInf'):
                continue

            # Payment IDs
            instr_id    = self._find_element_text(tx_elem, 'InstrId')
            end_to_end  = self._find_element_text(tx_elem, 'EndToEndId')
            tx_id       = self._find_element_text(tx_elem, 'TxId') or self._find_element_text(tx_elem, 'UETxRef')

            # Interbank settlement amount
            amount = None
            for elem in tx_elem.iter():
                if elem.tag.endswith('IntrBkSttlmAmt'):
                    try:
                        amount = Amount(
                            value=float(elem.text) if elem.text else 0.0,
                            currency=elem.get('Ccy', 'USD')
                        )
                    except (ValueError, TypeError):
                        pass
                    break

            # Settlement date
            sttlm_date = self._find_element_text(tx_elem, 'IntrBkSttlmDt')

            # Instructing agent (debtor bank — sends the payment)
            instg_bic = instg_id = None
            for elem in tx_elem.iter():
                if elem.tag.endswith('InstgAgt'):
                    instg_bic = self._find_element_text(elem, 'BICFI')
                    instg_id  = self._find_element_text(elem, 'Id')
                    break

            # Instructed agent (creditor bank — receives the payment)
            instd_bic = instd_id = None
            for elem in tx_elem.iter():
                if elem.tag.endswith('InstdAgt'):
                    instd_bic = self._find_element_text(elem, 'BICFI')
                    instd_id  = self._find_element_text(elem, 'Id')
                    break

            signal = PaymentInitiationSignal(
                signal_type=FinancialSignalType.PAYMENT_INITIATION,
                timestamp=timestamp,
                message_id=msg_id or instr_id or 'UNKNOWN',
                transaction_id=tx_id or instr_id or 'UNKNOWN',
                end_to_end_id=end_to_end,
                instruction_id=instr_id,
                amount=amount,
                settlement_method=sttlm_mtd,
                settlement_date=sttlm_date,
                debtor_agent=FinancialInstitution(bic=instg_bic, institution_id=instg_id),
                creditor_agent=FinancialInstitution(bic=instd_bic, institution_id=instd_id),
                source_system=instg_bic or instg_id or 'pacs.008',
                confidence=1.0,
                raw_data={
                    'message_type': 'pacs.008',
                    'message_id': msg_id,
                    'transaction_id': tx_id,
                    'settlement_method': sttlm_mtd,
                }
            )
            signals.append(signal)

        return signals

    def _extract_settlement_signals(self, root: ET.Element) -> List[PaymentSettlementSignal]:
        """Extract settlement signals from pacs.009 (FinInstToFinInstCdtTrf)."""
        signals = []

        # pacs.009 root element
        trf_elem = None
        for elem in root.iter():
            if elem.tag.endswith('FinInstToFinInstCdtTrf') or elem.tag.endswith('FIToFIPmtStsRpt'):
                trf_elem = elem
                break
        if trf_elem is None:
            return signals

        # Group header
        grp_hdr = None
        for elem in trf_elem.iter():
            if elem.tag.endswith('GrpHdr'):
                grp_hdr = elem
                break

        msg_id = self._find_element_text(grp_hdr, 'MsgId') if grp_hdr else None
        creation_time = self._find_element_text(grp_hdr, 'CreDtTm') if grp_hdr else None
        timestamp = self._parse_timestamp(creation_time) if creation_time else datetime.now()

        # Per-transaction info
        for tx_elem in trf_elem.iter():
            if not tx_elem.tag.endswith('CdtTrfTxInf'):
                continue

            tx_id  = self._find_element_text(tx_elem, 'InstrId') or self._find_element_text(tx_elem, 'TxId')

            # Interbank settlement amount
            amount = None
            for elem in tx_elem.iter():
                if elem.tag.endswith('IntrBkSttlmAmt'):
                    try:
                        amount = Amount(
                            value=float(elem.text) if elem.text else 0.0,
                            currency=elem.get('Ccy', 'USD')
                        )
                    except (ValueError, TypeError):
                        pass
                    break

            sttlm_date = self._find_element_text(tx_elem, 'IntrBkSttlmDt')

            # Settlement method
            sttlm_mtd = None
            for elem in tx_elem.iter():
                if elem.tag.endswith('SttlmMtd'):
                    sttlm_mtd = elem.text
                    break

            # Instructing / instructed agents
            instg_bic = instg_id = None
            for elem in tx_elem.iter():
                if elem.tag.endswith('InstgAgt'):
                    instg_bic = self._find_element_text(elem, 'BICFI')
                    instg_id  = self._find_element_text(elem, 'Id')
                    break

            instd_bic = instd_id = None
            for elem in tx_elem.iter():
                if elem.tag.endswith('InstdAgt'):
                    instd_bic = self._find_element_text(elem, 'BICFI')
                    instd_id  = self._find_element_text(elem, 'Id')
                    break

            signal = PaymentSettlementSignal(
                signal_type=FinancialSignalType.PAYMENT_SETTLEMENT,
                timestamp=timestamp,
                message_id=msg_id or tx_id or 'UNKNOWN',
                transaction_id=tx_id or 'UNKNOWN',
                amount=amount,
                settlement_date=sttlm_date,
                settlement_method=sttlm_mtd,
                debtor_agent=FinancialInstitution(bic=instg_bic, institution_id=instg_id),
                creditor_agent=FinancialInstitution(bic=instd_bic, institution_id=instd_id),
                source_system=instg_bic or instg_id or 'pacs.009',
                confidence=1.0,
                raw_data={
                    'message_type': 'pacs.009',
                    'message_id': msg_id,
                    'transaction_id': tx_id,
                    'settlement_date': sttlm_date,
                }
            )
            signals.append(signal)

        return signals

    def _extract_account_transaction_signals(self, root: ET.Element) -> List[AccountTransactionSignal]:
        """Extract account transaction signals from camt.054 (Debit/Credit Notification)."""
        signals = []

        ntfctn_elem = None
        for elem in root.iter():
            if elem.tag.endswith('BkToCstmrDbtCdtNtfctn'):
                ntfctn_elem = elem
                break
        if ntfctn_elem is None:
            return signals

        msg_id = None
        grp_hdr = None
        for elem in ntfctn_elem.iter():
            if elem.tag.endswith('GrpHdr'):
                grp_hdr = elem
                break
        if grp_hdr is not None:
            msg_id = self._find_element_text(grp_hdr, 'MsgId')

        # Per-notification
        for ntfctn in ntfctn_elem.iter():
            if not ntfctn.tag.endswith('Ntfctn'):
                continue

            acct_id = self._find_element_text(ntfctn, 'Id')

            for entry in ntfctn.iter():
                if not entry.tag.endswith('Ntry'):
                    continue

                amt_elem = None
                for e in entry.iter():
                    if e.tag.endswith('Amt'):
                        amt_elem = e
                        break

                amount = None
                if amt_elem is not None:
                    try:
                        amount = Amount(
                            value=float(amt_elem.text) if amt_elem.text else 0.0,
                            currency=amt_elem.get('Ccy', 'USD')
                        )
                    except (ValueError, TypeError):
                        pass

                cd_ind = self._find_element_text(entry, 'CdtDbtInd')
                booking_date = self._find_element_text(entry, 'BookgDt')
                value_date   = self._find_element_text(entry, 'ValDt')
                ref          = self._find_element_text(entry, 'AcctSvcrRef')

                # Pull e2e ID from NtryDtls/TxDtls/Refs if present
                e2e_id = None
                for e in entry.iter():
                    if e.tag.endswith('EndToEndId'):
                        e2e_id = e.text
                        break

                signal = AccountTransactionSignal(
                    signal_type=FinancialSignalType.ACCOUNT_TRANSACTION,
                    timestamp=datetime.now(),
                    message_id=msg_id or 'UNKNOWN',
                    transaction_id=ref or 'UNKNOWN',
                    account_id=acct_id or 'UNKNOWN',
                    amount=amount,
                    transaction_type=cd_ind or 'UNKNOWN',
                    booking_date=booking_date,
                    value_date=value_date,
                    source_system='camt.054',
                    confidence=1.0,
                    raw_data={
                        'message_type': 'camt.054',
                        'reference': ref,
                        'end_to_end_id': e2e_id,
                    }
                )
                signals.append(signal)

        return signals
    
    def _get_text(self, element: ET.Element, xpath: str, namespaces: dict) -> Optional[str]:
        """Safely get text from XML element"""
        elem = element.find(xpath, namespaces)
        return elem.text if elem is not None else None
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse ISO timestamp"""
        try:
            # Handle with/without timezone
            if 'Z' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            elif '+' in timestamp_str or timestamp_str.count('-') > 2:
                return datetime.fromisoformat(timestamp_str)
            else:
                return datetime.fromisoformat(timestamp_str)
        except:
            return datetime.now()