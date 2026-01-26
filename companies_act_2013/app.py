"""
Flask Web Server for Simple Legal RAG
Companies Act 2013 Retrieval System
"""

from flask import Flask, render_template, request, jsonify
from retrieval_pipeline_simple import GovernanceRetriever
import traceback

app = Flask(__name__)

# Initialize retriever on startup
print("Initializing retrieval system...")
try:
    retriever = GovernanceRetriever()
    print("✓ Retrieval system ready")
except Exception as e:
    print(f"✗ Failed to initialize retriever: {e}")
    retriever = None

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@app.route('/api/query', methods=['POST'])
def query():
    """Handle query requests."""
    if not retriever:
        return jsonify({
            'error': 'Retrieval system not initialized'
        }), 500
    
    try:
        data = request.get_json()
        query_text = data.get('query', '').strip()
        
        if not query_text:
            return jsonify({
                'error': 'Query cannot be empty'
            }), 400
        
        # Perform retrieval (includes LLM explanation)
        result = retriever.retrieve(query_text)
        
        # Format for frontend
        result['synthesized_answer'] = result.get('answer', 'No answer generated')
        result['answer_citations'] = result.get('citations', [])
        
        return jsonify({
            'success': True,
            'result': result
        })
    
    except Exception as e:
        print(f"Error processing query: {e}")
        traceback.print_exc()
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'retriever_ready': retriever is not None
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
