from __future__ import annotations

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from .text_chunker import IndexedChunk, TextChunker
from ..tokens import count_tokens


class PDFRetriever:
    """Retriever for finding relevant PDF chunks based on queries."""
    
    def __init__(self, indexed_chunks: List[IndexedChunk], index: Dict[str, Any]):
        self.indexed_chunks = indexed_chunks
        self.index = index
        self.chunk_embeddings: Optional[np.ndarray] = None
        
        # Statement type preferences for page ranges
        self.statement_page_preferences = {
            'balance_sheet': (1, 5),      # Usually in first few pages
            'income_statement': (1, 8),   # Often early in document
            'cash_flows': (3, 10)         # Usually after balance sheet and income statement
        }
    
    def set_embeddings(self, embeddings: np.ndarray):
        """Set the embeddings for all chunks."""
        if len(embeddings) != len(self.indexed_chunks):
            raise ValueError(f"Embeddings length {len(embeddings)} doesn't match chunks length {len(self.indexed_chunks)}")
        
        self.chunk_embeddings = embeddings
        
        # Store embeddings in chunks
        for i, chunk in enumerate(self.indexed_chunks):
            chunk.embedding = embeddings[i]
    
    def retrieve_relevant_chunks(self, 
                               query: str, 
                               statement_type: Optional[str] = None,
                               top_k: int = 3) -> List[IndexedChunk]:
        """Retrieve the most relevant chunks for a query."""
        candidates = self.indexed_chunks
        
        # First, filter by statement type if specified
        if statement_type and statement_type in self.index['chunks_by_statement']:
            candidates = self.index['chunks_by_statement'][statement_type]
            
            # If no statement-specific chunks found, fall back to page preference
            if not candidates:
                page_start, page_end = self.statement_page_preferences.get(statement_type, (1, 10))
                candidates = self._get_chunks_in_page_range(page_start, page_end)
        
        # If we have embeddings, use semantic similarity
        if self.chunk_embeddings is not None and candidates:
            return self._retrieve_by_similarity(query, candidates, top_k)
        
        # Fallback to keyword-based retrieval
        return self._retrieve_by_keywords(query, candidates, top_k)
    
    def retrieve_by_financial_concept(self, 
                                    concept: str,
                                    statement_type: Optional[str] = None,
                                    top_k: int = 2) -> List[IndexedChunk]:
        """Retrieve chunks related to a specific financial concept."""
        # Check if concept exists in financial terms index
        if concept.lower() in self.index['financial_terms_index']:
            candidates = self.index['financial_terms_index'][concept.lower()]
        else:
            # Fallback to keyword search
            candidates = []
            for chunk in self.indexed_chunks:
                if concept.lower() in chunk.chunk.text_content.lower():
                    candidates.append(chunk)
        
        # Filter by statement type if specified
        if statement_type:
            candidates = [c for c in candidates if self._chunk_matches_statement_type(c, statement_type)]
        
        # Sort by relevance (chunks with more financial terms are more relevant)
        candidates.sort(key=lambda c: len(c.financial_terms), reverse=True)
        
        return candidates[:top_k]
    
    def retrieve_by_page_preference(self, 
                                  query: str,
                                  preferred_pages: List[int],
                                  top_k: int = 3) -> List[IndexedChunk]:
        """Retrieve chunks from preferred pages."""
        candidates = []
        for page_num in preferred_pages:
            if page_num in self.index['chunks_by_page']:
                candidates.extend(self.index['chunks_by_page'][page_num])
        
        if not candidates:
            return []
        
        # Use similarity if available, otherwise keywords
        if self.chunk_embeddings is not None:
            return self._retrieve_by_similarity(query, candidates, top_k)
        else:
            return self._retrieve_by_keywords(query, candidates, top_k)
    
    def retrieve_chunks_with_figures(self, 
                                   min_amount: float = 1_000_000,  # 1 million default
                                   statement_type: Optional[str] = None) -> List[IndexedChunk]:
        """Retrieve chunks that contain financial figures above a threshold."""
        text_chunker = TextChunker()
        relevant_chunks = []
        
        for chunk in self.indexed_chunks:
            # Check if chunk matches statement type
            if statement_type and not self._chunk_matches_statement_type(chunk, statement_type):
                continue
            
            # Extract figures from the chunk
            figures = text_chunker.extract_financial_figures(chunk.chunk.text_content)
            
            # Check if any figure is above the threshold
            if any(fig['amount'] >= min_amount for fig in figures):
                relevant_chunks.append(chunk)
        
        return relevant_chunks
    
    def _retrieve_by_similarity(self, 
                              query: str, 
                              candidates: List[IndexedChunk], 
                              top_k: int) -> List[IndexedChunk]:
        """Retrieve using embedding similarity."""
        if not candidates or self.chunk_embeddings is None:
            return []
        
        # Get query embedding (this would need to be implemented in the calling code)
        # For now, we'll use a placeholder approach
        query_terms = query.lower().split()
        
        # Score candidates based on term overlap (simplified similarity)
        scored_candidates = []
        for chunk in candidates:
            score = self._calculate_term_overlap_score(query_terms, chunk)
            scored_candidates.append((score, chunk))
        
        # Sort by score and return top_k
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_candidates[:top_k]]
    
    def _retrieve_by_keywords(self, 
                            query: str, 
                            candidates: List[IndexedChunk], 
                            top_k: int) -> List[IndexedChunk]:
        """Retrieve using keyword matching."""
        query_terms = set(query.lower().split())
        scored_candidates = []
        
        for chunk in candidates:
            score = self._calculate_keyword_score(query_terms, chunk)
            if score > 0:  # Only include chunks with some relevance
                scored_candidates.append((score, chunk))
        
        # Sort by score and return top_k
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored_candidates[:top_k]]
    
    def _calculate_term_overlap_score(self, query_terms: List[str], chunk: IndexedChunk) -> float:
        """Calculate similarity score based on term overlap."""
        chunk_text = chunk.chunk.text_content.lower()
        chunk_terms = set(chunk_text.split())
        
        # Basic term overlap
        overlap = len(set(query_terms) & chunk_terms)
        base_score = overlap / len(query_terms) if query_terms else 0
        
        # Boost for financial terms
        financial_boost = len(chunk.financial_terms) * 0.1
        
        # Boost for chunk type relevance
        type_boost = 0.2 if chunk.chunk.chunk_type in ['financial_data', 'table'] else 0
        
        return base_score + financial_boost + type_boost
    
    def _calculate_keyword_score(self, query_terms: set, chunk: IndexedChunk) -> float:
        """Calculate keyword-based relevance score."""
        chunk_text = chunk.chunk.text_content.lower()
        chunk_keywords = set(chunk.keywords)
        chunk_financial_terms = set(chunk.financial_terms)
        
        # Score based on different types of matches
        direct_matches = sum(1 for term in query_terms if term in chunk_text)
        keyword_matches = len(query_terms & chunk_keywords)
        financial_matches = len(query_terms & chunk_financial_terms)
        
        # Weight different types of matches
        score = (direct_matches * 1.0 + 
                keyword_matches * 1.5 + 
                financial_matches * 2.0)
        
        # Normalize by chunk length (prefer shorter, more focused chunks)
        text_length = len(chunk.chunk.text_content)
        if text_length > 0:
            score = score / (text_length / 1000)  # Normalize per 1000 characters
        
        return score
    
    def _chunk_matches_statement_type(self, chunk: IndexedChunk, statement_type: str) -> bool:
        """Check if a chunk is relevant to a specific statement type."""
        text_chunker = TextChunker()
        classified_type = text_chunker.classify_statement_type(chunk)
        
        if classified_type == statement_type:
            return True
        
        # Also check page preferences
        page_start, page_end = self.statement_page_preferences.get(statement_type, (1, 100))
        return page_start <= chunk.chunk.page_number <= page_end
    
    def _get_chunks_in_page_range(self, start_page: int, end_page: int) -> List[IndexedChunk]:
        """Get all chunks within a page range."""
        chunks = []
        for page_num in range(start_page, end_page + 1):
            if page_num in self.index['chunks_by_page']:
                chunks.extend(self.index['chunks_by_page'][page_num])
        return chunks
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get statistics about the retrieval system."""
        return {
            'total_chunks': len(self.indexed_chunks),
            'chunks_by_page': {k: len(v) for k, v in self.index['chunks_by_page'].items()},
            'chunks_by_type': {k: len(v) for k, v in self.index['chunks_by_type'].items()},
            'chunks_by_statement': {k: len(v) for k, v in self.index['chunks_by_statement'].items()},
            'financial_terms_count': len(self.index['financial_terms_index']),
            'has_embeddings': self.chunk_embeddings is not None
        }
