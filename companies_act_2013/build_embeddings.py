"""
Build FAISS embeddings for Companies Act 2013 chunks
Uses Ollama embeddings (qwen3-embedding:0.6b)
"""

import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any
from langchain_ollama import OllamaEmbeddings
from tqdm import tqdm


class EmbeddingBuilder:
    def __init__(self, model_name: str = "qwen3-embedding:0.6b"):
        """Initialize embedding builder with Ollama model"""
        print(f"Initializing embeddings with model: {model_name}")
        self.embeddings = OllamaEmbeddings(
            model=model_name,
            base_url="http://localhost:11434"
        )
        self.dimension = 1024  # qwen3-embedding produces 1024-dim vectors
        
    def load_chunks(self, chunks_file: Path) -> List[Dict[str, Any]]:
        """Load chunks from JSON file"""
        print(f"Loading chunks from {chunks_file}...")
        with open(chunks_file, 'r', encoding='utf-8') as f:
            chunks = json.load(f)
        print(f"Loaded {len(chunks)} chunks")
        return chunks
    
    def create_embeddings(self, chunks: List[Dict[str, Any]]) -> tuple:
        """
        Create embeddings for all chunks
        Returns: (embeddings_array, metadata_list)
        """
        print("Creating embeddings...")
        
        embeddings_list = []
        metadata_list = []
        
        # Process in batches for efficiency
        batch_size = 10
        for i in tqdm(range(0, len(chunks), batch_size)):
            batch = chunks[i:i+batch_size]
            
            # Create text for embedding (combine title and text)
            texts = []
            for chunk in batch:
                title = chunk.get("title", "")
                text = chunk.get("text", "")
                section = chunk.get("section", "")
                
                # Create rich text for better embeddings
                embedding_text = f"Section {section}: {title}\n{text}" if section else f"{title}\n{text}"
                texts.append(embedding_text)
            
            try:
                # Get embeddings from Ollama
                batch_embeddings = self.embeddings.embed_documents(texts)
                
                # Store embeddings and metadata
                for j, embedding in enumerate(batch_embeddings):
                    embeddings_list.append(embedding)
                    metadata_list.append({
                        "chunk_index": i + j,
                        "section": batch[j].get("section"),
                        "sub_section": batch[j].get("sub_section"),
                        "citation": batch[j].get("citation"),
                        "document_type": batch[j].get("document_type"),
                        "title": batch[j].get("title")
                    })
                    
            except Exception as e:
                print(f"Error embedding batch {i}: {e}")
                continue
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings_list, dtype=np.float32)
        print(f"Created {len(embeddings_array)} embeddings of dimension {embeddings_array.shape[1]}")
        
        return embeddings_array, metadata_list
    
    def build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """Build FAISS index from embeddings"""
        print("Building FAISS index...")
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Create FlatL2 index (exact search)
        index = faiss.IndexFlatL2(self.dimension)
        index.add(embeddings)
        
        print(f"Built FAISS index with {index.ntotal} vectors")
        return index
    
    def save_index(self, index: faiss.Index, metadata: List[Dict], output_dir: Path):
        """Save FAISS index and metadata"""
        output_dir.mkdir(exist_ok=True)
        
        # Save FAISS index
        index_file = output_dir / "faiss_index.bin"
        faiss.write_index(index, str(index_file))
        print(f"Saved FAISS index to {index_file}")
        
        # Save metadata
        metadata_file = output_dir / "embedding_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"Saved metadata to {metadata_file}")
    
    def verify_index(self, index: faiss.Index, chunks: List[Dict], metadata: List[Dict]):
        """Verify the index works with a sample query"""
        print("\n=== Verifying Index ===")
        
        # Test query
        test_query = "What is the process for company incorporation?"
        print(f"Test query: {test_query}")
        
        # Get query embedding
        query_embedding = np.array([self.embeddings.embed_query(test_query)], dtype=np.float32)
        faiss.normalize_L2(query_embedding)
        
        # Search
        k = 5
        distances, indices = index.search(query_embedding, k)
        
        print(f"\nTop {k} results:")
        for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
            meta = metadata[idx]
            print(f"{i+1}. Section {meta['section']}: {meta['title']}")
            print(f"   Citation: {meta['citation']}")
            print(f"   Distance: {dist:.4f}")
            print()


def main():
    """Main execution"""
    # Paths
    chunks_file = Path("chunks_final.json")
    output_dir = Path("vector_store")
    
    # Check if chunks file exists
    if not chunks_file.exists():
        print(f"Error: {chunks_file} not found!")
        print("Please run chunking_engine.py first to create chunks.")
        return
    
    # Initialize builder
    builder = EmbeddingBuilder(model_name="qwen3-embedding:0.6b")
    
    # Load chunks
    chunks = builder.load_chunks(chunks_file)
    
    # Filter out chunks with no text
    chunks = [c for c in chunks if c.get("text", "").strip()]
    print(f"Processing {len(chunks)} chunks with text")
    
    # Create embeddings
    embeddings, metadata = builder.create_embeddings(chunks)
    
    # Build FAISS index
    index = builder.build_faiss_index(embeddings)
    
    # Save
    builder.save_index(index, metadata, output_dir)
    
    # Verify
    builder.verify_index(index, chunks, metadata)
    
    print("\n=== Build Complete ===")
    print(f"Total vectors: {index.ntotal}")
    print(f"Dimension: {embeddings.shape[1]}")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()
