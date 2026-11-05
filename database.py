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
        password_hash TEXT NOT NULL,
        monthly_budget REAL DEFAULT 0.0,
        currency TEXT DEFAULT '₹',
        theme TEXT DEFAULT 'dark',
        avatar TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

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

    # Seed demo user if none exists
    cursor.execute("SELECT id FROM users WHERE email = 'krishna@example.com'")
    user_row = cursor.fetchone()
    if not user_row:
        seed_demo_data(cursor, conn)
    else:
        seed_advanced_demo_features(cursor, conn, user_row['id'])

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
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def seed_demo_data(cursor, conn):
    pw_hash = hash_pw("password123")
    demo_avatar = get_avatar_for_user('Krishna Sahu', 'krishna@example.com')
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, monthly_budget, currency, theme, avatar)
        VALUES ('Krishna Sahu', 'krishna@example.com', ?, 20000.0, '₹', 'dark', ?)
    """, (pw_hash, demo_avatar))
    user_id = cursor.lastrowid

    # Seed Categories with exact matches to screenshot
    categories = [
        ("Food & Dining", "utensils", "#f97316", 5000.0),
        ("Shopping", "shopping-bag", "#ec4899", 4000.0),
        ("Transport", "car", "#3b82f6", 2500.0),
        ("Bills & Utilities", "receipt", "#10b981", 2000.0),
        ("Entertainment", "film", "#8b5cf6", 2000.0),
        ("Education", "graduation-cap", "#6366f1", 1500.0),
        ("Health", "heart-pulse", "#ef4444", 2000.0),
        ("Others", "grid", "#64748b", 3000.0)
    ]
    for name, icon, color, limit in categories:
        cursor.execute("""
            INSERT INTO categories (user_id, name, icon, color, budget_limit)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, name, icon, color, limit))

    # Seed Payment Methods
    payment_methods = [
        ("UPI", "smartphone", 1),
        ("Cash", "banknote", 0),
        ("Debit Card", "credit-card", 0),
        ("Credit Card", "wallet-cards", 0),
        ("Bank Transfer", "landmark", 0),
        ("Others", "circle-ellipsis", 0)
    ]
    for name, icon, is_def in payment_methods:
        cursor.execute("""
            INSERT INTO payment_methods (user_id, name, icon, is_default)
            VALUES (?, ?, ?, ?)
        """, (user_id, name, icon, is_def))

    # Seed Expenses matching screenshot entries
    expenses = [
        ("Lunch at Cafe", 250.0, "Food & Dining", "UPI", "2024-05-31 12:00:00", "Team lunch"),
        ("Grocery Shopping", 450.0, "Shopping", "UPI", "2024-05-31 11:00:00", "Monthly groceries"),
        ("Auto Fare", 80.0, "Transport", "Cash", "2024-05-31 08:30:00", "Office commute"),
        ("Electricity Bill", 1250.0, "Bills & Utilities", "UPI", "2024-05-30 07:45:00", "May month bill"),
        ("Movie Ticket", 300.0, "Entertainment", "Card", "2024-05-30 05:30:00", "Avengers movie"),
        ("Dinner", 799.0, "Food & Dining", "UPI", "2024-05-30 08:20:00", "Dinner with friends"),
        ("Internet Bill", 799.0, "Bills & Utilities", "UPI", "2024-05-29 08:00:00", "Monthly internet"),
        ("Bus Ticket", 40.0, "Transport", "Cash", "2024-05-28 06:10:00", "To office"),
        ("Shopping", 1200.0, "Shopping", "Card", "2024-05-28 04:00:00", "Clothes shopping"),
        ("Mobile Recharge", 199.0, "Bills & Utilities", "UPI", "2024-05-27 11:30:00", "Monthly recharge"),
        ("Pharmacy Meds", 420.0, "Health", "UPI", "2024-05-26 14:00:00", "First aid & vitamins"),
        ("Online Course", 899.0, "Education", "Debit Card", "2024-05-25 18:00:00", "Python Deep Dive Course"),
        ("Weekend Cafe Outing", 650.0, "Food & Dining", "UPI", "2024-05-24 19:30:00", "Coffee & pastries with friends"),
        ("Cab to Airport", 550.0, "Transport", "UPI", "2024-05-22 09:15:00", "Business trip cab fare"),
        ("Bookstore Purchase", 350.0, "Education", "Cash", "2024-05-20 16:20:00", "Algorithms Book"),
        ("Fuel Refill", 1000.0, "Transport", "Credit Card", "2024-05-18 10:00:00", "Car petrol tank full"),
        ("Streaming Subscription", 499.0, "Entertainment", "Debit Card", "2024-05-15 12:00:00", "Annual plan renewing"),
        ("Supermarket Weekly Run", 1650.0, "Shopping", "UPI", "2024-05-12 11:30:00", "Household essentials"),
        ("Fitness Club Monthly", 800.0, "Health", "Bank Transfer", "2024-05-10 07:00:00", "Gym membership")
    ]

    for title, amount, cat, pmethod, dt, notes in expenses:
        cursor.execute("""
            INSERT INTO expenses (user_id, title, amount, category, payment_method, expense_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, amount, cat, pmethod, dt, notes))

    # Seed Notifications matching screenshot module 7
    notifications = [
        (user_id, "You spent 12% more than last month", "You spent ₹1,250 more on Food & Dining, which is 12% more than last month.", "alert", 0, "2 hours ago"),
        (user_id, "Great! You are under budget in 3 categories.", "You are doing great in Shopping, Transport and Entertainment.", "success", 0, "5 hours ago"),
        (user_id, "Your average daily spending is ₹415.", "This is 8% better than your last month average.", "stat", 0, "1 day ago"),
        (user_id, "Budget Alert: Food & Dining", "You have used 85% of your Food & Dining budget. ₹750 remaining.", "warning", 0, "1 day ago"),
        (user_id, "Save more by setting monthly limits.", "Set monthly limits for better expense control.", "tip", 1, "2 days ago")
    ]

    for uid, title, msg, ntype, read, created in notifications:
        cursor.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (uid, title, msg, ntype, read, created))

    conn.commit()

    seed_advanced_demo_features(cursor, conn, user_id)

def seed_advanced_demo_features(cursor, conn, user_id):
    # Seed Recurring Subscriptions if none exist
    cursor.execute("SELECT COUNT(*) FROM subscriptions WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0] == 0:
        subscriptions = [
            ("Netflix 4K Ultra", 649.0, "Entertainment", "monthly", "2026-11-15", "Credit Card", "active", 1, "Family 4K plan"),
            ("Spotify Family Premium", 179.0, "Entertainment", "monthly", "2026-11-22", "UPI", "active", 1, "Lossless audio streaming"),
            ("Airtel Fiber Gigabit", 999.0, "Bills & Utilities", "monthly", "2026-11-10", "UPI", "active", 1, "300 Mbps unlimited broadband"),
            ("AWS Cloud Infrastructure", 1250.0, "Bills & Utilities", "monthly", "2026-11-28", "Credit Card", "active", 1, "EC2 & S3 backend hosting"),
            ("Cult.fit Elite Fitness Club", 2000.0, "Health", "monthly", "2026-11-05", "UPI", "active", 1, "Gym and boxing classes")
        ]
        for name, amt, cat, cycle, due, pm, status, renew, notes in subscriptions:
            cursor.execute("""
                INSERT INTO subscriptions (user_id, name, amount, category, billing_cycle, next_due_date, payment_method, status, auto_renew, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, name, amt, cat, cycle, due, pm, status, renew, notes))

    # Seed Savings Goals if none exist
    cursor.execute("SELECT COUNT(*) FROM savings_goals WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0] == 0:
        goals = [
            ("Emergency Rainy-Day Fund", 100000.0, 65000.0, "2026-12-31", "Emergency", "#10b981", "shield-halved", "in_progress"),
            ("Apple MacBook Pro M3", 150000.0, 95000.0, "2026-08-31", "Gadgets", "#f97316", "laptop-code", "in_progress"),
            ("Tokyo & Kyoto Summer Trip", 80000.0, 36000.0, "2026-10-31", "Travel", "#3b82f6", "plane-departure", "in_progress")
        ]
        for title, target, current, target_dt, cat, color, icon, status in goals:
            cursor.execute("""
                INSERT INTO savings_goals (user_id, title, target_amount, current_amount, target_date, category, color, icon, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, title, target, current, target_dt, cat, color, icon, status))
            gid = cursor.lastrowid
            # Seed an audit contribution
            cursor.execute("""
                INSERT INTO savings_contributions (goal_id, user_id, amount, contribution_date, notes)
                VALUES (?, ?, ?, '2026-11-01', 'Initial monthly automated savings allocation')
            """, (gid, user_id, min(current, 10000.0)))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded successfully.")
