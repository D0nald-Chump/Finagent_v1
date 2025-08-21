from __future__ import annotations

from typing import List, Dict, Any, Callable, Optional
from .text_chunker import IndexedChunk
from .pdf_retriever import PDFRetriever
from ..state import State, merge
from ..llm import call_llm
from ..config import MODEL_NAME
from ..costing import log_cost


class CitationEnhancer:
    """Enhances generators with PDF citation capabilities."""
    
    def __init__(self, retriever: PDFRetriever):
        self.retriever = retriever
    
    def enhance_generator_with_citations(self, 
                                       statement_type: str,
                                       original_prompt: str) -> Callable:
        """Create a citation-enhanced generator function."""
        
        def _citation_enhanced_generator(state: State) -> State:
            # Extract section data and check for revision mode
            from ..nodes import STATEMENT_CONFIG
            config = STATEMENT_CONFIG.get(statement_type)
            if not config:
                raise ValueError(f"Unknown statement type: {statement_type}")
            
            section_data = dict(state.get(config['state_key'], {}))
            feedback = section_data.get('feedback', [])
            existing_draft = section_data.get('draft', '')
            r = section_data.get("retries", 0)
            
            # Retrieve relevant PDF chunks
            retrieved_chunks = self._retrieve_relevant_chunks(statement_type, state, feedback)
            
            # Build citation-enhanced prompt
            if feedback and existing_draft:
                # Revision mode
                from ..nodes import log
                log(f"→ [Sub] {config['display_name']} (LLM) - Citation-Enhanced Revision Mode (attempt {r + 1})")
                user_prompt = self._build_revision_prompt(
                    statement_type, feedback, existing_draft, retrieved_chunks, state
                )
            else:
                # Initial generation mode
                from ..nodes import log
                log(f"→ [Sub] {config['display_name']} (LLM) - Citation-Enhanced Initial Generation")
                user_prompt = self._build_initial_prompt(
                    statement_type, retrieved_chunks, state
                )
            
            # Get enhanced system prompt
            enhanced_system_prompt = self._get_enhanced_system_prompt(original_prompt, retrieved_chunks)
            
            # Call LLM with enhanced prompt
            text, in_tok, out_tok = call_llm(MODEL_NAME, enhanced_system_prompt, user_prompt)
            log_cost(config['log_name'], "citation_enhanced_worker", in_tok, out_tok, enhanced_system_prompt, text)
            
            # Update section data
            section_data.update({
                "draft": text, 
                "_v": section_data.get("_v", 0) + 1, 
                "retries": r,
                "feedback": [],  # Clear processed feedback
                "retrieved_chunks": [self._chunk_to_dict(chunk) for chunk in retrieved_chunks]
            })
            
            return merge(state, {config['state_key']: section_data})
        
        return _citation_enhanced_generator
    
    def _retrieve_relevant_chunks(self, 
                                statement_type: str, 
                                state: State, 
                                feedback: List[Dict]) -> List[IndexedChunk]:
        """Retrieve relevant chunks for the analysis."""
        # Build query from statement type and feedback
        query_parts = [statement_type.replace('_', ' ')]
        
        # Add feedback-specific queries
        if feedback:
            for fb in feedback:
                if isinstance(fb, dict):
                    issue = fb.get('issue', '')
                    suggestion = fb.get('suggestion', '')
                    if issue:
                        query_parts.append(issue)
                    if suggestion:
                        query_parts.append(suggestion)
        
        query = ' '.join(query_parts)
        
        # Retrieve chunks using multiple strategies
        chunks = []
        
        # 1. Statement-specific retrieval
        stmt_chunks = self.retriever.retrieve_relevant_chunks(
            query, statement_type=statement_type, top_k=3
        )
        chunks.extend(stmt_chunks)
        
        # 2. Financial concept retrieval
        financial_concepts = self._extract_financial_concepts(statement_type)
        for concept in financial_concepts:
            concept_chunks = self.retriever.retrieve_by_financial_concept(
                concept, statement_type=statement_type, top_k=1
            )
            chunks.extend(concept_chunks)
        
        # 3. Chunks with significant figures
        figure_chunks = self.retriever.retrieve_chunks_with_figures(
            min_amount=1_000_000, statement_type=statement_type
        )
        chunks.extend(figure_chunks[:2])  # Limit to 2 most relevant
        
        # Remove duplicates while preserving order
        seen_chunk_ids = set()
        unique_chunks = []
        for chunk in chunks:
            if chunk.chunk.chunk_id not in seen_chunk_ids:
                unique_chunks.append(chunk)
                seen_chunk_ids.add(chunk.chunk.chunk_id)
        
        return unique_chunks[:5]  # Limit total chunks to avoid prompt bloat
    
    def _extract_financial_concepts(self, statement_type: str) -> List[str]:
        """Extract key financial concepts for each statement type."""
        concepts = {
            'balance_sheet': ['total assets', 'total liabilities', 'stockholders equity', 'cash', 'debt'],
            'income_statement': ['revenue', 'net income', 'operating income', 'gross profit', 'earnings per share'],
            'cash_flows': ['operating cash flow', 'free cash flow', 'capital expenditures', 'net income']
        }
        return concepts.get(statement_type, [])
    
    def _build_initial_prompt(self, 
                            statement_type: str, 
                            chunks: List[IndexedChunk], 
                            state: State) -> str:
        """Build the initial generation prompt with citations."""
        pdf_text_sample = state.get('ctx', {}).get('pdf_text', '<none>')
        
        # Format retrieved chunks for the prompt
        formatted_chunks = self._format_chunks_for_prompt(chunks)
        
        prompt = f"""Analyze the {statement_type.replace('_', ' ')} based on the provided financial document.

CITATION REQUIREMENTS:
1. When referencing specific data, MUST include citation: 【Page X: "exact quote"】
2. Use provided PDF chunks below for accurate citations
3. If calculating derived metrics, explain the calculation process
4. Maintain professional analysis quality

RETRIEVED PDF CONTENT:
{formatted_chunks}

FULL DOCUMENT CONTEXT (for additional reference):
{pdf_text_sample[:1000]}...

Please provide a comprehensive analysis with proper citations for all specific data points."""
        
        return prompt
    
    def _build_revision_prompt(self, 
                             statement_type: str, 
                             feedback: List[Dict], 
                             existing_draft: str, 
                             chunks: List[IndexedChunk], 
                             state: State) -> str:
        """Build the revision prompt with citations."""
        feedback_text = "\n".join([
            f"- {item.get('issue', '')}: {item.get('suggestion', '')}" 
            for item in feedback if isinstance(item, dict)
        ]) if feedback else "General improvements needed"
        
        formatted_chunks = self._format_chunks_for_prompt(chunks)
        
        prompt = f"""Revise the {statement_type.replace('_', ' ')} analysis based on feedback.

FEEDBACK TO ADDRESS:
{feedback_text}

CITATION REQUIREMENTS:
1. Add proper citations: 【Page X: "exact quote"】
2. Use provided PDF chunks for accurate references
3. Address all feedback points with supporting evidence

RETRIEVED PDF CONTENT:
{formatted_chunks}

CURRENT DRAFT TO REVISE:
{existing_draft}

Please revise the analysis addressing all feedback points with proper citations."""
        
        return prompt
    
    def _get_enhanced_system_prompt(self, original_prompt: str, chunks: List[IndexedChunk]) -> str:
        """Create an enhanced system prompt with citation instructions."""
        citation_instructions = """
CITATION GUIDELINES:
- When referencing specific figures, data, or quotes from the financial document, MUST include citations
- Citation format: 【Page X: "exact quoted text"】
- Example: The company reported revenue of $22.5 billion 【Page 3: "Total revenue was $22,496 million"】
- For calculated metrics, explain the source data and calculation
- If information is inferred or estimated, mark it clearly as (estimated) or (calculated from X and Y)
"""
        
        return original_prompt + citation_instructions
    
    def _format_chunks_for_prompt(self, chunks: List[IndexedChunk]) -> str:
        """Format chunks for inclusion in the prompt."""
        if not chunks:
            return "No specific PDF chunks retrieved."
        
        formatted = []
        for i, chunk in enumerate(chunks, 1):
            formatted.append(f"""--- Chunk {i} ---
Page: {chunk.chunk.page_number}
Type: {chunk.chunk.chunk_type}
Content: {chunk.chunk.text_content.strip()}""")
        
        return "\n\n".join(formatted)
    
    def format_citation(self, chunk: IndexedChunk, quoted_text: str) -> str:
        """Format a citation for a specific chunk and quote."""
        page_ref = chunk.chunk.get_citation_reference()
        preview = quoted_text[:100] + "..." if len(quoted_text) > 100 else quoted_text
        return f"【{page_ref}: \"{preview}\"】"
    
    def extract_relevant_quotes(self, 
                              chunks: List[IndexedChunk], 
                              analysis_context: str) -> List[str]:
        """Extract the most relevant quotes from chunks for a given context."""
        quotes = []
        context_lower = analysis_context.lower()
        
        for chunk in chunks:
            text = chunk.chunk.text_content
            
            # Split into sentences
            sentences = text.split('.')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 20:  # Skip very short sentences
                    continue
                
                # Check if sentence is relevant to the context
                if any(word in sentence.lower() for word in context_lower.split()):
                    citation = self.format_citation(chunk, sentence)
                    quotes.append(citation)
        
        return quotes[:3]  # Return top 3 most relevant quotes
    
    def _chunk_to_dict(self, chunk: IndexedChunk) -> Dict[str, Any]:
        """Convert an IndexedChunk to a dictionary for state storage."""
        return {
            "chunk_id": chunk.chunk.chunk_id,
            "page_number": chunk.chunk.page_number,
            "text_content": chunk.chunk.text_content,
            "chunk_type": chunk.chunk.chunk_type,
            "keywords": chunk.keywords,
            "financial_terms": chunk.financial_terms
        }
