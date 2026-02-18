"""
Implement hybrid retrieval: Section lookup + Vector search
"""

file_path = r'c:\Users\kalid\OneDrive\Documents\RAG\companies_act_2013\governance_db\retrieval_service_faiss.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the section where we return after direct lookup
# We need to modify it to ALSO do vector search and combine results

old_pattern = """                return {
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
                            'similarity_score': 1.0  # Direct match
                        }
                        for chunk in chunk_details
                    ],
                    'relationships': []
                }
        
        # Fall back to vector search for other queries"""

new_pattern = """                # Store direct lookup results
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
        
        # Vector search for queries without section numbers"""

if old_pattern in content:
    content = content.replace(old_pattern, new_pattern)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Implemented hybrid retrieval!")
    print("  - Direct section lookup for binding documents (ACT, rules, etc.)")
    print("  - Vector search for non-binding documents (FAQ, textbooks, etc.)")
    print("  - Combined results for comprehensive answers")
    print("\n⚠️  RESTART Flask server for changes to take effect")
else:
    print("❌ Pattern not found. Manual edit required.")
    print("\nSearching for alternative pattern...")
    
    # Try to find the return statement
    if "'relationships': []" in content and "# Fall back to vector search" in content:
        print("✓ Found the section, but pattern doesn't match exactly.")
        print("  This might be due to previous edits.")
        print("\n📝 Manual fix needed - see the new pattern above")
