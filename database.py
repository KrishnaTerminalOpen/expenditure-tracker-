"""
SpendWise Database Module
Handles SQLite schema, seed data, and connection helpers.
"""
import sqlite3
import os
import shutil
import tempfile
import bcrypt
from avatars import get_avatar_for_user

def get_db_path() -> str:
    """
    Returns the appropriate SQLite database file path.
    On Vercel and serverless platforms where /var/task is read-only,
    copies spendwise.db to the writable /tmp directory if needed.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    source_db = os.path.join(base_dir, "spendwise.db")

    is_vercel = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') is not None
    is_readonly = not os.access(base_dir, os.W_OK)

    if is_vercel or is_readonly:
        tmp_dir = tempfile.gettempdir()
        tmp_db = os.path.join(tmp_dir, "spendwise.db")
        if not os.path.exists(tmp_db) and os.path.exists(source_db):
            try:
                shutil.copy2(source_db, tmp_db)
                os.chmod(tmp_db, 0o666)
            except Exception as e:
                print(f"Error copying DB to tmp: {e}")
        return tmp_db
    return source_db

def get_db():
    conn = sqlite3.connect(get_db_path(), timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        google_id TEXT UNIQUE,
        monthly_budget REAL DEFAULT 0.0,
        currency TEXT DEFAULT '₹',
        theme TEXT DEFAULT 'dark',
        avatar TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Automatic migration: Ensure google_id column exists on existing installations
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [col[1] for col in cursor.fetchall()]
    if 'google_id' not in user_columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id)")
        except Exception as e:
            print(f"Migration note (google_id): {e}")

    # Automatic migration: Ensure password_hash is nullable for Google-only users
    cursor.execute("PRAGMA table_info(users)")
    pw_col = next((r for r in cursor.fetchall() if r[1] == 'password_hash'), None)
    if pw_col and pw_col[3] == 1:  # notnull is index 3
        try:
            cursor.execute("PRAGMA foreign_keys=OFF")
            cursor.execute("""
                CREATE TABLE users_temp (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    google_id TEXT UNIQUE,
                    monthly_budget REAL DEFAULT 0.0,
                    currency TEXT DEFAULT '₹',
                    theme TEXT DEFAULT 'dark',
                    avatar TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                INSERT INTO users_temp (id, name, email, password_hash, google_id, monthly_budget, currency, theme, avatar, created_at)
                SELECT id, name, email, password_hash, google_id, monthly_budget, currency, theme, avatar, created_at FROM users
            """)
            cursor.execute("DROP TABLE users")
            cursor.execute("ALTER TABLE users_temp RENAME TO users")
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id)")
            cursor.execute("PRAGMA foreign_keys=ON")
            conn.commit()
        except Exception as e:
            print(f"Migration note (password_hash nullable): {e}")

    # Categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT NOT NULL,
        color TEXT NOT NULL,
        budget_limit REAL DEFAULT 0.0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Payment Methods table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_methods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT NOT NULL,
        is_default INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Expenses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        payment_method TEXT NOT NULL,
        expense_date TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Notifications & Insights table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT NOT NULL, -- alert, tip, stat, warning, success
        is_read INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Subscriptions & Recurring Bills table (Module 9)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        billing_cycle TEXT NOT NULL DEFAULT 'monthly', -- monthly, yearly, weekly
        next_due_date TEXT NOT NULL,
        payment_method TEXT NOT NULL DEFAULT 'UPI',
        status TEXT NOT NULL DEFAULT 'active', -- active, paused, cancelled
        auto_renew INTEGER DEFAULT 1,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Financial Savings Goals & Targets table (Module 10)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS savings_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        target_amount REAL NOT NULL,
        current_amount REAL NOT NULL DEFAULT 0.0,
        target_date TEXT,
        category TEXT DEFAULT 'General',
        color TEXT DEFAULT '#10b981',
        icon TEXT DEFAULT 'bullseye',
        status TEXT NOT NULL DEFAULT 'in_progress', -- in_progress, achieved
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    # Savings Goal Contributions Audit table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS savings_contributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        goal_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        contribution_date TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (goal_id) REFERENCES savings_goals (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    conn.commit()

    # Migrate any legacy shared avatar to unique gender-appropriate avatars
    migrate_user_avatars(cursor, conn)

    conn.close()

def migrate_user_avatars(cursor, conn):
    """
    Ensures each user receives a unique, gender-appropriate avatar
    instead of sharing a generic default image.
    """
    try:
        cursor.execute("SELECT id, name, email, avatar FROM users")
        rows = cursor.fetchall()
        for row in rows:
            uid = row['id']
            name = row['name'] or ''
            email = row['email'] or ''
            curr = (row['avatar'] or '').strip()
            # If empty or using old hardcoded female photo
            if not curr or 'photo-1534528741775' in curr:
                new_av = get_avatar_for_user(name, email)
                cursor.execute("UPDATE users SET avatar = ? WHERE id = ?", (new_av, uid))
        conn.commit()
    except Exception as e:
        print(f"Avatar migration error: {e}")

def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_pw(password: str, hashed: str) -> bool:
    if not hashed or not password:
        return False
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

