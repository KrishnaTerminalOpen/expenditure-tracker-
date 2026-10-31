"""
SpendWise Web Application
Full Python Flask Backend powering the 8 modules shown in the design:
1. Authentication & Profile
2. Dashboard
3. Expense Management (CRUD + Filter + Search + Add Modal)
4. Category & Payment Management
5. Budget Management
6. Analytics & Reports
7. Notifications & Spending Insights
8. Expense History, Search & Export (CSV & PDF)
"""
import io
import csv
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, Response
)
from database import get_db, init_db, hash_pw, check_pw
from pdf_generator import generate_expense_pdf

app = Flask(__name__)
app.secret_key = "spendwise-super-secret-production-key-2026"

@app.template_filter('cat_class')
def cat_class(cat_name):
    mapping = {
        'Food & Dining': 'cat-dot-food',
        'Shopping': 'cat-dot-shopping',
        'Transport': 'cat-dot-transport',
        'Bills & Utilities': 'cat-dot-bills',
        'Entertainment': 'cat-dot-entertainment',
        'Education': 'cat-dot-education',
        'Health': 'cat-dot-health'
    }
    return mapping.get(cat_name, 'cat-dot-others')

# Ensure DB is ready
init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return user

# ==========================================
# MODULE 1: AUTHENTICATION & PROFILE
# ==========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and check_pw(password, user['password_hash']):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']

            # Check if user has recorded any transactions
            txn_count = conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user['id'],)).fetchone()[0]
            if txn_count == 0:
                flash(f"Welcome, {user['name']}! Let's record your first expense to activate your dashboard.", "info")
                return redirect(url_for('first_transaction'))

            flash("Welcome back!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid email or password. Please try again.", "danger")
            return render_template('auth.html', active_tab='login', email=email)

    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('auth.html', active_tab='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if not name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template('auth.html', active_tab='register', name=name, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('auth.html', active_tab='register', name=name, email=email)

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with this email already exists.", "danger")
            return render_template('auth.html', active_tab='register', name=name)

        hashed = hash_pw(password)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, monthly_budget)
            VALUES (?, ?, ?, 20000.0)
        """, (name, email, hashed))
        new_user_id = cursor.lastrowid

        # Seed initial categories for new user
        cats = [
            ("Food & Dining", "utensils", "#f97316", 5000.0),
            ("Shopping", "shopping-bag", "#ec4899", 4000.0),
            ("Transport", "car", "#3b82f6", 2500.0),
            ("Bills & Utilities", "receipt", "#10b981", 2000.0),
            ("Entertainment", "film", "#8b5cf6", 2000.0),
            ("Education", "graduation-cap", "#6366f1", 1500.0),
            ("Health", "heart-pulse", "#ef4444", 2000.0),
            ("Others", "grid", "#64748b", 3000.0)
        ]
        for cname, icon, color, limit in cats:
            cursor.execute("INSERT INTO categories (user_id, name, icon, color, budget_limit) VALUES (?, ?, ?, ?, ?)",
                           (new_user_id, cname, icon, color, limit))

        # Seed payment methods
        pmethods = [
            ("UPI", "smartphone", 1),
            ("Cash", "banknote", 0),
            ("Debit Card", "credit-card", 0),
            ("Credit Card", "wallet-cards", 0),
            ("Bank Transfer", "landmark", 0),
            ("Others", "circle-ellipsis", 0)
        ]
        for pname, picon, is_def in pmethods:
            cursor.execute("INSERT INTO payment_methods (user_id, name, icon, is_default) VALUES (?, ?, ?, ?)",
                           (new_user_id, pname, picon, is_def))

        # Welcome notification
        cursor.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
            VALUES (?, 'Welcome to SpendWise!', 'Track your expenses, set budgets, and gain smart insights effortlessly.', 'success', 0, 'Just now')
        """, (new_user_id,))

        conn.commit()
        conn.close()

        session['user_id'] = new_user_id
        session['user_name'] = name
        session['user_email'] = email
        flash(f"Account created successfully! Welcome, {name}.", "success")
        return redirect(url_for('first_transaction'))

    return render_template('auth.html', active_tab='register')

