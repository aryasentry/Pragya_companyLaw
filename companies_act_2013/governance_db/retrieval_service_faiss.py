"""
FAISS-based Retrieval Service with PostgreSQL Integration
Combines vector search with full database metadata
"""
import os
import json
import faiss
import numpy as np
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from db_config import get_db_connection

# Configuration
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', 'qwen3-embedding:0.6b')
LLM_MODEL = os.getenv('OLLAMA_LLM_MODEL', 'qwen2.5:1.5b')
VECTOR_DB_PATH = Path(__file__).parent / "vector_store"
INDEX_FILE = VECTOR_DB_PATH / "faiss_index.bin"
METADATA_FILE = VECTOR_DB_PATH / "metadata.json"


class GovernanceRetriever:
    """FAISS + PostgreSQL retrieval system"""
    
    def __init__(self):
        self.index = None
        self.metadata = []
        self.chunk_id_to_idx = {}
        
        # Load FAISS index
        if INDEX_FILE.exists() and METADATA_FILE.exists():
            self.index = faiss.read_index(str(INDEX_FILE))
            
            with open(METADATA_FILE, 'r') as f:
                self.metadata = json.load(f)
            
            for idx, meta in enumerate(self.metadata):
                self.chunk_id_to_idx[meta['chunk_id']] = idx
            
            print(f"Loaded FAISS index: {len(self.metadata)} vectors")
        else:
            raise FileNotFoundError(f"FAISS index not found at {INDEX_FILE}")
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding using Ollama"""
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={'model': EMBEDDING_MODEL, 'prompt': text},
                timeout=10  # Reduced from 30s - embeddings are fast with local Ollama
            )
            
            if response.status_code == 200:
                embedding = response.json()['embedding']
                return np.array(embedding, dtype=np.float32)
            else:
                print(f"Embedding error: {response.status_code}")
                return None
        
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def search_vectors(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search FAISS index"""
        query_embedding = self.generate_embedding(query)
        if query_embedding is None:
            return []
        
        # Normalize query
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        
        # Search
        scores, indices = self.index.search(query_embedding.reshape(1, -1), top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.metadata):
                # Filter by 50% similarity threshold
                if float(score) >= 0.5:
                    result = self.metadata[idx].copy()
                    result['similarity_score'] = float(score)
                    results.append(result)
        
        return results
    
    def get_chunk_details(self, chunk_ids: List[str]) -> List[Dict]:
        """Fetch full chunk details from PostgreSQL"""
        if not chunk_ids:
            return []
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            query = """
                SELECT 
                    ci.chunk_id,
                    ci.parent_chunk_id,
                    ci.section,
                    ci.document_type,
                    ci.chunk_role,
                    ci.authority_level,
                    ci.binding,
                    cc.text,
                    cc.title,
                    cc.compliance_area,
                    cc.citation,
                    ct.date_issued,
                    ct.effective_from,
                    ct.effective_to,
                    ca.issued_by,
                    ca.notification_number,
                    crr.priority,
                    ce.model AS embedding_model,
                    ce.embedded_at
                FROM chunks_identity ci
                JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                LEFT JOIN chunk_temporal ct ON ci.chunk_id = ct.chunk_id
                LEFT JOIN chunk_administrative ca ON ci.chunk_id = ca.chunk_id
                LEFT JOIN chunk_retrieval_rules crr ON ci.chunk_id = crr.chunk_id
                LEFT JOIN chunk_embeddings ce ON ci.chunk_id = ce.chunk_id
                WHERE ci.chunk_id = ANY(%s)
                ORDER BY crr.priority, ci.section
            """
            
            cur.execute(query, (chunk_ids,))
            results = cur.fetchall()
            cur.close()
        
        return results
    
    def get_chunk_relationships(self, chunk_id: str) -> List[Dict]:
        """Get related chunks"""
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            query = """
                SELECT 
                    relationship_type,
                    target_chunk_id,
                    confidence_score,
                    metadata
                FROM chunk_relationships
                WHERE source_chunk_id = %s
                ORDER BY confidence_score DESC
            """
            
            cur.execute(query, (chunk_id,))
            results = cur.fetchall()
            cur.close()
        
        return results
    
    def generate_answer(self, query: str, context_chunks: List[Dict]) -> Dict:
        """Generate LLM answer from retrieved chunks"""
        if not context_chunks:
            return {
                'answer': 'No relevant information found in the database.',
                'citations': []
            }
        
        # Build context with citations
        context_parts = []
        citations = []
        
        for chunk in context_chunks:
            doc_type = chunk['document_type'].upper()
            section = chunk['section']
            title = chunk.get('title', '')
            text = chunk['text']
            
            citation = f"Section {section}"
            context_parts.append(f"[{doc_type}] {citation}: {title}\n{text}")
            citations.append(citation)
        
        # Reduced context size for faster generation (8000 -> 6000 chars)
        context = "\n\n---\n\n".join(context_parts)[:6000]
        
        # Simplified prompt for faster, clearer answers
        prompt = f"""You are a legal assistant answering strictly from the provided source documents 
related to the Companies Act, 2013 (India).

Rules:
- Use ONLY the provided sources.
- Do NOT add outside knowledge.
- Always cite the exact Section number.
- If answer is not in the sources, say:
  "The provided sources do not contain information about this topic."

User Question:
{query}

Source Documents:
{context}

Answer Format:

## Answer

Provide a clear explanation based ONLY on the sources.
Explain in simple, structured language.
You may summarize but do not invent.

## Legal References
- Section X: short supporting reference from source
"""
        
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    'model': LLM_MODEL,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.3,  # Reduced from 0.5 for faster, more deterministic answers
                        'top_p': 0.9,
                        'num_predict': 768,  # Balanced: more than 512, less than 1024
                        'num_ctx': 4096  # Context window size
                    }
                },
                timeout=45  # Balanced: faster than 60s, safer than 30s
            )
            
            if response.status_code == 200:
                answer_text = response.json().get('response', '')
                
                if not answer_text:
                    return {
                        'answer': 'Unable to generate answer from the retrieved context.',
                        'citations': list(set([f"Section {chunk['section']}" for chunk in context_chunks])),
                        'error': 'Empty LLM response'
                    }
                
                # Extract citations
                citations = list(set([f"Section {chunk['section']}" for chunk in context_chunks]))
                
                return {
                    'answer': answer_text.strip(),
                    'citations': citations,
                    'model': LLM_MODEL
                }
            else:
                error_msg = f'LLM returned {response.status_code}'
                try:
                    error_detail = response.json()
                    error_msg += f': {error_detail}'
                except:
                    pass
                return {
                    'answer': 'Error generating answer. Please try again.',
                    'citations': [],
                    'error': error_msg
                }
        
        except requests.exceptions.Timeout:
            return {
                'answer': 'Answer generation timed out. Please try a simpler query.',
                'citations': [],
                'error': 'LLM timeout after 45 seconds'
            }
        except Exception as e:
            return {
                'answer': 'Error generating answer. Please check if Ollama is running.',
                'citations': [],
                'error': f'{type(e).__name__}: {str(e)}'
            }
    
    def query(self, user_query: str, top_k: int = 15, include_relationships: bool = False) -> Dict:
        """
        Complete retrieval pipeline with hybrid search
        
        Args:
            user_query: User's question
            top_k: Number of chunks to retrieve
            include_relationships: Whether to fetch related chunks
        
        Returns:
            Dictionary with answer, citations, and source chunks
        """
        import logging
        import re
        logger = logging.getLogger(__name__)
        
        logger.info(f"Query: {user_query}")
        
        # Check if query is asking for a definition
        is_definition_query = any(keyword in user_query.lower() for keyword in [
            'definition', 'define', 'meaning', 'means', 'what is', 'what does'
        ])
        
        # Check if query is asking about a specific section number
        section_match = re.search(r'section\s+(\d+)', user_query.lower())
        
        # Special handling for definition queries
        if is_definition_query and not section_match:
            logger.info("Detected definition query - prioritizing Section 2")
            
            # Extract the term being defined
            term_patterns = [
                r'definition\s+of\s+(["\']?)(\w+(?:\s+\w+)*)\1',
                r'define\s+(["\']?)(\w+(?:\s+\w+)*)\1',
                r'what\s+is\s+(?:a\s+|an\s+)?(["\']?)(\w+(?:\s+\w+)*)\1',
                r'meaning\s+of\s+(["\']?)(\w+(?:\s+\w+)*)\1'
            ]
            
            term = None
            for pattern in term_patterns:
                match = re.search(pattern, user_query.lower())
                if match:
                    term = match.group(2) if match.lastindex >= 2 else match.group(1)
                    break
            
            if term:
                logger.info(f"Searching for definition of: {term}")
                
                # Search in Section 2 (definitions) first
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT ci.chunk_id
                        FROM chunks_identity ci
                        JOIN chunks_content cc ON ci.chunk_id = cc.chunk_id
                        WHERE ci.section = '002'
                        AND ci.document_type = 'act'
                        AND LOWER(cc.text) LIKE %s
                        ORDER BY 
                            CASE WHEN ci.chunk_role = 'parent' THEN 0 ELSE 1 END,
                            ci.chunk_id
                        LIMIT 5
                    """, (f'%{term.lower()}%',))
                    
                    definition_chunks = [row['chunk_id'] for row in cur.fetchall()]
                    cur.close()
                
                if definition_chunks:
                    logger.info(f"Found {len(definition_chunks)} definition chunks in Section 2")
                    chunk_details = self.get_chunk_details(definition_chunks)
                    answer_result = self.generate_answer(user_query, chunk_details)
                    
                    return {
                        'answer': answer_result['answer'],
                        'citations': answer_result['citations'],
                        'retrieved_chunks': [
                            {
                                'chunk_id': chunk['chunk_id'],
                                'section': chunk['section'],
                                'document_type': chunk['document_type'],
                                'text': chunk['text'][:500] + '...' if len(chunk['text']) > 500 else chunk['text'],
                                'title': chunk['title'],
                                'compliance_area': chunk['compliance_area'],
                                'priority': chunk['priority'],
                                'authority_level': chunk['authority_level'],
                                'citation': chunk['citation'],
                                'similarity_score': 1.0  
                            }
                            for chunk in chunk_details
                        ],
                        'relationships': []
                    }
        
        if section_match:
            # Direct section lookup
            section_num = section_match.group(1).zfill(3)  # Pad to 3 digits
            logger.info(f"Detected section number query: Section {section_num}")
            
            # Fetch directly from database
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT ci.chunk_id
                    FROM chunks_identity ci
                    WHERE ci.section = %s
                    ORDER BY 
                        CASE WHEN ci.chunk_role = 'parent' THEN 0 ELSE 1 END,
                        ci.chunk_id
                    LIMIT %s
                """, (section_num, top_k))
                
                chunk_ids = [row['chunk_id'] for row in cur.fetchall()]
                cur.close()
            
            if chunk_ids:
                logger.info(f"Found {len(chunk_ids)} chunks for Section {section_num} (direct lookup)")
                chunk_details = self.get_chunk_details(chunk_ids)
                
                # Generate answer from direct lookup ONLY
                answer_result = self.generate_answer(user_query, chunk_details)
                logger.info(f"Generated answer ({len(answer_result['answer'])} chars)")
                
                # Store direct lookup results
                direct_chunks = [
                    {
                        'chunk_id': chunk['chunk_id'],
                        'section': chunk['section'],
                        'document_type': chunk['document_type'],
                        'text': chunk['text'][:500] + '...' if len(chunk['text']) > 500 else chunk['text'],
                        'title': chunk['title'],
                        'compliance_area': chunk['compliance_area'],
                        'priority': chunk['priority'],
                        'authority_level': chunk['authority_level'],
                        'citation': chunk['citation'],
                        'similarity_score': 1.0,  # Direct match
                        'source_type': 'direct_lookup'  # Mark as primary source
                    }
                    for chunk in chunk_details
                ]
                
                # ALSO do vector search to find non-binding documents (FAQ, textbooks, etc.)
                logger.info(f"Also performing vector search for supplementary non-binding documents...")
                vector_results = self.search_vectors(user_query, top_k)
                
                # Get vector search chunks (excluding duplicates from direct lookup)
                direct_chunk_ids = {c['chunk_id'] for c in direct_chunks}
                vector_chunk_ids = [r['chunk_id'] for r in vector_results if r['chunk_id'] not in direct_chunk_ids]
                
                supplementary_chunks = []
                if vector_chunk_ids:
                    score_map = {r['chunk_id']: r['similarity_score'] for r in vector_results}
                    vector_chunk_details = self.get_chunk_details(vector_chunk_ids)
                    
                    supplementary_chunks = [
                        {
                            'chunk_id': chunk['chunk_id'],
                            'section': chunk['section'],
                            'document_type': chunk['document_type'],
                            'text': chunk['text'][:500] + '...' if len(chunk['text']) > 500 else chunk['text'],
                            'title': chunk['title'],
                            'compliance_area': chunk['compliance_area'],
                            'priority': chunk['priority'],
                            'authority_level': chunk['authority_level'],
                            'citation': chunk['citation'],
                            'similarity_score': score_map.get(chunk['chunk_id'], 0),
                            'source_type': 'supplementary'  # Mark as supplementary
                        }
                        for chunk in vector_chunk_details
                    ]
                    
                    logger.info(f"Found {len(supplementary_chunks)} supplementary chunks from vector search")
                
                # Return: Answer from direct lookup + all chunks (direct + supplementary)
                all_chunks = direct_chunks + supplementary_chunks[:top_k - len(direct_chunks)]
                
                logger.info(f"Returning: {len(direct_chunks)} direct chunks + {len(supplementary_chunks)} supplementary chunks")
                
                return {
                    'answer': answer_result['answer'],  # Answer ONLY from direct lookup
                    'citations': answer_result['citations'],
                    'retrieved_chunks': all_chunks,
                    'direct_lookup_count': len(direct_chunks),
                    'supplementary_count': len(supplementary_chunks),
                    'relationships': []
                }
        
        # Vector search for queries without section numbers
        # Step 1: Vector search
        vector_results = self.search_vectors(user_query, top_k)
        logger.info(f"Found {len(vector_results)} vector matches")
        
        if not vector_results:
            return {
                'answer': 'No relevant information found in the database.',
                'citations': [],
                'retrieved_chunks': [],
                'relationships': []
            }
        
        # Step 2: Get full chunk details from PostgreSQL
        chunk_ids = [r['chunk_id'] for r in vector_results]
        score_map = {r['chunk_id']: r['similarity_score'] for r in vector_results}
        chunk_details = self.get_chunk_details(chunk_ids)
        logger.info(f"Retrieved {len(chunk_details)} chunks from PostgreSQL")
        
        # Step 3: Get relationships (optional)
        relationships = []
        if include_relationships:
            for chunk_id in [c['chunk_id'] for c in chunk_details[:3]]:  # Only top 3
                rels = self.get_chunk_relationships(chunk_id)
                relationships.extend(rels)
        
        # Step 4: Generate LLM answer
        answer_result = self.generate_answer(user_query, chunk_details)
        logger.info(f"Generated answer ({len(answer_result['answer'])} chars)")
        
        # Step 5: Format response
        return {
            'answer': answer_result['answer'],
            'citations': answer_result['citations'],
            'retrieved_chunks': [
                {
                    'chunk_id': chunk['chunk_id'],
                    'section': chunk['section'],
                    'document_type': chunk['document_type'],
                    'text': chunk['text'][:500] + '...' if len(chunk['text']) > 500 else chunk['text'],
                    'title': chunk['title'],
                    'compliance_area': chunk['compliance_area'],
                    'priority': chunk['priority'],
                    'authority_level': chunk['authority_level'],
                    'citation': chunk['citation'],
                    'similarity_score': score_map.get(chunk['chunk_id'], 0)
                }
                for chunk in chunk_details[:top_k]
            ],
            'relationships': [
                {
                    'type': rel['relationship_type'],
                    'target': rel['target_chunk_id'],
                    'confidence': float(rel['confidence_score']) if rel['confidence_score'] else 0
                }
                for rel in relationships
            ] if include_relationships else []
        }


# Test function
if __name__ == "__main__":
    retriever = GovernanceRetriever()
    
    test_queries = [
        "What are the requirements for company incorporation?",
        "Who can be a director of a company?",
        "What is the minimum share capital required?"
    ]
    
    for query in test_queries:
        print("\n" + "="*70)
        result = retriever.query(query, top_k=20)
        
        print(f"\nQuery: {query}")
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nCitations: {', '.join(result['citations'])}")
        print(f"\nRetrieved Chunks: {len(result['retrieved_chunks'])}")