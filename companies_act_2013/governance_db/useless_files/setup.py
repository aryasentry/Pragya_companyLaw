"""
Quick setup script for governance RAG system
Run this first to initialize the database
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("🚀 Governance RAG Setup Script")
print("=" * 60)

# Check database environment variables
db_config = {
    'DB_HOST': os.getenv('DB_HOST', 'localhost'),
    'DB_PORT': os.getenv('DB_PORT', '5432'),
    'DB_NAME': os.getenv('DB_NAME', 'testdb'),
    'DB_USER': os.getenv('DB_USER', 'arya'),
    'DB_PASSWORD': os.getenv('DB_PASSWORD', 'secret123')
}

print("\n📊 Database Configuration:")
for key, value in db_config.items():
    if 'PASSWORD' in key:
        print(f"  {key}: {'*' * len(value)}")
    else:
        print(f"  {key}: {value}")

# Check Ollama configuration
ollama_config = {
    'OLLAMA_BASE_URL': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
    'OLLAMA_EMBEDDING_MODEL': os.getenv('OLLAMA_EMBEDDING_MODEL', 'qwen3-embedding:0.6b'),
    'OLLAMA_LLM_MODEL': os.getenv('OLLAMA_LLM_MODEL', 'qwen2.5:1.5b')
}

print("\n🤖 Ollama Configuration:")
for key, value in ollama_config.items():
    print(f"  {key}: {value}")

# Test PostgreSQL connection
print("\n🔌 Testing PostgreSQL connection...")
try:
    import psycopg2
    conn = psycopg2.connect(
        dbname=db_config['DB_NAME'],
        user=db_config['DB_USER'],
        password=db_config['DB_PASSWORD'],
        host=db_config['DB_HOST'],
        port=db_config['DB_PORT']
    )
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"✅ PostgreSQL connected: {version[0][:50]}...")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ PostgreSQL connection failed: {e}")
    print("\nMake sure Docker PostgreSQL is running:")
    print("  docker ps | grep pg-db")
    sys.exit(1)

# Test Ollama connection
print("\n🤖 Testing Ollama connection...")
try:
    import requests
    response = requests.get(f"{ollama_config['OLLAMA_BASE_URL']}/api/tags", timeout=5)
    if response.status_code == 200:
        models = response.json().get('models', [])
        print(f"✅ Ollama connected. Found {len(models)} models:")
        for model in models:
            print(f"  - {model['name']}")
    else:
        print(f"⚠️ Ollama responded with status {response.status_code}")
except Exception as e:
    print(f"⚠️ Ollama connection failed: {e}")
    print("\nMake sure Ollama is running:")
    print("  ollama list")

# Initialize database
print("\n📝 Initializing database schema...")
try:
    import psycopg2
    from db_config import get_db_connection
    
    # Read and execute schema.sql
    with open('schema.sql', 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(schema_sql)
        cur.close()
    
    print("✅ Database schema initialized successfully")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ SETUP COMPLETE!")
print("=" * 60)
print("\n📚 Next Steps:")
print("  1. Run chunking test: python test_chunking.py")
print("  2. View data in pgAdmin: http://localhost:5050")
print("     Email: arya@gmail.com")
print("     Password: admin123")
print("  3. Connect to PostgreSQL:")
print("     Host: pg-db")
print("     Port: 5432")
print("     Database: testdb")
print("     Username: arya")
print("     Password: secret123")
