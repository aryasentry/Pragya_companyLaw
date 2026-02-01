#!/usr/bin/env python3
"""
Pre-flight checklist - Run this before testing
Verifies all prerequisites are met
"""
import os
import sys
import subprocess

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_docker_postgres():
    """Check if PostgreSQL Docker container is running"""
    print("\n🐳 Checking Docker PostgreSQL...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=pg-db", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "Up" in result.stdout:
            print("✅ PostgreSQL container is running")
            return True
        else:
            print("❌ PostgreSQL container is not running")
            print("   Start it with: docker start pg-db")
            return False
    except Exception as e:
        print(f"❌ Docker check failed: {e}")
        return False

def check_docker_pgadmin():
    """Check if pgAdmin Docker container is running"""
    print("\n🐳 Checking Docker pgAdmin...")
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=pgadmin", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if "Up" in result.stdout:
            print("✅ pgAdmin container is running")
            print("   Access at: http://localhost:5050")
            return True
        else:
            print("❌ pgAdmin container is not running")
            print("   Start it with: docker start pgadmin")
            return False
    except Exception as e:
        print(f"❌ Docker check failed: {e}")
        return False

def check_ollama():
    """Check if Ollama is running and has required models"""
    print("\n🤖 Checking Ollama...")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            has_embedding = "qwen3-embedding" in result.stdout
            has_llm = "qwen2.5" in result.stdout
            
            if has_embedding:
                print("✅ Ollama embedding model found: qwen3-embedding:0.6b")
            else:
                print("❌ Missing embedding model")
                print("   Install: ollama pull qwen3-embedding:0.6b")
            
            if has_llm:
                print("✅ Ollama LLM found: qwen2.5:1.5b")
            else:
                print("⚠️  Missing LLM model (optional for chunking)")
                print("   Install: ollama pull qwen2.5:1.5b")
            
            return has_embedding
        else:
            print("❌ Ollama not responding")
            print("   Make sure Ollama is running: ollama serve")
            return False
    except FileNotFoundError:
        print("❌ Ollama not installed")
        print("   Install from: https://ollama.ai/")
        return False
    except Exception as e:
        print(f"❌ Ollama check failed: {e}")
        return False

def check_python_packages():
    """Check if required Python packages are installed"""
    print("\n📦 Checking Python packages...")
    required = {
        'psycopg2': 'psycopg2-binary',
        'dotenv': 'python-dotenv',
        'requests': 'requests',
        'flask': 'flask'
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} not installed")
            missing.append(package)
    
    if missing:
        print(f"\n   Install missing packages:")
        print(f"   pip install {' '.join(missing)}")
        return False
    return True

def check_env_file():
    """Check if .env file exists"""
    print("\n⚙️  Checking environment configuration...")
    if os.path.exists('.env'):
        print("✅ .env file exists")
        
        # Verify key variables
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = [
            'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD',
            'OLLAMA_BASE_URL', 'OLLAMA_EMBEDDING_MODEL'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
            return False
        
        print("✅ All environment variables set")
        return True
    else:
        print("❌ .env file not found")
        print("   Copy .env.example to .env and configure")
        return False

def check_database_connection():
    """Test database connection"""
    print("\n🔌 Testing database connection...")
    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'testdb'),
            user=os.getenv('DB_USER', 'arya'),
            password=os.getenv('DB_PASSWORD', 'secret123'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Connected to PostgreSQL")
        print(f"   {version[:50]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_database_initialized():
    """Check if database tables exist"""
    print("\n📊 Checking database schema...")
    try:
        import psycopg2
        from dotenv import load_dotenv
        load_dotenv()
        
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'testdb'),
            user=os.getenv('DB_USER', 'arya'),
            password=os.getenv('DB_PASSWORD', 'secret123'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'chunk%'
        """)
        table_count = cursor.fetchone()[0]
        
        if table_count >= 15:
            print(f"✅ Database initialized ({table_count} tables found)")
            cursor.close()
            conn.close()
            return True
        elif table_count > 0:
            print(f"⚠️  Partial initialization ({table_count}/15 tables)")
            print("   Re-run: python setup.py")
            cursor.close()
            conn.close()
            return False
        else:
            print("❌ Database not initialized (0 tables)")
            print("   Run: python setup.py")
            cursor.close()
            conn.close()
            return False
    except Exception as e:
        print(f"❌ Schema check failed: {e}")
        return False

def main():
    print_header("🚀 Governance RAG - Pre-Flight Checklist")
    
    checks = [
        ("Docker PostgreSQL", check_docker_postgres),
        ("Docker pgAdmin", check_docker_pgadmin),
        ("Ollama", check_ollama),
        ("Python Packages", check_python_packages),
        ("Environment Config", check_env_file),
        ("Database Connection", check_database_connection),
        ("Database Schema", check_database_initialized)
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check crashed: {e}")
            results.append((name, False))
    
    # Summary
    print_header("📋 Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\n{passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All checks passed! Ready to test.")
        print("\nNext steps:")
        print("  1. Run: python test_chunking.py")
        print("  2. View data in pgAdmin: http://localhost:5050")
        return 0
    else:
        print("\n⚠️  Some checks failed. Fix issues above before testing.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