@app.route('/first-transaction', methods=['GET', 'POST'])
@app.route('/onboarding', methods=['GET', 'POST'])
@login_required
def first_transaction():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        amount_raw = request.form.get('amount', '0').strip()
        try:
            amount = float(amount_raw)
        except ValueError:
            amount = 0.0

        category = request.form.get('category', 'Others')
        payment_method = request.form.get('payment_method', 'UPI')
        expense_date = request.form.get('expense_date', '').strip()
        notes = request.form.get('notes', '').strip()
        monthly_budget = request.form.get('monthly_budget', '').strip()

        if not expense_date:
            expense_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            expense_date = expense_date.replace('T', ' ')
            if len(expense_date) == 16:
                expense_date += ":00"

        if monthly_budget:
            try:
                mb_val = float(monthly_budget)
                conn.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (mb_val, uid))
            except ValueError:
                pass

        if amount > 0 and title:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO expenses (user_id, title, amount, category, payment_method, expense_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (uid, title, amount, category, payment_method, expense_date, notes))

            # Celebratory milestone notification
            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
                VALUES (?, '🎉 First Expense Recorded!', 'Congratulations! You have officially initiated your SpendWise tracking journey.', 'success', 0, 'Just now')
            """, (uid,))
            conn.commit()

        conn.close()
        session['skip_onboarding'] = True
        flash("🎉 Fantastic! Your first transaction has been logged. Welcome to your financial dashboard!", "success")
        return redirect(url_for('dashboard', first_txn=1))

    # GET request
    categories = conn.execute("SELECT * FROM categories WHERE user_id = ? ORDER BY id ASC", (uid,)).fetchall()
    payment_methods = conn.execute("SELECT * FROM payment_methods WHERE user_id = ? ORDER BY is_default DESC, id ASC", (uid,)).fetchall()
    conn.close()

    return render_template('onboarding.html', user=user, categories=categories, payment_methods=payment_methods)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    conn = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        monthly_budget = float(request.form.get('monthly_budget', 20000.0))
        currency = request.form.get('currency', '₹')
        theme = request.form.get('theme', 'dark')

        conn.execute("""
            UPDATE users SET name = ?, monthly_budget = ?, currency = ?, theme = ?
            WHERE id = ?
        """, (name, monthly_budget, currency, theme, user['id']))
        conn.commit()
        session['user_name'] = name
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    # Stats for profile card
    total_spent = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?", (user['id'],)).fetchone()[0]
    total_txns = conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user['id'],)).fetchone()[0]
    conn.close()
    return render_template('profile.html', user=user, current_page='profile', total_spent=total_spent, total_txns=total_txns)

# ==========================================
# MODULE 2: DASHBOARD
# ==========================================

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    # Check total transaction count
    txn_count = conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (uid,)).fetchone()[0]
    if txn_count == 0 and not request.args.get('skip_onboarding') and not session.get('skip_onboarding'):
        conn.close()
        return redirect(url_for('first_transaction'))

    if request.args.get('skip_onboarding'):
        session['skip_onboarding'] = True

    # Total expenses (All time)
    total_expenses = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?", (uid,)).fetchone()[0]

    # Today's expenses
    today_str = date.today().strftime('%Y-%m-%d')
    todays_expenses = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ? AND expense_date LIKE ?",
        (uid, f"{today_str}%")
    ).fetchone()[0]

    # Monthly budget and remaining
    monthly_budget = user['monthly_budget'] or 20000.0
    remaining_budget = max(0.0, monthly_budget - total_expenses)

    # Highest Category
    highest_cat_row = conn.execute("""
        SELECT category, SUM(amount) as cat_sum
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY cat_sum DESC
        LIMIT 1
    """, (uid,)).fetchone()
    if highest_cat_row:
        highest_category = highest_cat_row['category']
        highest_category_amount = highest_cat_row['cat_sum']
    else:
        highest_category = "No Expenses Yet"
        highest_category_amount = 0.0

    # Monthly Trend (31-day points or distinct dates)
    trend_rows = conn.execute("""
        SELECT SUBSTR(expense_date, 1, 10) as edate, SUM(amount) as day_total
        FROM expenses
        WHERE user_id = ?
        GROUP BY edate
        ORDER BY edate ASC
    """, (uid,)).fetchall()

    trend_labels = [r['edate'][-5:] for r in trend_rows]
    trend_values = [r['day_total'] for r in trend_rows]

    # Category breakdown for donut chart
    cat_breakdown = conn.execute("""
        SELECT category, SUM(amount) as total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
    """, (uid,)).fetchall()

    cat_labels = [r['category'] for r in cat_breakdown]
    cat_values = [r['total'] for r in cat_breakdown]
    cat_percentages = []
    if total_expenses > 0:
        for r in cat_breakdown:
            cat_percentages.append(round((r['total'] / total_expenses) * 100))

    # Recent Transactions (last 5)
    recent_txns = conn.execute("""
        SELECT * FROM expenses
        WHERE user_id = ?
        ORDER BY expense_date DESC, id DESC
        LIMIT 5
    """, (uid,)).fetchall()

    # Budget Progress items (categories with limit and spent)
    cat_budgets = conn.execute("""
        SELECT c.name, c.budget_limit, COALESCE(SUM(e.amount), 0) as spent, c.color
        FROM categories c
        LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.budget_limit DESC
        LIMIT 4
    """, (uid,)).fetchall()

    # Spending Insights
    unread_insights = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 3
    """, (uid,)).fetchall()

    # Dynamic Financial Health Score (0 - 100)
    if total_expenses > monthly_budget:
        over_pct = min(100, ((total_expenses - monthly_budget) / monthly_budget) * 100)
        health_score = max(20, round(55 - over_pct * 0.35))
        health_status = "Attention Required"
        health_status_class = "negative"
        health_tip = f"You are ₹{total_expenses - monthly_budget:,.0f} over your target limit. Review your {highest_category} category."
    elif total_expenses > 0:
        used_pct = (total_expenses / monthly_budget) * 100
        health_score = min(98, max(50, round(100 - (used_pct * 0.35))))
        if health_score >= 80:
            health_status = "Optimal Health"
            health_status_class = "positive"
            health_tip = f"Excellent pacing! You have used {used_pct:.0f}% of your monthly allocation with ₹{remaining_budget:,.0f} safe buffer."
        else:
            health_status = "Moderate"
            health_status_class = "warning"
            health_tip = f"You have reached {used_pct:.0f}% of your budget limit. Keep an eye on {highest_category}."
    else:
        health_score = 100
        health_status = "Ready to Track"
        health_status_class = "positive"
        health_tip = "No expenses recorded this cycle. Log purchases as they occur for maximum financial visibility."

    conn.close()

    return render_template(
        'dashboard.html',
        user=user,
        current_page='dashboard',
        total_expenses=total_expenses,
        todays_expenses=todays_expenses,
        monthly_budget=monthly_budget,
        remaining_budget=remaining_budget,
        highest_category=highest_category,
        highest_category_amount=highest_category_amount,
        trend_labels=trend_labels,
        trend_values=trend_values,
        cat_labels=cat_labels,
        cat_values=cat_values,
        cat_breakdown=cat_breakdown,
        cat_percentages=cat_percentages,
        recent_txns=recent_txns,
        cat_budgets=cat_budgets,
        unread_insights=unread_insights,
        txn_count=txn_count,
        health_score=health_score,
        health_status=health_status,
        health_status_class=health_status_class,
        health_tip=health_tip
    )

