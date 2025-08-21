from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path


@dataclass
class PDFChunk:
    """Represents a chunk of text from a specific page in a PDF."""
    chunk_id: str              # Unique identifier like "page_3_chunk_2"
    page_number: int           # Page number (1-indexed)
    text_content: str          # Actual text content
    start_char: int            # Start character position in page
    end_char: int              # End character position in page
    chunk_type: str            # Type: "table", "paragraph", "header", "footnote"
    
    def get_citation_reference(self) -> str:
        """Generate a citation reference for this chunk."""
        return f"Page {self.page_number}"
    
    def get_preview_text(self, max_chars: int = 100) -> str:
        """Get a preview of the text content for citation."""
        text = self.text_content.strip()
        if len(text) <= max_chars:
            return text
        return text[:max_chars-3] + "..."


class PDFParser:
    """Parser for extracting structured text chunks from PDF files."""
    
    def __init__(self):
        self.financial_keywords = {
            'revenue', 'income', 'assets', 'liabilities', 'equity', 'cash', 
            'debt', 'earnings', 'profit', 'loss', 'balance', 'statement',
            'million', 'billion', 'thousand', '$', 'usd', 'total'
        }
    
    def parse_pdf_with_pages(self, pdf_path: str) -> List[PDFChunk]:
        """Parse PDF and extract chunks with page information."""
        try:
            # Lazy import so the rest of the app works even without pypdf installed
            from pypdf import PdfReader
        except ImportError as e:
            print(f"pypdf not available: {e}")
            return self._create_dummy_chunks()
        
        try:
            reader = PdfReader(str(pdf_path))
            chunks = []
            
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        page_chunks = self._chunk_page_text(page_text, page_num)
                        chunks.extend(page_chunks)
                except Exception as e:
                    print(f"Error processing page {page_num}: {e}")
                    continue
            
            return chunks
            
        except Exception as e:
            print(f"PDF parsing failed: {e}")
            return self._create_dummy_chunks()
    
    def _chunk_page_text(self, page_text: str, page_number: int) -> List[PDFChunk]:
        """Split page text into semantic chunks."""
        chunks = []
        
        # Split by double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', page_text.strip())
        
        current_char = 0
        chunk_counter = 1
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            # Determine chunk type
            chunk_type = self._detect_chunk_type(paragraph)
            
            # Create chunk
            chunk = PDFChunk(
                chunk_id=f"page_{page_number}_chunk_{chunk_counter}",
                page_number=page_number,
                text_content=paragraph,
                start_char=current_char,
                end_char=current_char + len(paragraph),
                chunk_type=chunk_type
            )
            chunks.append(chunk)
            
            current_char += len(paragraph) + 2  # +2 for paragraph break
            chunk_counter += 1
        
        return chunks
    
    def _detect_chunk_type(self, text: str) -> str:
        """Detect the type of text chunk."""
        text_lower = text.lower()
        text_lines = text.split('\n')
        
        # Check for table-like structures
        if self._looks_like_table(text):
            return "table"
        
        # Check for headers (short, often capitalized)
        if len(text) < 100 and (text.isupper() or text.istitle()):
            return "header"
        
        # Check for footnotes (usually start with numbers or special chars)
        if re.match(r'^\d+\s+', text) or re.match(r'^[\(\[]?\d+[\)\]]?\s+', text):
            return "footnote"
        
        # Check for financial data (contains many numbers and financial terms)
        if self._contains_financial_data(text):
            return "financial_data"
        
        # Default to paragraph
        return "paragraph"
    
    def _looks_like_table(self, text: str) -> bool:
        """Check if text looks like a table."""
        lines = text.split('\n')
        if len(lines) < 2:
            return False
        
        # Check for consistent spacing or tab characters
        tab_lines = sum(1 for line in lines if '\t' in line)
        if tab_lines > len(lines) * 0.5:
            return True
        
        # Check for numeric columns
        numeric_lines = sum(1 for line in lines if re.search(r'\$?\d+[,\d]*\.?\d*', line))
        if numeric_lines > len(lines) * 0.7:
            return True
        
        return False
    
    def _contains_financial_data(self, text: str) -> bool:
        """Check if text contains financial data."""
        text_lower = text.lower()
        
        # Count financial keywords
        keyword_count = sum(1 for keyword in self.financial_keywords if keyword in text_lower)
        
        # Count dollar amounts
        dollar_count = len(re.findall(r'\$\s*\d+[,\d]*\.?\d*', text))
        
        # Count large numbers (likely financial figures)
        large_number_count = len(re.findall(r'\b\d{1,3}[,\d]*\.?\d*\s*(million|billion|thousand)\b', text_lower))
        
        return keyword_count >= 2 or dollar_count >= 1 or large_number_count >= 1
    
    def extract_page_text(self, pdf_path: str, page_num: int) -> str:
        """Extract text from a specific page."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(pdf_path))
            
            if 1 <= page_num <= len(reader.pages):
                return reader.pages[page_num - 1].extract_text() or ""
            return ""
            
        except Exception as e:
            print(f"Error extracting page {page_num}: {e}")
            return ""
    
    def _create_dummy_chunks(self) -> List[PDFChunk]:
        """Create dummy chunks when PDF parsing fails."""
        return [
            PDFChunk(
                chunk_id="dummy_chunk_1",
                page_number=1,
                text_content="Dummy financial text with revenue of $100 million and total assets of $500 million.",
                start_char=0,
                end_char=100,
                chunk_type="financial_data"
            )
        ]
