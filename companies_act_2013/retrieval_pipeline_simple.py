import json
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import faiss
from langchain_ollama import OllamaEmbeddings, OllamaLLM

VECTOR_STORE_DIR = Path("vector_store")
FAISS_INDEX_FILE = VECTOR_STORE_DIR / "faiss_index.bin"
METADATA_FILE = VECTOR_STORE_DIR / "embedding_metadata.json"
CHUNKS_FILE = Path("chunks/chunks_final.json")

EMBEDDING_MODEL = "qwen3-embedding:0.6b"
LLM_MODEL = "qwen2.5:1.5b"

TOP_K = 30

class GovernanceRetriever:
 
    def __init__(self):
        print(f"\n{'='*80}")
        print("SIMPLE LEGAL RAG - RETRIEVAL PIPELINE")
        print(f"{'='*80}\n")
        print(f"[1/5] Initializing embeddings ({EMBEDDING_MODEL})...")
        self.embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url="http://localhost:11434"
        )
        print(" Embeddings initialized")
        
        print(f"\n[2/5] Loading FAISS index from {FAISS_INDEX_FILE}...")
        self.faiss_index = faiss.read_index(str(FAISS_INDEX_FILE))
        print(f"FAISS index loaded ({self.faiss_index.ntotal} vectors)")
        
        print(f"\n[3/5] Loading metadata from {METADATA_FILE}...")
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            metadata_data = json.load(f)
        
        self.index_to_chunk_id = metadata_data['index_to_chunk_id']
        self.metadata_list = metadata_data['metadata']
        self.embedding_dim = metadata_data['embedding_dimension']
        
        print(f" Loaded metadata for {len(self.metadata_list)} chunks")
        
        print(f"\n[4/5] Loading source chunks from {CHUNKS_FILE}...")
        with open(CHUNKS_FILE, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        
        self.chunks = {c['chunk_id']: c for c in chunks_data.get('chunks', [])}
        print(f" Loaded {len(self.chunks)} source chunks")
        
        print(f"\n[5/5] Initializing LLM ({LLM_MODEL})...")
        self.llm = OllamaLLM(
            model=LLM_MODEL,
            base_url="http://localhost:11434",
            temperature=0.3
        )
        print(" LLM initialized")
        
        print(f"\n{'='*80}")
        print("RETRIEVAL PIPELINE READY")
        print(f"{'='*80}\n")
    
    def retrieve(self, query: str) -> Dict[str, Any]:
        """Simple retrieval with detailed explanation."""
        print(f"\n{'='*80}")
        print(f"QUERY: {query}")
        print(f"{'='*80}\n")
        
        print(f"[1/3] FAISS similarity search...")
        query_embedding = np.array(self.embeddings.embed_query(query), dtype=np.float32)
        query_embedding = query_embedding.reshape(1, -1)
        distances, indices = self.faiss_index.search(query_embedding, TOP_K)
        print(f" Retrieved {len(indices[0])} candidates")
        
        print(f"\n[2/3] Mapping to chunks...")
        all_chunks = []
        
        for idx in indices[0]:
            if idx == -1:
                continue
            
            chunk_id = self.index_to_chunk_id.get(str(idx))
            if not chunk_id:
                continue
            
            metadata = self.metadata_list[int(idx)]
            source_chunk = self.chunks.get(chunk_id)
            
            if not source_chunk or not source_chunk.get('text'):
                continue
            
            all_chunks.append({
                'chunk_id': chunk_id,
                'document_type': metadata['document_type'],
                'citation': source_chunk.get('citation', 'No citation'),
                'text': source_chunk['text'],
                'section': metadata.get('section'),
                'metadata': metadata
            })
        
        print(f" Found {len(all_chunks)} chunks")
        print(f"  Document types: {', '.join(set(c['document_type'] for c in all_chunks))}")
        
        print(f"\n[3/3] Generating detailed explanation...")
        answer, citations = self._generate_explanation(query, all_chunks)
        print(f" Generated answer ({len(answer)} chars)")
        
        sections = self._group_for_display(all_chunks)
        
        output = {
            "query": query,
            "answer": answer,
            "citations": citations,
            "retrieved_sections": sections
        }
        
        print(f"\n{'='*80}")
        print("RETRIEVAL COMPLETE")
        print(f"{'='*80}\n")
        
        return output
    
    def _generate_explanation(self, query: str, chunks: List[Dict]) -> tuple:
        if not chunks:
            return "No relevant information found.", []
        context_parts = []
        citations = []
        
        for chunk in chunks:
            doc_type = chunk['document_type'].upper()
            citation = chunk['citation']
            text = chunk['text']
            
            context_parts.append(f"[{doc_type}] {citation}\n{text}")
            citations.append(citation)
        
        context = "\n\n---\n\n".join(context_parts)[:8000]
        
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

WELL-FORMATTED MARKDOWN ANSWER:
"""
        
        try:
            answer = self.llm.invoke(prompt).strip()
        except Exception as e:
            print(f" LLM failed: {e}")
            answer = "Error generating explanation."
        
        return answer, list(set(citations))
    
    def _group_for_display(self, chunks: List[Dict]) -> List[Dict]:
        grouped = {}
        
        for chunk in chunks:
            section = chunk.get('section', 0)
            if section not in grouped:
                grouped[section] = {
                    'section': section,
                    'primary_chunk': None,
                    'supporting_chunks': []
                }
            
            if chunk['document_type'] == 'act' and not grouped[section]['primary_chunk']:
                grouped[section]['primary_chunk'] = {
                    'chunk_id': chunk['chunk_id'],
                    'citation': chunk['citation'],
                    'text': chunk['text'],
                    'section': section,
                    'is_primary': True
                }
            else:
                grouped[section]['supporting_chunks'].append({
                    'chunk_id': chunk['chunk_id'],
                    'document_type': chunk['document_type'],
                    'citation': chunk['citation'],
                    'text': chunk['text']
                })
        
        return [v for v in grouped.values() if v['primary_chunk']]


def main():
    retriever = GovernanceRetriever()
    
    print("\nExample queries:")
    print("  1. What is the process for incorporation of a company?")
    print("  2. What are the requirements for registered office?")
    print("  3. What forms are required for company registration?")
    
    print("\n" + "="*80)
    while True:
        query = input("\nEnter query (or 'quit'): ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        try:
            result = retriever.retrieve(query)
            print(f"\n{'='*80}")
            print("ANSWER")
            print(f"{'='*80}\n")
            print(result['answer'])
            print(f"\n\nCitations ({len(result['citations'])}):")
            for i, cite in enumerate(result['citations'][:5], 1):
                print(f"  {i}. {cite}")
            print(f"\n{'='*80}\n")
            
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
