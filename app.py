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
from datetime import datetime, date, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, Response
)
from database import get_db, init_db, hash_pw, check_pw
from pdf_generator import generate_expense_pdf
from avatars import get_avatar_for_user, get_all_avatars, detect_gender

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
    user = None
    try:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        if user and (not user['avatar'] or 'photo-1534528741775' in (user['avatar'] or '')):
            try:
                auto_avatar = get_avatar_for_user(user['name'], user['email'])
                conn.execute("UPDATE users SET avatar = ? WHERE id = ?", (auto_avatar, user['id']))
                conn.commit()
                user = conn.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
            except Exception:
                pass
    finally:
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

        if user and check_pw(password, user['password_hash']):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            conn.close()

            flash("Welcome back!", "success")
            return redirect(url_for('dashboard'))
        else:
            conn.close()
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
        user_avatar = get_avatar_for_user(name, email)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, monthly_budget, avatar)
            VALUES (?, ?, ?, 0.0, ?)
        """, (name, email, hashed, user_avatar))
        new_user_id = cursor.lastrowid

        # Seed initial categories for new user (0.0 limit until user configures it)
        cats = [
            ("Food & Dining", "utensils", "#f97316", 0.0),
            ("Shopping", "shopping-bag", "#ec4899", 0.0),
            ("Transport", "car", "#3b82f6", 0.0),
            ("Bills & Utilities", "receipt", "#10b981", 0.0),
            ("Entertainment", "film", "#8b5cf6", 0.0),
            ("Education", "graduation-cap", "#6366f1", 0.0),
            ("Health", "heart-pulse", "#ef4444", 0.0),
            ("Others", "grid", "#64748b", 0.0)
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
        return redirect(url_for('dashboard'))

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
        monthly_budget = float(request.form.get('monthly_budget', 0.0) or 0.0)
        currency = request.form.get('currency', '₹')
        theme = request.form.get('theme', 'dark')
        avatar = request.form.get('avatar', '').strip()

        if not avatar:
            avatar = get_avatar_for_user(name, user['email'])

        conn.execute("""
            UPDATE users SET name = ?, monthly_budget = ?, currency = ?, theme = ?, avatar = ?
            WHERE id = ?
        """, (name, monthly_budget, currency, theme, avatar, user['id']))
        conn.commit()
        session['user_name'] = name
        flash("Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    # Stats for profile card
    total_spent = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?", (user['id'],)).fetchone()[0]
    total_txns = conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user['id'],)).fetchone()[0]
    conn.close()
    all_avatars = get_all_avatars()
    user_gender = detect_gender(user['name'])
    return render_template(
        'profile.html',
        user=user,
        current_page='profile',
        total_spent=total_spent,
        total_txns=total_txns,
        all_avatars=all_avatars,
        user_gender=user_gender
    )

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

    # Total expenses (All time)
    total_expenses = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?", (uid,)).fetchone()[0]

    # Today's expenses
    today_str = date.today().strftime('%Y-%m-%d')
    todays_expenses = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ? AND expense_date LIKE ?",
        (uid, f"{today_str}%")
    ).fetchone()[0]

    # Monthly budget and remaining
    monthly_budget = float(user['monthly_budget'] or 0.0)
    remaining_budget = max(0.0, monthly_budget - total_expenses) if monthly_budget > 0 else 0.0

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

    # Budget Progress items (categories with explicit user limits and spent)
    cat_budgets = conn.execute("""
        SELECT c.name, c.budget_limit, COALESCE(SUM(e.amount), 0) as spent, c.color
        FROM categories c
        LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id
        WHERE c.user_id = ? AND c.budget_limit > 0
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
    if monthly_budget > 0:
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
    else:
        health_score = 95 if total_expenses > 0 else 100
        health_status = "Budget Unset"
        health_status_class = "positive"
        health_tip = "Define your custom monthly budget in Budget Management to enable real-time tracking & threshold alerts."

    # Predictive Financial Runway & Velocity
    import calendar
    today = date.today()
    total_days_in_month = calendar.monthrange(today.year, today.month)[1]
    day_of_month = today.day
    days_remaining = max(1, total_days_in_month - day_of_month)
    daily_velocity = total_expenses / max(1, day_of_month)
    projected_month_end = total_expenses + (daily_velocity * days_remaining)
    projected_surplus = (monthly_budget - projected_month_end) if monthly_budget > 0 else 0

    # Subscriptions Summary
    subs_rows = conn.execute("SELECT * FROM subscriptions WHERE user_id = ? AND status = 'active'", (uid,)).fetchall()
    mrc_total = sum(
        r['amount'] if r['billing_cycle'] == 'monthly' else (r['amount']/12 if r['billing_cycle'] == 'yearly' else r['amount']*4.33)
        for r in subs_rows
    )

    # Savings Goals Summary
    goals_rows = conn.execute("SELECT * FROM savings_goals WHERE user_id = ? ORDER BY id DESC", (uid,)).fetchall()
    total_goals_saved = sum(g['current_amount'] for g in goals_rows)
    total_goals_target = sum(g['target_amount'] for g in goals_rows)
    goals_progress_pct = round((total_goals_saved / total_goals_target) * 100) if total_goals_target > 0 else 0

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
        health_tip=health_tip,
        days_remaining=days_remaining,
        daily_velocity=daily_velocity,
        projected_month_end=projected_month_end,
        projected_surplus=projected_surplus,
        mrc_total=mrc_total,
        active_subs_count=len(subs_rows),
        total_goals_saved=total_goals_saved,
        total_goals_target=total_goals_target,
        goals_progress_pct=goals_progress_pct,
        goals_rows=goals_rows[:3]
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
    budget_limit = float(request.form.get('budget_limit', 0.0) or 0.0)

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
        action = request.form.get('action', '')
        if action == 'single_category':
            cat_id = request.form.get('category_id')
            limit_raw = request.form.get('budget_limit', '0').strip()
            try:
                limit_val = max(0.0, float(limit_raw))
            except ValueError:
                limit_val = 0.0
            conn.execute("UPDATE categories SET budget_limit = ? WHERE id = ? AND user_id = ?", (limit_val, cat_id, uid))
            conn.commit()
            conn.close()
            flash("Category budget limit updated successfully!", "success")
            return redirect(url_for('budget'))

        # Standard form update (overall budget and category limits)
        overall_val = request.form.get('overall_budget', '0').strip()
        try:
            overall_budget = max(0.0, float(overall_val))
        except ValueError:
            overall_budget = 0.0
        conn.execute("UPDATE users SET monthly_budget = ? WHERE id = ?", (overall_budget, uid))

        # Check for category limits updates
        for key, val in request.form.items():
            if key.startswith('cat_limit_'):
                cat_id = key.replace('cat_limit_', '')
                try:
                    c_val = max(0.0, float(val.strip() or 0))
                except ValueError:
                    c_val = 0.0
                conn.execute("UPDATE categories SET budget_limit = ? WHERE id = ? AND user_id = ?", (c_val, cat_id, uid))

        conn.commit()
        flash("Budget goals updated successfully!", "success")
        return redirect(url_for('budget'))

    overall_budget = float(user['monthly_budget'] or 0.0)
    total_spent = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?", (uid,)).fetchone()[0]
    remaining = max(0.0, overall_budget - total_spent) if overall_budget > 0 else 0.0
    overall_percent = min(100, round((total_spent / overall_budget) * 100)) if overall_budget > 0 else 0

    # Category budgets list
    cat_budgets = conn.execute("""
        SELECT c.*, COALESCE(SUM(e.amount), 0) as spent
        FROM categories c
        LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.budget_limit DESC, c.name ASC
    """, (uid,)).fetchall()

    budget_items = []
    for cb in cat_budgets:
        limit = float(cb['budget_limit'] or 0.0)
        spent = float(cb['spent'] or 0.0)
        if limit > 0:
            pct = min(100, round((spent / limit) * 100))
            if spent > limit:
                status = "Exceeded"
                status_color = "#ef4444"
            elif pct >= 80:
                status = "High"
                status_color = "#ef4444"
            elif pct >= 50:
                status = "Medium"
                status_color = "#f59e0b"
            else:
                status = "Good"
                status_color = "#10b981"
        else:
            pct = 0
            status = "Not Set"
            status_color = "#64748b"

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

