"""
SpendWise: Local SQLite to Turso Cloud Database Migration Script
Use this script to upload your existing local spendwise.db data
(users, expenses, categories, goals, etc.) directly into your Turso Cloud Database.

Usage:
    python migrate_to_turso.py [TURSO_DATABASE_URL] [TURSO_AUTH_TOKEN]

Or set them in your .env file:
    TURSO_DATABASE_URL=libsql://your-db.turso.io
    TURSO_AUTH_TOKEN=your-token
"""
import os
import sys
import sqlite3
from dotenv import load_dotenv

load_dotenv()

def migrate():
    # 1. Get credentials
    turso_url = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get('TURSO_DATABASE_URL')
    turso_token = (sys.argv[2] if len(sys.argv) > 2 else None) or os.environ.get('TURSO_AUTH_TOKEN')

    if not turso_url or not turso_token:
        print("=" * 60)
        print("SpendWise Turso Cloud Migration")
        print("=" * 60)
        print("Missing Turso credentials.")
        print("\nPlease run with:")
        print("    python migrate_to_turso.py <TURSO_DATABASE_URL> <TURSO_AUTH_TOKEN>")
        print("\nOr add them to your .env file:")
        print("    TURSO_DATABASE_URL=libsql://your-db.turso.io")
        print("    TURSO_AUTH_TOKEN=your-auth-token")
        return

    try:
        import libsql
    except ImportError:
        print("Error: 'libsql' is not installed. Please run: pip install libsql")
        return

    # 2. Connect to local database
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_db_path = os.path.join(base_dir, "spendwise.db")
    if not os.path.exists(local_db_path):
        print(f"Error: Local database '{local_db_path}' not found.")
        return

    print(f"Connecting to local SQLite database: {local_db_path}...")
    local_conn = sqlite3.connect(local_db_path)
    local_conn.row_factory = sqlite3.Row

    print(f"Connecting to Turso Cloud Database: {turso_url}...")
    remote_conn = libsql.connect(database=turso_url, auth_token=turso_token)

    # 3. Initialize schema on Turso
    print("Ensuring database schema exists on Turso...")
    os.environ['TURSO_DATABASE_URL'] = turso_url
    os.environ['TURSO_AUTH_TOKEN'] = turso_token
    from database import init_db
    init_db()
    print("Schema initialized on Turso successfully.")

    tables = [
        'users',
        'categories',
        'payment_methods',
        'expenses',
        'notifications',
        'subscriptions',
        'savings_goals',
        'savings_contributions'
    ]

    print("\nStarting data migration...")
    total_migrated = 0

    for table in tables:
        try:
            # Check if table exists locally
            local_cur = local_conn.execute(f"SELECT * FROM {table}")
            rows = local_cur.fetchall()
            if not rows:
                print(f"  • {table}: 0 rows found locally.")
                continue

            col_names = [d[0] for d in local_cur.description]
            placeholders = ", ".join(["?"] * len(col_names))
            cols_str = ", ".join(col_names)

            insert_sql = f"INSERT OR REPLACE INTO {table} ({cols_str}) VALUES ({placeholders})"

            count = 0
            for r in rows:
                vals = [r[col] for col in col_names]
                remote_conn.execute(insert_sql, vals)
                count += 1

            remote_conn.commit()
            total_migrated += count
            print(f"  ✓ {table}: Successfully migrated {count} row(s).")
        except Exception as e:
            print(f"  ✗ {table}: Error migrating ({e})")

    local_conn.close()
    remote_conn.close()
    print("=" * 60)
    print(f"Migration completed! Total {total_migrated} records synchronized to Turso.")
    print("Your SpendWise cloud database is now active and persistent forever.")
    print("=" * 60)

if __name__ == "__main__":
    migrate()

