"""
SpendWise Database Module
Handles SQLite schema, seed data, and connection helpers.
"""
import sqlite3
import os
import bcrypt

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spendwise.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
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
        monthly_budget REAL DEFAULT 20000.0,
        currency TEXT DEFAULT '₹',
        theme TEXT DEFAULT 'dark',
        avatar TEXT DEFAULT 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150',
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
        budget_limit REAL DEFAULT 5000.0,
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

    conn.commit()

    # Seed demo user if none exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'krishna@example.com'")
    if cursor.fetchone()[0] == 0:
        seed_demo_data(cursor, conn)

    conn.close()

def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_pw(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def seed_demo_data(cursor, conn):
    pw_hash = hash_pw("password123")
    cursor.execute("""
        INSERT INTO users (name, email, password_hash, monthly_budget, currency, theme)
        VALUES ('Krishna Sahu', 'krishna@example.com', ?, 20000.0, '₹', 'dark')
    """, (pw_hash,))
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

if __name__ == "__main__":
    init_db()
    print("Database initialized and seeded successfully.")
