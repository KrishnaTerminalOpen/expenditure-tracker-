# SpendWise - Intelligent Personal Expense Tracker & Financial Management

A full-stack, enterprise-grade personal expense management web application built entirely in **Python**. SpendWise provides end-to-end financial tracking, category budget thresholds, monthly spending trends, automated budget health notifications, and instant PDF/CSV auditing reports.

![SpendWise Architecture](https://raw.githubusercontent.com/KrishnaTerminalOpen/expenditure-tracker-/main/static/css/index.css)

---

## 🌟 Key Modules (Matching High-Fidelity UI Specification)

1. **Authentication & Profile (Module 1)**:
   - Secure login and registration powered by **bcrypt** password hashing.
   - Profile management with customizable monthly spending limits and currency settings.
   - Demo credentials pre-configured for instant review.

2. **Dashboard & Key Performance Indicators (Module 2)**:
   - 4 Real-time KPI summary cards: Total Expenses (This Month), Today's Spending, Remaining Budget, and Highest Category.
   - Interactive Spline line chart showcasing daily spending trajectories.
   - Category distribution doughnut chart with percentage breakdown.
   - Recent transaction audit feed, Category budget progress bars, and spending insight recommendations.

3. **Expense Management (Module 3)**:
   - Complete CRUD operations (Create, Read, Update, Delete) for individual transactions.
   - Live multi-keyword search and category filtering.
   - Interactive expense modals with instant date/time capture.

4. **Category & Payment Gateway Management (Module 4)**:
   - Category cards with individual monthly expenditure limits, icon indicators, and spend analytics.
   - Support for multiple payment methods: UPI, Cash, Credit Card, Debit Card, Bank Transfer, and Digital Wallets.

5. **Budget Management & Threshold Alarms (Module 5)**:
   - Overall monthly budget progress indicator with dynamic percentage alerts.
   - Category budget tracking with color-coded risk assessment tags (`Good`, `Medium`, `High`).

6. **Analytics & Reports (Module 6)**:
   - Period-filtered financial analytics (This Month, This Year, Custom).
   - Daily spending histogram (Days 1 to 31) to identify peak spending dates.
   - Average daily spending rate calculations and month-over-month variances.

7. **Smart Notifications & Spending Insights (Module 7)**:
   - Automated financial alerts triggered when category limits hit 80%+.
   - Insight cards categorized into budget alerts, saving tips, and behavioral trends.

8. **Expense History, Search & Export Engine (Module 8)**:
   - Full ledger audit with search and filtering by category, payment method, and date ranges.
   - **CSV Export**: Clean spreadsheet export with custom headers and timestamps.
   - **PDF Report Engine**: Native PDF generator utilizing **ReportLab** with formatted financial tables and KPI summaries.

---

## 🛠️ Technology Stack (100% Python Native)

- **Backend**: Python 3.12, Flask 3.1.x
- **Database**: SQLite3 with normalized relational schema
- **Security**: Bcrypt cryptographic hashing for passwords
- **PDF Engine**: ReportLab 5.x & Pillow
- **Frontend / UI**: Clean semantic HTML5, Vanilla CSS Glassmorphism Design System, Chart.js for data visualization, and FontAwesome 6 icons.

---

## 🚀 Quickstart Guide

### 1. Clone the repository
```bash
git clone https://github.com/KrishnaTerminalOpen/expenditure-tracker-.git
cd expenditure-tracker-
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize the database
```bash
python database.py
```

### 4. Run the application
```bash
python app.py
```
Open your browser and navigate to `http://127.0.0.1:5000`.

### 🔑 Demo Credentials
- **Email**: `krishna@example.com`
- **Password**: `password123`

---

## 📂 Project Directory Structure

```
spendwise-antigravity/
├── app.py                  # Main Flask application & routes (Modules 1-8)
├── database.py             # SQLite schema, migrations & seed dataset
├── pdf_generator.py        # ReportLab PDF report generation engine
├── requirements.txt        # Python package dependencies
├── README.md               # Comprehensive documentation & setup guide
├── .gitignore              # Git ignore rules for Python & environments
├── templates/
│   ├── base.html           # Master layout with sidebar & top navbar
│   ├── auth.html           # Module 1: Login & Registration
│   ├── dashboard.html      # Module 2: Analytics & KPI Dashboard
│   ├── expenses.html       # Module 3: Expense Management (CRUD)
│   ├── categories_payments.html # Module 4: Categories & Payment Methods
│   ├── budget.html         # Module 5: Budget Goals & Limits
│   ├── analytics.html      # Module 6: Historical Analytics & Histograms
│   ├── insights.html       # Module 7: Notifications & Spending Insights
│   ├── history.html        # Module 8: Transaction Ledger & Data Exports
│   └── profile.html        # User Profile & Preferences
└── static/
    └── css/
        └── index.css       # Complete dark-mode FinTech design system
```

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
