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
                timeout=30
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
        
        context = "\n\n---\n\n".join(context_parts)[:8000]
        
        # Stricter prompt based on old working system
        prompt = f"""You are a legal information assistant for the Companies Act, 2013 (India).

QUESTION:
{query}

RELEVANT SOURCES:
{context}

INSTRUCTIONS:
Answer the question clearly and concisely. DO NOT copy statutory text verbatim.

Format your response using Markdown:
- Use **bold** for important terms and section references
- Use proper paragraphs with blank lines between them
- Use bullet points (- or *) for lists
- Use numbered lists (1., 2., 3.) for steps/procedures
- Use > for important notes or quotes if needed

Content guidelines:
- Summarize key points in plain language
- Answer the specific question asked
- Keep it brief (2-4 paragraphs maximum)
- Reference section numbers like **Section 1** or **Section 2(20)**
- If there are forms/procedures, list them clearly with numbers

DO NOT:
- Quote long statutory provisions verbatim
- Copy-paste entire sections
- Include irrelevant details
- Repeat yourself

WELL-FORMATTED MARKDOWN ANSWER:"""
        
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    'model': LLM_MODEL,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': 0.3,
                        'top_p': 0.9
                    }
                },
                timeout=45
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
        
        # Check if query is asking about a specific section number
        section_match = re.search(r'section\s+(\d+)', user_query.lower())
        
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
                
                # Generate answer
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
                        'similarity_score': 1.0  # Direct match
                    }
                    for chunk in chunk_details
                ]
                
                # ALSO do vector search to find non-binding documents (FAQ, textbooks, etc.)
                logger.info(f"Also performing vector search for non-binding documents...")
                vector_results = self.search_vectors(user_query, top_k)
                
                # Get vector search chunks (excluding duplicates from direct lookup)
                direct_chunk_ids = {c['chunk_id'] for c in direct_chunks}
                vector_chunk_ids = [r['chunk_id'] for r in vector_results if r['chunk_id'] not in direct_chunk_ids]
                
                if vector_chunk_ids:
                    score_map = {r['chunk_id']: r['similarity_score'] for r in vector_results}
                    vector_chunk_details = self.get_chunk_details(vector_chunk_ids)
                    
                    vector_chunks = [
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
                        for chunk in vector_chunk_details
                    ]
                    
                    # Combine: Direct lookup first, then vector search results
                    all_chunks = direct_chunks + vector_chunks[:top_k - len(direct_chunks)]
                    
                    # Generate answer from ALL chunks (binding + non-binding)
                    all_chunk_details = chunk_details + vector_chunk_details[:top_k - len(chunk_details)]
                    combined_answer = self.generate_answer(user_query, all_chunk_details)
                    
                    logger.info(f"Combined results: {len(direct_chunks)} direct + {len(vector_chunks)} vector")
                    
                    return {
                        'answer': combined_answer['answer'],
                        'citations': combined_answer['citations'],
                        'retrieved_chunks': all_chunks,
                        'relationships': []
                    }
                else:
                    # No additional vector results, return direct lookup only
                    return {
                        'answer': answer_result['answer'],
                        'citations': answer_result['citations'],
                        'retrieved_chunks': direct_chunks,
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
