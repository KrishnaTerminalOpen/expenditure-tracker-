# SpendWise - Intelligent Personal Expense Tracker & Financial OS

A full-stack, enterprise-grade personal expense and financial intelligence web application built entirely in **Python**. SpendWise provides end-to-end capital tracking, category budget thresholds, monthly spending trends, automated budget health notifications, recurring subscription management, milestone savings targets, smart bank statement parsing, and instant PDF/CSV auditing reports.

---

## 🌟 Key Modules & Enterprise Architecture

1. **Authentication & Profile (Module 1)**:
   - Secure login and registration powered by **bcrypt** cryptographic password hashing.
   - **⚡ 1-Click Instant Demo Login**: Instant one-click authentication for rapid demonstration.
   - Password reveal/hide toggle, device persistence, and profile preferences.

2. **Dashboard & Predictive Intelligence (Module 2)**:
   - 4 Real-time KPI summary cards: Total Expenses, Today's Spending, Remaining Budget, and Highest Category.
   - **AI Predictive Month-End Runway**: Computes daily spending velocity and forecasts month-end total spend and surplus/deficit buffers.
   - Interactive Spline line chart showcasing daily spending trajectories and Category Doughnut chart with live distribution.
   - Recent transaction feed, category budget pacing bars, and financial health score gauge.

3. **Expense Management (Module 3)**:
   - Complete CRUD operations (Create, Read, Update, Delete) for individual transactions.
   - Multi-keyword live search, category filters, and period filters.
   - Modal date/time capture and receipt details.

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

9. **Recurring Subscriptions & Fixed Bills Hub (Module 9)**:
   - Monitor memberships, cloud subscriptions (AWS, GitHub), streaming (Netflix, Spotify), and utilities (Airtel Fiber, Gym).
   - Monthly Recurring Cost (MRC) and Projected Annualized Cost calculations.
   - Renewal countdown pills ("Due in 4 days", "Due today") and Pause/Resume states.
   - **⚡ 1-Click Log as Expense**: Automatically records the renewal in your expense ledger and advances the due date.

10. **Financial Savings Goals & Milestones Hub (Module 10)**:
    - Set target capital milestones (Emergency Fund, MacBook Pro, Vacation, Real Estate).
    - Milestone progress bars with dynamic completion percentages (`25%`, `50%`, `75%`, `100%`).
    - **Interactive Goal Deposits**: Allocate salary and savings with full contribution audit logging.
    - Milestone celebration with audio chimes and confetti bursts upon 100% completion.

11. **Smart Bank Statement (CSV) Import Engine**:
    - Upload bank statements or spreadsheet CSVs directly from your bank.
    - Automated keyword heuristics that classify merchants (Swiggy, Amazon, Uber, Netflix, Electricity) into their correct categories and payment methods.
    - Built-in downloadable sample CSV statement template.

---

## 🛠️ Technology Stack (100% Python Native)

- **Backend**: Python 3.12, Flask 3.1.x
- **Database**: SQLite3 with normalized relational schema (WAL mode)
- **Security**: Bcrypt cryptographic hashing for passwords
- **PDF Engine**: ReportLab 5.x & Pillow
- **Frontend / UI**: Modern Glassmorphism FinTech Design System (`Outfit`, `Plus Jakarta Sans`, `JetBrains Mono`), Chart.js visualizations, and FontAwesome 6 icons.

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
*(Or click the **1-Click Demo Login** button on the sign-in page)*

---

## 📂 Project Directory Structure

```
spendwise-antigravity/
├── app.py                      # Main Flask application & routes (Modules 1-10 + CSV Import)
├── database.py                 # SQLite schema, migrations & seed dataset
├── pdf_generator.py            # ReportLab PDF report generation engine
├── requirements.txt            # Python package dependencies
├── README.md                   # Comprehensive documentation & setup guide
├── .gitignore                  # Git ignore rules for Python & environments
├── templates/
│   ├── base.html               # Master layout with sidebar & top navbar & command palette
│   ├── auth.html               # Module 1: Login & Registration (1-Click Demo)
│   ├── dashboard.html          # Module 2: Analytics & KPI Dashboard + Predictive Runway
│   ├── expenses.html           # Module 3: Expense Management (CRUD + Statement Import)
│   ├── categories_payments.html# Module 4: Categories & Payment Methods
│   ├── budget.html             # Module 5: Budget Goals & Limits
│   ├── analytics.html          # Module 6: Historical Analytics & Histograms
│   ├── insights.html           # Module 7: Notifications & Spending Insights
│   ├── history.html            # Module 8: Transaction Ledger & Data Exports
│   ├── subscriptions.html      # Module 9: Recurring Subscriptions & Fixed Bills Hub
│   ├── savings_goals.html      # Module 10: Financial Savings Goals & Milestones Hub
│   └── profile.html            # User Profile & Preferences
└── static/
    └── css/
        └── index.css           # Complete dark-mode FinTech design system
```

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
