"""Run admin_audit_log migration on existing DB. Usage: python run_migrate_admin_audit.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db_config import get_db_connection

def main():
    sql_path = Path(__file__).parent / 'migrate_admin_audit.sql'
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    # Split by ';' and drop comment-only lines from each block so we don't skip CREATE TABLE
    raw = [s.strip() for s in sql.split(';') if s.strip()]
    statements = []
    for block in raw:
        lines = [line for line in block.splitlines() if line.strip() and not line.strip().startswith('--')]
        stmt = '\n'.join(lines).strip()
        if stmt:
            statements.append(stmt)
    for stmt in statements:
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(stmt)
            print("OK:", stmt[:60].replace('\n', ' ') + ("..." if len(stmt) > 60 else ""))
        except Exception as e:
            print("Skip:", e)
    print("admin_audit_log migration done.")

if __name__ == '__main__':
    main()
