"""
Database configuration and connection management
"""
import os
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Database configuration (Docker PostgreSQL)
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'testdb'),
    'user': os.getenv('DB_USER', 'arya'),
    'password': os.getenv('DB_PASSWORD', 'secret123'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432')
}

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

def execute_query(query: str, params: Optional[tuple] = None, fetch: bool = False):
    """Execute a single query"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            return cursor.rowcount

def execute_many(query: str, params_list: list):
    """Execute batch insert/update"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount
