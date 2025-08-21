from __future__ import annotations

import os
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path

from .pdf_parser import PDFParser, PDFChunk
from .text_chunker import TextChunker, IndexedChunk
from .pdf_retriever import PDFRetriever
from .citation_enhancer import CitationEnhancer
from ..tokens import count_tokens


class PDFRAGManager:
    """Manages the complete PDF RAG pipeline."""
    
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.text_chunker = TextChunker()
        self.retriever: Optional[PDFRetriever] = None
        self.citation_enhancer: Optional[CitationEnhancer] = None
        
        self.indexed_chunks: List[IndexedChunk] = []
        self.chunk_index: Dict[str, Any] = {}
        self.is_initialized = False
    
    def initialize_from_pdf(self, pdf_path: str) -> bool:
        """Initialize the RAG system from a PDF file."""
        try:
            print(f"→ PDF RAG: Parsing {pdf_path}")
            
            # 1. Parse PDF into chunks
            pdf_chunks = self.pdf_parser.parse_pdf_with_pages(pdf_path)
            if not pdf_chunks:
                print("→ PDF RAG: No chunks extracted from PDF")
                return False
            
            print(f"→ PDF RAG: Extracted {len(pdf_chunks)} chunks from {pdf_path}")
            
            # 2. Create indexed chunks
            self.indexed_chunks = self.text_chunker.chunk_by_semantic_meaning(pdf_chunks)
            
            # 3. Build search index
            self.chunk_index = self.text_chunker.build_chunk_index(self.indexed_chunks)
            
            # 4. Initialize retriever
            self.retriever = PDFRetriever(self.indexed_chunks, self.chunk_index)
            
            # 5. Initialize citation enhancer
            self.citation_enhancer = CitationEnhancer(self.retriever)
            
            # 6. Generate embeddings if possible
            self._generate_embeddings()
            
            self.is_initialized = True
            print(f"→ PDF RAG: Initialization complete. {len(self.indexed_chunks)} chunks ready for retrieval.")
            
            return True
            
        except Exception as e:
            print(f"→ PDF RAG: Initialization failed: {e}")
            return False
    
    def _generate_embeddings(self):
        """Generate embeddings for all chunks."""
        try:
            # Try to use OpenAI embeddings if available
            from ..llm import _USE_OPENAI, _client
            
            if not _USE_OPENAI or not _client:
                print("→ PDF RAG: OpenAI not available, skipping embeddings")
                return
            
            # Extract text from all chunks
            texts = [chunk.chunk.text_content for chunk in self.indexed_chunks]
            
            # Generate embeddings in batches to avoid token limits
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                print(f"→ PDF RAG: Generating embeddings for batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                
                response = _client.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch_texts
                )
                
                batch_embeddings = [np.array(data.embedding, dtype=np.float32) for data in response.data]
                all_embeddings.extend(batch_embeddings)
            
            # Convert to numpy array and set in retriever
            embeddings_array = np.vstack(all_embeddings)
            self.retriever.set_embeddings(embeddings_array)
            
            print(f"→ PDF RAG: Generated embeddings for {len(all_embeddings)} chunks")
            
        except Exception as e:
            print(f"→ PDF RAG: Failed to generate embeddings: {e}")
    
    def get_citation_enhanced_generator(self, statement_type: str, original_prompt: str):
        """Get a citation-enhanced generator for a specific statement type."""
        if not self.is_initialized or not self.citation_enhancer:
            raise RuntimeError("PDF RAG system not initialized. Call initialize_from_pdf() first.")
        
        return self.citation_enhancer.enhance_generator_with_citations(statement_type, original_prompt)
    
    def search_chunks(self, 
                     query: str, 
                     statement_type: Optional[str] = None, 
                     top_k: int = 5) -> List[IndexedChunk]:
        """Search for relevant chunks."""
        if not self.is_initialized or not self.retriever:
            return []
        
        return self.retriever.retrieve_relevant_chunks(query, statement_type, top_k)
    
    def get_chunks_by_page(self, page_number: int) -> List[IndexedChunk]:
        """Get all chunks from a specific page."""
        if not self.is_initialized:
            return []
        
        return self.chunk_index.get('chunks_by_page', {}).get(page_number, [])
    
    def get_chunks_with_financial_data(self, 
                                     min_amount: float = 1_000_000) -> List[IndexedChunk]:
        """Get chunks containing significant financial figures."""
        if not self.is_initialized or not self.retriever:
            return []
        
        return self.retriever.retrieve_chunks_with_figures(min_amount)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the RAG system."""
        if not self.is_initialized:
            return {"status": "not_initialized"}
        
        stats = {
            "status": "initialized",
            "total_chunks": len(self.indexed_chunks),
            "chunks_by_page": {},
            "chunks_by_type": {},
            "chunks_by_statement": {},
            "financial_terms_count": 0,
            "has_embeddings": False
        }
        
        if self.retriever:
            retriever_stats = self.retriever.get_retrieval_stats()
            stats.update(retriever_stats)
        
        return stats
    
    def preview_chunks(self, max_chunks: int = 5) -> List[Dict[str, Any]]:
        """Get a preview of the parsed chunks for debugging."""
        if not self.is_initialized:
            return []
        
        previews = []
        for i, chunk in enumerate(self.indexed_chunks[:max_chunks]):
            preview = {
                "chunk_id": chunk.chunk.chunk_id,
                "page_number": chunk.chunk.page_number,
                "chunk_type": chunk.chunk.chunk_type,
                "text_preview": chunk.chunk.get_preview_text(150),
                "keywords": chunk.keywords[:5],  # Top 5 keywords
                "financial_terms": chunk.financial_terms[:5]  # Top 5 financial terms
            }
            previews.append(preview)
        
        return previews
    
    def test_retrieval(self, query: str) -> Dict[str, Any]:
        """Test the retrieval system with a query."""
        if not self.is_initialized or not self.retriever:
            return {"error": "System not initialized"}
        
        # Try different retrieval methods
        results = {}
        
        # General retrieval
        general_chunks = self.retriever.retrieve_relevant_chunks(query, top_k=3)
        results["general_retrieval"] = [
            {
                "chunk_id": chunk.chunk.chunk_id,
                "page": chunk.chunk.page_number,
                "type": chunk.chunk.chunk_type,
                "preview": chunk.chunk.get_preview_text(100)
            }
            for chunk in general_chunks
        ]
        
        # Statement-specific retrieval
        for stmt_type in ["balance_sheet", "income_statement", "cash_flows"]:
            stmt_chunks = self.retriever.retrieve_relevant_chunks(
                query, statement_type=stmt_type, top_k=2
            )
            results[f"{stmt_type}_retrieval"] = [
                {
                    "chunk_id": chunk.chunk.chunk_id,
                    "page": chunk.chunk.page_number,
                    "preview": chunk.chunk.get_preview_text(100)
                }
                for chunk in stmt_chunks
            ]
        
        return results
