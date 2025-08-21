from __future__ import annotations

import re
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .pdf_parser import PDFChunk


@dataclass
class IndexedChunk:
    """A PDF chunk with additional indexing information."""
    chunk: PDFChunk
    embedding: Optional[np.ndarray] = None
    keywords: List[str] = None
    financial_terms: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.financial_terms is None:
            self.financial_terms = []


class TextChunker:
    """Handles text chunking and indexing for financial documents."""
    
    def __init__(self):
        self.financial_terms = {
            # Balance Sheet terms
            'assets', 'current assets', 'non-current assets', 'total assets',
            'liabilities', 'current liabilities', 'long-term liabilities', 'total liabilities',
            'equity', 'stockholders equity', 'retained earnings', 'common stock',
            'cash', 'cash equivalents', 'accounts receivable', 'inventory',
            'property plant equipment', 'accounts payable', 'debt', 'long-term debt',
            
            # Income Statement terms
            'revenue', 'net revenue', 'total revenue', 'sales', 'net sales',
            'cost of revenue', 'cost of goods sold', 'gross profit', 'gross margin',
            'operating expenses', 'operating income', 'operating margin',
            'net income', 'earnings', 'earnings per share', 'eps',
            'research and development', 'sales and marketing', 'general and administrative',
            
            # Cash Flow terms
            'cash flow', 'operating cash flow', 'investing cash flow', 'financing cash flow',
            'free cash flow', 'capital expenditures', 'capex', 'depreciation',
            'amortization', 'working capital', 'stock-based compensation',
            
            # Financial ratios and metrics
            'current ratio', 'quick ratio', 'debt to equity', 'return on equity', 'roe',
            'return on assets', 'roa', 'gross margin', 'operating margin', 'net margin',
            'debt ratio', 'interest coverage', 'days sales outstanding', 'dso',
            
            # General financial terms
            'million', 'billion', 'thousand', 'fiscal year', 'quarter', 'quarterly',
            'year-over-year', 'yoy', 'quarter-over-quarter', 'qoq',
            'gaap', 'non-gaap', 'adjusted', 'normalized'
        }
        
        self.statement_type_keywords = {
            'balance_sheet': {
                'balance sheet', 'statement of financial position', 'assets', 'liabilities', 
                'equity', 'current assets', 'working capital', 'cash', 'inventory'
            },
            'income_statement': {
                'income statement', 'statement of operations', 'profit and loss', 'p&l',
                'revenue', 'sales', 'cost of revenue', 'gross profit', 'operating income',
                'net income', 'earnings', 'eps'
            },
            'cash_flows': {
                'cash flow', 'statement of cash flows', 'operating activities',
                'investing activities', 'financing activities', 'free cash flow',
                'capital expenditures', 'depreciation'
            }
        }
    
    def chunk_by_semantic_meaning(self, chunks: List[PDFChunk]) -> List[IndexedChunk]:
        """Convert PDF chunks to indexed chunks with semantic information."""
        indexed_chunks = []
        
        for chunk in chunks:
            # Extract keywords and financial terms
            keywords = self.extract_keywords(chunk.text_content)
            financial_terms = self.extract_financial_keywords(chunk.text_content)
            
            indexed_chunk = IndexedChunk(
                chunk=chunk,
                keywords=keywords,
                financial_terms=financial_terms
            )
            indexed_chunks.append(indexed_chunk)
        
        return indexed_chunks
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract general keywords from text."""
        # Simple keyword extraction - could be enhanced with NLP libraries
        text_lower = text.lower()
        
        # Remove common stopwords and extract meaningful words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text_lower)
        
        # Filter out very common words
        stopwords = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how',
            'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy',
            'did', 'she', 'use', 'her', 'many', 'oil', 'sit', 'set'
        }
        
        keywords = [word for word in set(words) if word not in stopwords and len(word) > 3]
        return keywords[:10]  # Limit to top 10 keywords
    
    def extract_financial_keywords(self, text: str) -> List[str]:
        """Extract financial terms from text."""
        text_lower = text.lower()
        found_terms = []
        
        for term in self.financial_terms:
            if term in text_lower:
                found_terms.append(term)
        
        return found_terms
    
    def classify_statement_type(self, chunk: IndexedChunk) -> Optional[str]:
        """Classify which financial statement type this chunk likely belongs to."""
        text_lower = chunk.chunk.text_content.lower()
        
        scores = {}
        for stmt_type, keywords in self.statement_type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                scores[stmt_type] = score
        
        if scores:
            return max(scores, key=scores.get)
        return None
    
    def extract_financial_figures(self, text: str) -> List[Dict[str, Any]]:
        """Extract financial figures with their context."""
        figures = []
        
        # Pattern for dollar amounts
        dollar_pattern = r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(million|billion|thousand|m|b|k)?'
        
        for match in re.finditer(dollar_pattern, text, re.IGNORECASE):
            amount_str = match.group(1).replace(',', '')
            unit = match.group(2)
            
            # Convert to standard format
            amount = float(amount_str)
            if unit and unit.lower() in ['million', 'm']:
                amount *= 1_000_000
            elif unit and unit.lower() in ['billion', 'b']:
                amount *= 1_000_000_000
            elif unit and unit.lower() in ['thousand', 'k']:
                amount *= 1_000
            
            # Get context around the figure
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            
            figures.append({
                'amount': amount,
                'formatted_amount': match.group(0),
                'context': context,
                'position': match.start()
            })
        
        return figures
    
    def build_chunk_index(self, chunks: List[IndexedChunk]) -> Dict[str, Any]:
        """Build an index for fast chunk retrieval."""
        index = {
            'chunks_by_page': {},
            'chunks_by_type': {},
            'chunks_by_statement': {},
            'financial_terms_index': {},
            'keyword_index': {}
        }
        
        for chunk in chunks:
            # Index by page
            page_num = chunk.chunk.page_number
            if page_num not in index['chunks_by_page']:
                index['chunks_by_page'][page_num] = []
            index['chunks_by_page'][page_num].append(chunk)
            
            # Index by chunk type
            chunk_type = chunk.chunk.chunk_type
            if chunk_type not in index['chunks_by_type']:
                index['chunks_by_type'][chunk_type] = []
            index['chunks_by_type'][chunk_type].append(chunk)
            
            # Index by statement type
            stmt_type = self.classify_statement_type(chunk)
            if stmt_type:
                if stmt_type not in index['chunks_by_statement']:
                    index['chunks_by_statement'][stmt_type] = []
                index['chunks_by_statement'][stmt_type].append(chunk)
            
            # Index by financial terms
            for term in chunk.financial_terms:
                if term not in index['financial_terms_index']:
                    index['financial_terms_index'][term] = []
                index['financial_terms_index'][term].append(chunk)
            
            # Index by keywords
            for keyword in chunk.keywords:
                if keyword not in index['keyword_index']:
                    index['keyword_index'][keyword] = []
                index['keyword_index'][keyword].append(chunk)
        
        return index