# ==========================================
# MODULE 3: EXPENSE MANAGEMENT
# ==========================================

@app.route('/expenses', methods=['GET'])
@login_required
def expenses():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    period_filter = request.args.get('period', 'This Month').strip()
    page = int(request.args.get('page', 1))
    per_page = 10

    sql = "SELECT * FROM expenses WHERE user_id = ?"
    params = [uid]

    if search_query:
        sql += " AND (title LIKE ? OR category LIKE ? OR notes LIKE ?)"
        wild = f"%{search_query}%"
        params.extend([wild, wild, wild])

    if category_filter and category_filter != 'All':
        sql += " AND category = ?"
        params.append(category_filter)

    # Order
    sql += " ORDER BY expense_date DESC, id DESC"

    all_rows = conn.execute(sql, params).fetchall()
    total_count = len(all_rows)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    paged_expenses = all_rows[offset:offset + per_page]

    # Categories and Payment methods for modals & filter
    categories = conn.execute("SELECT * FROM categories WHERE user_id = ?", (uid,)).fetchall()
    payment_methods = conn.execute("SELECT * FROM payment_methods WHERE user_id = ?", (uid,)).fetchall()

    conn.close()

    return render_template(
        'expenses.html',
        user=user,
        current_page='expenses',
        expenses=paged_expenses,
        categories=categories,
        payment_methods=payment_methods,
        total_count=total_count,
        page=page,
        total_pages=total_pages,
        search_query=search_query,
        category_filter=category_filter,
        period_filter=period_filter
    )