# ==========================================
# MODULE 9: RECURRING SUBSCRIPTIONS & BILLS
# ==========================================

@app.route('/subscriptions')
@login_required
def subscriptions():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    raw_subs = conn.execute("""
        SELECT * FROM subscriptions
        WHERE user_id = ?
        ORDER BY next_due_date ASC, id DESC
    """, (uid,)).fetchall()

    today_dt = date.today()
    subs = []
    monthly_cost = 0.0
    annual_cost = 0.0
    active_count = 0
    next_due_sub = None

    for r in raw_subs:
        d = dict(r)
        try:
            due_dt = datetime.strptime(d['next_due_date'], '%Y-%m-%d').date()
            days_diff = (due_dt - today_dt).days
        except Exception:
            days_diff = 30
        d['days_until'] = days_diff

        if d['status'] == 'active':
            active_count += 1
            if d['billing_cycle'] == 'monthly':
                m_amt = d['amount']
            elif d['billing_cycle'] == 'yearly':
                m_amt = d['amount'] / 12.0
            else:
                m_amt = d['amount'] * 4.33
            monthly_cost += m_amt
            annual_cost += m_amt * 12.0

            if next_due_sub is None and days_diff >= 0:
                next_due_sub = d

        subs.append(d)

    conn.close()
    return render_template(
        'subscriptions.html',
        user=user,
        current_page='subscriptions',
        subscriptions=subs,
        monthly_cost=monthly_cost,
        annual_cost=annual_cost,
        active_count=active_count,
        next_due_sub=next_due_sub
    )

