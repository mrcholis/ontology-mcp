"""
Financial Signal Extraction Pipeline

Same architecture as agricultural signal extraction, but for banking/finance domain.
"""

from typing import List, Any
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.signals.iso20022_extractor import ISO20022Extractor
from src.signals.financial_signals import FinancialSignal


class FinancialSignalExtractionPipeline:
    """
    Pipeline for extracting financial signals from ISO 20022 messages.
    
    Same architecture as EnhancedSignalExtractionPipeline, but for finance domain.
    """
    
    def __init__(self):
        """Initialize with ISO 20022 extractor"""
        self.extractors = [
            ISO20022Extractor()
        ]
    
    def register_extractor(self, extractor):
        """Register additional extractor"""
        self.extractors.insert(0, extractor)
    
    def extract(self, raw_data: Any) -> List[FinancialSignal]:
        """
        Extract financial signals from raw data.
        
        Args:
            raw_data: ISO 20022 XML string or JSON
            
        Returns:
            List of extracted financial signals
        """
        for extractor in self.extractors:
            if extractor.can_handle(raw_data):
                return extractor.extract_signals(raw_data)
        
        return []