@app.route('/expenses/add', methods=['POST'])
@login_required
def add_expense():
    user = get_current_user()
    title = request.form.get('title', '').strip()
    amount = float(request.form.get('amount', 0))
    category = request.form.get('category', 'Others').strip()
    payment_method = request.form.get('payment_method', 'UPI').strip()
    date_val = request.form.get('expense_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')).strip()
    notes = request.form.get('notes', '').strip()

    if len(date_val) == 10:
        date_val += " " + datetime.now().strftime('%H:%M:%S')

    conn = get_db()
    conn.execute("""
        INSERT INTO expenses (user_id, title, amount, category, payment_method, expense_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user['id'], title, amount, category, payment_method, date_val, notes))

    # Check category budget alert
    cat = conn.execute("SELECT * FROM categories WHERE user_id = ? AND name = ?", (user['id'], category)).fetchone()
    if cat and cat['budget_limit'] > 0:
        spent = conn.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ? AND category = ?", (user['id'], category)).fetchone()[0] or 0.0
        if spent >= 0.8 * cat['budget_limit']:
            conn.execute("""
                INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
                VALUES (?, ?, ?, 'warning', 0, 'Just now')
            """, (user['id'], f"Budget Alert: {category}", f"You have reached {int((spent/cat['budget_limit'])*100)}% of your {category} budget. Remaining: ₹{max(0, cat['budget_limit']-spent):.0f}."))

    conn.commit()
    conn.close()

    flash("Expense added successfully!", "success")
    return redirect(request.referrer or url_for('expenses'))

@app.route('/expenses/edit/<int:exp_id>', methods=['POST'])
@login_required
def edit_expense(exp_id):
    user = get_current_user()
    title = request.form.get('title', '').strip()
    amount = float(request.form.get('amount', 0))
    category = request.form.get('category', 'Others').strip()
    payment_method = request.form.get('payment_method', 'UPI').strip()
    notes = request.form.get('notes', '').strip()

    conn = get_db()
    conn.execute("""
        UPDATE expenses
        SET title = ?, amount = ?, category = ?, payment_method = ?, notes = ?
        WHERE id = ? AND user_id = ?
    """, (title, amount, category, payment_method, notes, exp_id, user['id']))
    conn.commit()
    conn.close()

    flash("Expense updated successfully!", "success")
    return redirect(request.referrer or url_for('expenses'))

@app.route('/expenses/delete/<int:exp_id>', methods=['POST'])
@login_required
def delete_expense(exp_id):
    user = get_current_user()
    conn = get_db()
    conn.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (exp_id, user['id']))
    conn.commit()
    conn.close()
    flash("Expense removed.", "info")
    return redirect(request.referrer or url_for('expenses'))

# ==========================================
# MODULE 4: CATEGORY & PAYMENT MANAGEMENT
# ==========================================

@app.route('/categories-payments', methods=['GET'])
@login_required
def categories_payments():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    # Get categories with expense counts
    cats = conn.execute("""
        SELECT c.*, COUNT(e.id) as expense_count, COALESCE(SUM(e.amount), 0) as total_spent
        FROM categories c
        LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.id ASC
    """, (uid,)).fetchall()

    # Get payment methods with usage counts
    methods = conn.execute("""
        SELECT p.*, COUNT(e.id) as usage_count
        FROM payment_methods p
        LEFT JOIN expenses e ON e.payment_method = p.name AND e.user_id = p.user_id
        WHERE p.user_id = ?
        GROUP BY p.id
        ORDER BY p.is_default DESC, p.id ASC
    """, (uid,)).fetchall()

    conn.close()

    return render_template(
        'categories_payments.html',
        user=user,
        current_page='categories',
        categories=cats,
        payment_methods=methods
    )

@app.route('/categories/add', methods=['POST'])
@login_required
def add_category():
    user = get_current_user()
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', 'tag').strip()
    color = request.form.get('color', '#3b82f6').strip()
    budget_limit = float(request.form.get('budget_limit', 3000.0))

    if name:
        conn = get_db()
        conn.execute("""
            INSERT INTO categories (user_id, name, icon, color, budget_limit)
            VALUES (?, ?, ?, ?, ?)
        """, (user['id'], name, icon, color, budget_limit))
        conn.commit()
        conn.close()
        flash("Category created successfully!", "success")

    return redirect(url_for('categories_payments'))

@app.route('/categories/delete/<int:cat_id>', methods=['POST'])
@login_required
def delete_category(cat_id):
    user = get_current_user()
    conn = get_db()
    conn.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, user['id']))
    conn.commit()
    conn.close()
    flash("Category deleted.", "info")
    return redirect(url_for('categories_payments'))

@app.route('/payments/add', methods=['POST'])
@login_required
def add_payment_method():
    user = get_current_user()
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', 'credit-card').strip()

    if name:
        conn = get_db()
        conn.execute("""
            INSERT INTO payment_methods (user_id, name, icon, is_default)
            VALUES (?, ?, ?, 0)
        """, (user['id'], name, icon))
        conn.commit()
        conn.close()
        flash("Payment method added!", "success")

    return redirect(url_for('categories_payments'))

@app.route('/payments/delete/<int:pm_id>', methods=['POST'])
@login_required
def delete_payment_method(pm_id):
    user = get_current_user()
    conn = get_db()
    conn.execute("DELETE FROM payment_methods WHERE id = ? AND user_id = ?", (pm_id, user['id']))
    conn.commit()
    conn.close()
    flash("Payment method removed.", "info")
    return redirect(url_for('categories_payments'))

# ==========================================
# MODULE 5: BUDGET MANAGEMENT
# ==========================================

@app.route('/budget', methods=['GET', 'POST'])
@login_required
def budget():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    if request.method == 'POST':
        overall_budget = float(request.form.get('overall_budget', 20000.0))
        conn.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (overall_budget, uid))

        # Check for category limits updates
        for key, val in request.form.items():
            if key.startswith('cat_limit_'):
                cat_id = key.replace('cat_limit_', '')
                conn.execute("UPDATE categories SET budget_limit = ? WHERE id = ? AND user_id = ?", (float(val), cat_id, uid))

        conn.commit()
        flash("Budget goals updated successfully!", "success")
        return redirect(url_for('budget'))

    overall_budget = user['monthly_budget'] or 20000.0
    total_spent = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?", (uid,)).fetchone()[0]
    remaining = max(0.0, overall_budget - total_spent)
    overall_percent = min(100, round((total_spent / overall_budget) * 100)) if overall_budget > 0 else 0

    # Category budgets list
    cat_budgets = conn.execute("""
        SELECT c.*, COALESCE(SUM(e.amount), 0) as spent
        FROM categories c
        LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.budget_limit DESC
    """, (uid,)).fetchall()

    budget_items = []
    for cb in cat_budgets:
        limit = cb['budget_limit'] or 1.0
        spent = cb['spent']
        pct = min(100, round((spent / limit) * 100))
        if pct >= 80:
            status = "High"
            status_color = "#ef4444"
        elif pct >= 50:
            status = "Medium"
            status_color = "#f59e0b"
        else:
            status = "Good"
            status_color = "#10b981"

        budget_items.append({
            'id': cb['id'],
            'name': cb['name'],
            'icon': cb['icon'],
            'color': cb['color'],
            'limit': limit,
            'spent': spent,
            'percent': pct,
            'status': status,
            'status_color': status_color
        })

    conn.close()

    return render_template(
        'budget.html',
        user=user,
        current_page='budget',
        overall_budget=overall_budget,
        total_spent=total_spent,
        remaining=remaining,
        overall_percent=overall_percent,
        budget_items=budget_items
    )

# ==========================================
# MODULE 6: ANALYTICS & REPORTS
# ==========================================

@app.route('/analytics')
@login_required
def analytics():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    period = request.args.get('period', 'This Month')

    total_expenses = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?", (uid,)).fetchone()[0]
    total_txns = conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (uid,)).fetchone()[0]
    
    # Days with expenses
    distinct_days = conn.execute("SELECT COUNT(DISTINCT SUBSTR(expense_date, 1, 10)) FROM expenses WHERE user_id = ?", (uid,)).fetchone()[0] or 1
    avg_daily = total_expenses / max(1, distinct_days)

    # Categories Breakdown
    cat_breakdown = conn.execute("""
        SELECT category, SUM(amount) as cat_sum, COUNT(id) as count
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY cat_sum DESC
    """, (uid,)).fetchall()

    cat_labels = [r['category'] for r in cat_breakdown]
    cat_values = [r['cat_sum'] for r in cat_breakdown]
    cat_pcts = [round((r['cat_sum'] / max(1, total_expenses)) * 100) for r in cat_breakdown]

    # Daily Expenses Histogram (Days 1 to 31)
    daily_rows = conn.execute("""
        SELECT SUBSTR(expense_date, 9, 2) as day_num, SUM(amount) as day_sum
        FROM expenses
        WHERE user_id = ?
        GROUP BY day_num
        ORDER BY day_num ASC
    """, (uid,)).fetchall()

    daily_dict = {f"{int(r['day_num']):02d}": r['day_sum'] for r in daily_rows}
    daily_labels = [f"{d:02d}" for d in range(1, 32)]
    daily_values = [daily_dict.get(f"{d:02d}", 0) for d in range(1, 32)]

    # Monthly Trend Line
    trend_rows = conn.execute("""
        SELECT SUBSTR(expense_date, 1, 10) as edate, SUM(amount) as total
        FROM expenses
        WHERE user_id = ?
        GROUP BY edate
        ORDER BY edate ASC
    """, (uid,)).fetchall()
    trend_labels = [r['edate'][-5:] for r in trend_rows] or ["1 May", "15 May", "31 May"]
    trend_values = [r['total'] for r in trend_rows] or [1200, 2450, 1800]

    conn.close()

    return render_template(
        'analytics.html',
        user=user,
        current_page='analytics',
        period=period,
        total_expenses=total_expenses,
        total_txns=total_txns,
        avg_daily=avg_daily,
        cat_labels=cat_labels,
        cat_values=cat_values,
        cat_breakdown=cat_breakdown,
        cat_pcts=cat_pcts,
        daily_labels=daily_labels,
        daily_values=daily_values,
        trend_labels=trend_labels,
        trend_values=trend_values
    )

# ==========================================
# MODULE 7: NOTIFICATIONS & SPENDING INSIGHTS
# ==========================================

@app.route('/insights')
@login_required
def insights():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    notifs = conn.execute("""
        SELECT * FROM notifications
        WHERE user_id = ?
        ORDER BY is_read ASC, id DESC
    """, (uid,)).fetchall()

    conn.close()

    return render_template(
        'insights.html',
        user=user,
        current_page='insights',
        notifications=notifs
    )

@app.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    user = get_current_user()
    conn = get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user['id'],))
    conn.commit()
    conn.close()
    flash("All insights marked as read.", "success")
    return redirect(url_for('insights'))

# ==========================================
# MODULE 8: EXPENSE HISTORY, SEARCH & EXPORT
# ==========================================

@app.route('/history')
@login_required
def history():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    search_query = request.args.get('search', '').strip()
    category_filter = request.args.get('category', '').strip()
    payment_filter = request.args.get('payment', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10

    sql = "SELECT * FROM expenses WHERE user_id = ?"
    params = [uid]

    if search_query:
        sql += " AND (title LIKE ? OR category LIKE ? OR notes LIKE ?)"
        wild = f"%{search_query}%"
        params.extend([wild, wild, wild])

    if category_filter and category_filter != 'All Categories':
        sql += " AND category = ?"
        params.append(category_filter)

    if payment_filter and payment_filter != 'All Methods':
        sql += " AND payment_method = ?"
        params.append(payment_filter)

    sql += " ORDER BY expense_date DESC, id DESC"

    all_rows = conn.execute(sql, params).fetchall()
    total_count = len(all_rows)
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    paged_expenses = all_rows[offset:offset + per_page]

    # Overall Summary
    total_expenses = sum(r['amount'] for r in all_rows)
    highest_expense = max([r['amount'] for r in all_rows], default=0.0)
    lowest_expense = min([r['amount'] for r in all_rows], default=0.0)
    distinct_days = len(set(r['expense_date'][:10] for r in all_rows)) or 1
    avg_daily = total_expenses / distinct_days

    # Dropdown options
    categories = conn.execute("SELECT * FROM categories WHERE user_id = ?", (uid,)).fetchall()
    payment_methods = conn.execute("SELECT * FROM payment_methods WHERE user_id = ?", (uid,)).fetchall()

    conn.close()

    return render_template(
        'history.html',
        user=user,
        current_page='history',
        expenses=paged_expenses,
        categories=categories,
        payment_methods=payment_methods,
        total_count=total_count,
        total_expenses=total_expenses,
        highest_expense=highest_expense,
        lowest_expense=lowest_expense,
        avg_daily=avg_daily,
        page=page,
        total_pages=total_pages,
        search_query=search_query,
        category_filter=category_filter,
        payment_filter=payment_filter
    )

@app.route('/export/csv')
@login_required
def export_csv():
    user = get_current_user()
    conn = get_db()
    rows = conn.execute("""
        SELECT expense_date, title, category, payment_method, amount, notes
        FROM expenses
        WHERE user_id = ?
        ORDER BY expense_date DESC
    """, (user['id'],)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Payment Method", "Amount (INR)", "Notes"])

    for r in rows:
        writer.writerow([r['expense_date'], r['title'], r['category'], r['payment_method'], f"{r['amount']:.2f}", r['notes'] or ''])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=SpendWise_Expenses_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

@app.route('/export/pdf')
@login_required
def export_pdf():
    user = get_current_user()
    conn = get_db()
    rows = conn.execute("""
        SELECT expense_date, title, category, payment_method, amount, notes
        FROM expenses
        WHERE user_id = ?
        ORDER BY expense_date DESC
    """, (user['id'],)).fetchall()

    total_expenses = sum(r['amount'] for r in rows)
    highest_expense = max([r['amount'] for r in rows], default=0.0)
    distinct_days = len(set(r['expense_date'][:10] for r in rows)) or 1
    summary = {
        'total_expenses': total_expenses,
        'total_count': len(rows),
        'daily_avg': total_expenses / distinct_days,
        'highest_expense': highest_expense
    }
    conn.close()

    pdf_bytes = generate_expense_pdf(user['name'], rows, summary)

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment;filename=SpendWise_Report_{datetime.now().strftime('%Y%m%d')}.pdf"}
    )

# Quick theme toggle endpoint
@app.route('/api/toggle-theme', methods=['POST'])
@login_required
def toggle_theme():
    user = get_current_user()
    new_theme = 'light' if user['theme'] == 'dark' else 'dark'
    conn = get_db()
    conn.execute("UPDATE users SET theme = ? WHERE id = ?", (new_theme, user['id']))
    conn.commit()
    conn.close()
    return jsonify({"theme": new_theme})

if __name__ == '__main__':
    print("SpendWise server running at http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