@app.route('/subscriptions/add', methods=['POST'])
@login_required
def subscription_add():
    user = get_current_user()
    name = request.form.get('name', '').strip()
    try:
        amount = float(request.form.get('amount') or 0.0)
    except (ValueError, TypeError):
        amount = 0.0

    category = request.form.get('category', 'Others')
    billing_cycle = request.form.get('billing_cycle', 'monthly')
    next_due_date = request.form.get('next_due_date', date.today().strftime('%Y-%m-%d'))
    payment_method = request.form.get('payment_method', 'UPI')
    notes = request.form.get('notes', '').strip()

    if not name or amount <= 0:
        flash("Valid subscription name and positive amount required.", "danger")
        return redirect(url_for('subscriptions'))

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO subscriptions (user_id, name, amount, category, billing_cycle, next_due_date, payment_method, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user['id'], name, amount, category, billing_cycle, next_due_date, payment_method, notes))
        conn.commit()
        flash(f"Subscription '{name}' added successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error adding subscription: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('subscriptions'))

@app.route('/subscriptions/edit/<int:sub_id>', methods=['POST'])
@login_required
def subscription_edit(sub_id):
    user = get_current_user()
    name = request.form.get('name', '').strip()
    try:
        amount = float(request.form.get('amount') or 0.0)
    except (ValueError, TypeError):
        amount = 0.0

    category = request.form.get('category', 'Others')
    billing_cycle = request.form.get('billing_cycle', 'monthly')
    next_due_date = request.form.get('next_due_date', '')
    payment_method = request.form.get('payment_method', 'UPI')
    notes = request.form.get('notes', '').strip()

    conn = get_db()
    try:
        conn.execute("""
            UPDATE subscriptions
            SET name = ?, amount = ?, category = ?, billing_cycle = ?, next_due_date = ?, payment_method = ?, notes = ?
            WHERE id = ? AND user_id = ?
        """, (name, amount, category, billing_cycle, next_due_date, payment_method, notes, sub_id, user['id']))
        conn.commit()
        flash(f"Subscription '{name}' updated.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating subscription: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('subscriptions'))

@app.route('/subscriptions/delete/<int:sub_id>', methods=['GET', 'POST'])
@login_required
def subscription_delete(sub_id):
    user = get_current_user()
    conn = get_db()
    try:
        conn.execute("DELETE FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user['id']))
        conn.commit()
        flash("Subscription removed.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error deleting subscription: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('subscriptions'))

@app.route('/subscriptions/toggle-status/<int:sub_id>', methods=['GET', 'POST'])
@login_required
def subscription_toggle_status(sub_id):
    user = get_current_user()
    conn = get_db()
    try:
        sub = conn.execute("SELECT status, name FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user['id'])).fetchone()
        if sub:
            new_status = 'paused' if sub['status'] == 'active' else 'active'
            conn.execute("UPDATE subscriptions SET status = ? WHERE id = ?", (new_status, sub_id))
            conn.commit()
            flash(f"Subscription '{sub['name']}' is now {new_status}.", "info")
        else:
            flash("Subscription not found.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating status: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('subscriptions'))

@app.route('/subscriptions/log-as-expense/<int:sub_id>', methods=['GET', 'POST'])
@login_required
def subscription_log_expense(sub_id):
    user = get_current_user()
    conn = get_db()
    try:
        sub = conn.execute("SELECT * FROM subscriptions WHERE id = ? AND user_id = ?", (sub_id, user['id'])).fetchone()
        if not sub:
            # Fallback check if user owns it or if demo user
            sub = conn.execute("SELECT * FROM subscriptions WHERE id = ?", (sub_id,)).fetchone()
            if not sub:
                flash("Subscription not found.", "warning")
                return redirect(url_for('subscriptions'))

        try:
            amt = float(sub['amount'])
        except (ValueError, TypeError):
            amt = 0.0

        sub_name = str(sub['name'] or 'Subscription')
        sub_cat = str(sub['category'] or 'Bills & Utilities')
        sub_pm = str(sub['payment_method'] or 'UPI')
        sub_notes = str(sub['notes'] or 'Auto-logged subscription renewal')
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute("""
            INSERT INTO expenses (user_id, title, amount, category, payment_method, expense_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user['id'], f"{sub_name} (Subscription Renewal)", amt, sub_cat, sub_pm, now_str, sub_notes))

        try:
            curr_due_str = str(sub['next_due_date'] or '').strip()
            if ' ' in curr_due_str:
                curr_due_str = curr_due_str.split(' ')[0]
            if 'T' in curr_due_str:
                curr_due_str = curr_due_str.split('T')[0]
            curr_due = datetime.strptime(curr_due_str, '%Y-%m-%d').date()

            bcycle = str(sub['billing_cycle'] or 'monthly').lower()
            if bcycle == 'yearly':
                new_due = curr_due.replace(year=curr_due.year + 1)
            elif bcycle == 'weekly':
                new_due = curr_due + timedelta(days=7)
            else:
                month = curr_due.month + 1
                year = curr_due.year
                if month > 12:
                    month = 1
                    year += 1
                import calendar
                day = min(curr_due.day, calendar.monthrange(year, month)[1])
                new_due = date(year, month, day)
            new_due_str = new_due.strftime('%Y-%m-%d')
        except Exception:
            new_due_str = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')

        conn.execute("UPDATE subscriptions SET next_due_date = ? WHERE id = ?", (new_due_str, sub['id']))
        conn.commit()
        flash(f"Successfully recorded ₹{amt:,.0f} payment for {sub_name} into expenses! Next renewal due: {new_due_str}.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Could not log subscription expense: {str(e)}", "danger")
    finally:
        conn.close()
    return redirect(url_for('subscriptions'))


# ==========================================
# MODULE 10: SAVINGS GOALS & TARGETS
# ==========================================

@app.route('/savings-goals')
@login_required
def savings_goals():
    user = get_current_user()
    conn = get_db()
    uid = user['id']

    raw_goals = conn.execute("""
        SELECT * FROM savings_goals
        WHERE user_id = ?
        ORDER BY status ASC, id DESC
    """, (uid,)).fetchall()

    goals = []
    total_saved = 0.0
    total_target = 0.0
    achieved_count = 0
    closest_goal = None

    for r in raw_goals:
        d = dict(r)
        pct = round((d['current_amount'] / d['target_amount']) * 100) if d['target_amount'] > 0 else 0
        d['pct'] = pct
        total_saved += d['current_amount']
        total_target += d['target_amount']
        if pct >= 100:
            achieved_count += 1
        elif closest_goal is None or pct > closest_goal['pct']:
            closest_goal = d
        goals.append(d)

    overall_pct = round((total_saved / total_target) * 100) if total_target > 0 else 0
    remaining_target = max(0.0, total_target - total_saved)

    conn.close()
    return render_template(
        'savings_goals.html',
        user=user,
        current_page='savings_goals',
        goals=goals,
        total_saved=total_saved,
        total_target=total_target,
        remaining_target=remaining_target,
        overall_pct=overall_pct,
        achieved_count=achieved_count,
        closest_goal=closest_goal
    )

@app.route('/savings-goals/add', methods=['POST'])
@login_required
def savings_goal_add():
    user = get_current_user()
    title = request.form.get('title', '').strip()
    try:
        target_amount = float(request.form.get('target_amount') or 0.0)
    except (ValueError, TypeError):
        target_amount = 0.0

    try:
        initial_amount = float(request.form.get('initial_amount') or 0.0)
    except (ValueError, TypeError):
        initial_amount = 0.0

    category = request.form.get('category', 'General')
    color = request.form.get('color', '#10b981')
    target_date = request.form.get('target_date', '')

    icon_map = {
        'Emergency': 'shield-halved',
        'Gadgets': 'laptop-code',
        'Travel': 'plane-departure',
        'Vehicle': 'car',
        'Home': 'house',
        'Investments': 'chart-line',
        'General': 'bullseye'
    }
    icon = icon_map.get(category, 'bullseye')

    if not title or target_amount <= 0:
        flash("Valid goal title and positive target required.", "danger")
        return redirect(url_for('savings_goals'))

    status = 'achieved' if initial_amount >= target_amount else 'in_progress'

    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO savings_goals (user_id, title, target_amount, current_amount, target_date, category, color, icon, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user['id'], title, target_amount, initial_amount, target_date, category, color, icon, status))
        goal_id = cursor.lastrowid

        if initial_amount > 0:
            cursor.execute("""
                INSERT INTO savings_contributions (goal_id, user_id, amount, contribution_date, notes)
                VALUES (?, ?, ?, ?, 'Initial seed deposit')
            """, (goal_id, user['id'], initial_amount, date.today().strftime('%Y-%m-%d')))

        conn.commit()
        flash(f"Goal '{title}' created successfully!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error creating goal: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('savings_goals'))

@app.route('/savings-goals/edit/<int:goal_id>', methods=['POST'])
@login_required
def savings_goal_edit(goal_id):
    user = get_current_user()
    title = request.form.get('title', '').strip()
    try:
        target_amount = float(request.form.get('target_amount') or 0.0)
    except (ValueError, TypeError):
        target_amount = 0.0

    category = request.form.get('category', 'General')
    color = request.form.get('color', '#10b981')
    target_date = request.form.get('target_date', '')

    conn = get_db()
    try:
        conn.execute("""
            UPDATE savings_goals
            SET title = ?, target_amount = ?, category = ?, color = ?, target_date = ?
            WHERE id = ? AND user_id = ?
        """, (title, target_amount, category, color, target_date, goal_id, user['id']))
        conn.commit()
        flash(f"Goal '{title}' updated.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating goal: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('savings_goals'))

@app.route('/savings-goals/delete/<int:goal_id>', methods=['GET', 'POST'])
@login_required
def savings_goal_delete(goal_id):
    user = get_current_user()
    conn = get_db()
    try:
        conn.execute("DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user['id']))
        conn.execute("DELETE FROM savings_contributions WHERE goal_id = ? AND user_id = ?", (goal_id, user['id']))
        conn.commit()
        flash("Goal removed.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error removing goal: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('savings_goals'))

@app.route('/savings-goals/deposit/<int:goal_id>', methods=['GET', 'POST'])
@login_required
def savings_goal_deposit(goal_id):
    user = get_current_user()
    try:
        amount = float(request.form.get('amount') or 0.0)
    except (ValueError, TypeError):
        amount = 0.0

    notes = request.form.get('notes', 'Direct goal deposit').strip()

    if amount <= 0:
        flash("Please enter a positive deposit amount.", "danger")
        return redirect(url_for('savings_goals'))

    conn = get_db()
    try:
        goal = conn.execute("SELECT * FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user['id'])).fetchone()
        if not goal:
            goal = conn.execute("SELECT * FROM savings_goals WHERE id = ?", (goal_id,)).fetchone()

        if goal:
            curr_amt = float(goal['current_amount'] or 0.0)
            target_amt = float(goal['target_amount'] or 0.0)
            new_amt = curr_amt + amount
            new_status = 'achieved' if new_amt >= target_amt else 'in_progress'

            conn.execute("UPDATE savings_goals SET current_amount = ?, status = ? WHERE id = ?", (new_amt, new_status, goal['id']))
            conn.execute("""
                INSERT INTO savings_contributions (goal_id, user_id, amount, contribution_date, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (goal['id'], user['id'], amount, date.today().strftime('%Y-%m-%d'), notes))
            conn.commit()

            if new_status == 'achieved' and goal['status'] != 'achieved':
                flash(f"🎉 CONGRATULATIONS! You achieved your milestone goal '{goal['title']}'!", "success")
            else:
                flash(f"Successfully deposited ₹{amount:,.0f} to '{goal['title']}'! Current progress: ₹{new_amt:,.0f}.", "success")
        else:
            flash("Savings goal not found.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Error depositing to goal: {str(e)}", "danger")
    finally:
        conn.close()

    return redirect(url_for('savings_goals'))


# ==========================================
# SMART CSV BANK STATEMENT IMPORT ENGINE
# ==========================================

def auto_detect_category(text: str) -> tuple[str, str]:
    t = text.lower()
    if any(k in t for k in ['swiggy', 'zomato', 'cafe', 'coffee', 'starbucks', 'restaurant', 'food', 'mcdonald', 'burger', 'pizza', 'domino', 'dine', 'lunch', 'dinner', 'bakery']):
        cat = 'Food & Dining'
    elif any(k in t for k in ['amazon', 'flipkart', 'myntra', 'zara', 'nike', 'shopping', 'retail', 'mart', 'grocer', 'store', 'cloth', 'blinkit', 'zepto', 'instamart']):
        cat = 'Shopping'
    elif any(k in t for k in ['uber', 'ola', 'rapido', 'fuel', 'petrol', 'diesel', 'shell', 'irctc', 'train', 'metro', 'bus', 'flight', 'indigo', 'airline', 'toll', 'fastag']):
        cat = 'Transport'
    elif any(k in t for k in ['netflix', 'spotify', 'hotstar', 'prime', 'cinema', 'pvr', 'movie', 'theatre', 'gaming', 'steam', 'playstation', 'concert', 'event']):
        cat = 'Entertainment'
    elif any(k in t for k in ['electricity', 'water', 'gas', 'broadband', 'wifi', 'airtel', 'jio', 'vi', 'bill', 'recharge', 'power', 'bescom', 'tneb', 'aws', 'cloud', 'github']):
        cat = 'Bills & Utilities'
    elif any(k in t for k in ['hospital', 'pharmacy', 'medicine', 'apollo', 'doctor', 'clinic', 'dentist', 'health', 'cult', 'gym', 'fitness', 'opticals']):
        cat = 'Health'
    elif any(k in t for k in ['udemy', 'coursera', 'course', 'book', 'education', 'school', 'college', 'tuition', 'exam', 'cert']):
        cat = 'Education'
    else:
        cat = 'Others'

    if any(k in t for k in ['upi', 'gpay', 'phonepe', 'paytm']):
        pm = 'UPI'
    elif any(k in t for k in ['atm', 'cash', 'wdl']):
        pm = 'Cash'
    elif any(k in t for k in ['credit card', 'cc']):
        pm = 'Credit Card'
    elif any(k in t for k in ['debit card', 'dc', 'pos']):
        pm = 'Debit Card'
    elif any(k in t for k in ['neft', 'rtgs', 'imps', 'transfer', 'ach']):
        pm = 'Bank Transfer'
    else:
        pm = 'UPI'

    return cat, pm

@app.route('/import/csv', methods=['POST'])
@login_required
def import_csv():
    user = get_current_user()
    if 'statement_file' not in request.files:
        flash("No CSV file selected.", "danger")
        return redirect(url_for('expenses'))

    file = request.files['statement_file']
    if not file or file.filename == '':
        flash("No file selected for statement import.", "danger")
        return redirect(url_for('expenses'))

    try:
        content = file.stream.read().decode('utf-8-sig', errors='replace')
        stream = io.StringIO(content)
        reader = csv.reader(stream)
        rows = list(reader)

        if not rows:
            flash("The uploaded CSV statement file is empty.", "danger")
            return redirect(url_for('expenses'))

        header = [col.strip().lower() for col in rows[0]]
        
        date_idx = -1
        desc_idx = -1
        amount_idx = -1
        cat_idx = -1
        pm_idx = -1

        for idx, col in enumerate(header):
            if any(k in col for k in ['date', 'txn date', 'transaction date', 'value date']):
                if date_idx == -1: date_idx = idx
            elif any(k in col for k in ['desc', 'narration', 'particulars', 'title', 'merchant', 'payee']):
                if desc_idx == -1: desc_idx = idx
            elif any(k in col for k in ['amount', 'debit', 'spent', 'withdrawal', 'cost']):
                if amount_idx == -1: amount_idx = idx
            elif 'category' in col:
                cat_idx = idx
            elif any(k in col for k in ['payment', 'method', 'mode', 'channel']):
                pm_idx = idx

        if date_idx == -1: date_idx = 0
        if desc_idx == -1: desc_idx = 1 if len(header) > 1 else 0
        if amount_idx == -1: amount_idx = 2 if len(header) > 2 else -1

        if amount_idx == -1:
            flash("Could not detect Amount column in your CSV statement.", "danger")
            return redirect(url_for('expenses'))

        conn = get_db()
        imported_count = 0
        auto_cat_count = 0

        for r in rows[1:]:
            if len(r) <= max(date_idx, desc_idx, amount_idx):
                continue
            
            raw_title = r[desc_idx].strip() if desc_idx < len(r) else 'Imported Expense'
            raw_amt_str = r[amount_idx].replace('₹', '').replace('$', '').replace(',', '').strip()
            if not raw_title or not raw_amt_str:
                continue

            try:
                amt = abs(float(raw_amt_str))
                if amt <= 0:
                    continue
            except ValueError:
                continue

            raw_date = r[date_idx].strip()
            formatted_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d/%m/%y'):
                try:
                    d_parsed = datetime.strptime(raw_date, fmt)
                    formatted_date = d_parsed.strftime('%Y-%m-%d 12:00:00')
                    break
                except ValueError:
                    pass

            auto_cat, auto_pm = auto_detect_category(raw_title)

            cat = r[cat_idx].strip() if (cat_idx != -1 and cat_idx < len(r) and r[cat_idx].strip()) else auto_cat
            pm = r[pm_idx].strip() if (pm_idx != -1 and pm_idx < len(r) and r[pm_idx].strip()) else auto_pm
            if cat == auto_cat:
                auto_cat_count += 1

            conn.execute("""
                INSERT INTO expenses (user_id, title, amount, category, payment_method, expense_date, notes)
                VALUES (?, ?, ?, ?, ?, ?, 'Imported via Bank Statement CSV Parser')
            """, (user['id'], raw_title, amt, cat, pm, formatted_date))
            imported_count += 1

        conn.commit()
        conn.close()

        if imported_count > 0:
            flash(f"⚡ Successfully imported {imported_count} transactions! Auto-categorized {auto_cat_count} entries using intelligent heuristics.", "success")
        else:
            flash("No valid expense rows could be parsed from the CSV statement.", "warning")

    except Exception as e:
        flash(f"Error processing CSV statement: {str(e)}", "danger")

    return redirect(url_for('expenses'))

@app.route('/import/template')
@login_required
def import_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Amount", "Category", "Payment Method"])
    writer.writerow(["2026-11-01", "Starbucks Coffee & Croissant", "380.00", "Food & Dining", "UPI"])
    writer.writerow(["2026-11-02", "Uber Ride to Tech Park", "240.00", "Transport", "UPI"])
    writer.writerow(["2026-11-02", "Amazon Pantry Essentials", "1450.00", "Shopping", "Credit Card"])
    writer.writerow(["2026-11-03", "Airtel Broadband Fiber", "999.00", "Bills & Utilities", "UPI"])
    writer.writerow(["2026-11-03", "Cult.fit Monthly Gym Pass", "1800.00", "Health", "Debit Card"])
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=spendwise_sample_statement.csv"}
    )

if __name__ == '__main__':
    print("SpendWise server running at http://127.0.0.1:5000")
    app.run(debug=True, host='127.0.0.1', port=5000)
