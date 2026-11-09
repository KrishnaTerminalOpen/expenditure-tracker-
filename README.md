# SpendWise - Intelligent Financial Operating System & Expense Tracker

[![Live Demo](https://img.shields.io/badge/Live%20Demo-myspendwise--app.vercel.app-f97316?style=for-the-badge&logo=vercel)](https://myspendwise-app.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.12-3b82f6?style=for-the-badge&logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.x-10b981?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![Google Sign-In](https://img.shields.io/badge/Google%20Auth-Identity%20Services-ea4335?style=for-the-badge&logo=google)](https://developers.google.com/identity)

A full-stack, enterprise-grade personal expense intelligence platform and financial operating system built with **Python (Flask)** and modern glassmorphic web standards. SpendWise delivers real-time expense tracking, automated category pacing, Google OAuth 2.0 authentication, predictive month-end runway modeling, recurring subscription auditing, milestone savings targets, automated bank statement categorization, and instant PDF audit reports.

---

## 🌐 Live Application
- **Production URL**: [https://myspendwise-app.vercel.app](https://myspendwise-app.vercel.app)
- **Repository**: [https://github.com/KrishnaTerminalOpen/expenditure-tracker-](https://github.com/KrishnaTerminalOpen/expenditure-tracker-)

---

## 🌟 Core Features & Modules

### 1. 🔐 Authentication & Onboarding
- **Real-Time "Sign in with Google"**: Seamless 1-click Google OAuth authentication powered by Google Identity Services (`https://accounts.google.com/gsi/client`) and cryptographically verified on the backend with official `google-auth` (`verify_oauth2_token`).
- **Standard Email & Password Auth**: Bank-grade **Bcrypt** cryptographic password hashing with password visibility toggling and persistent encrypted sessions.
- **Compulsory Budget Onboarding**: New users automatically land on the expense onboarding page and must establish a monthly spending allocation before advancing into the dashboard.
- **Enterprise Data Privacy**: Strict multi-tenant user data isolation ensures every user accesses only their own financial records.

### 2. 📊 Predictive Financial Intelligence Dashboard
- **Real-Time KPIs**: Total Expenses (all time), Today's Spend, Remaining Monthly Allocation, and Highest Category.
- **Predictive Month-End Runway**: Calculates daily spending velocity ($V = \frac{\text{Spend}}{\text{Day}}$) to project month-end expenditure and calculate surplus/deficit buffers.
- **Dynamic Financial Health Score (0–100)**: Real-time health gauge evaluating current burn rate versus budget targets.
- **Visual Analytics**: Interactive Spline line charts tracking daily trajectory and Category Doughnut distribution powered by **Chart.js**.

### 3. 💳 Expense Ledger & Smart Statement Parser
- **Transaction Ledger**: Complete CRUD operations for all expenses with category, payment gateway, date/time, and notes.
- **Show More Expandable Notes**: Long transaction descriptions automatically truncate with an interactive "Show More / Show Less" toggle to maintain clean card layouts.
- **Bank Statement CSV Parser**: Upload bank statements (CSV format). Intelligent regex/keyword heuristics automatically categorize merchants (e.g., Swiggy, Amazon, Uber, Netflix, Electricity) to their appropriate categories and payment methods.

### 4. 🏷️ Category Pacing & Payment Methods
- **Category Pacing Gauges**: Individual category limits with spent-versus-allocated progress bars and risk indicators (`Good`, `Medium`, `High`).
- **Multi-Gateway Tracking**: UPI, Credit Cards, Debit Cards, Cash, Bank Transfers, and Digital Wallets.

### 5. 🔄 Recurring Subscriptions & Fixed Bills Hub
- **Subscription Tracker**: Monitor SaaS memberships, utilities, and streaming services (Netflix, Spotify, AWS, Gym).
- **Metric Insights**: Monthly Recurring Cost (MRC) and Projected Annualized Cost calculations.
- **Active Renewal Alarms**: Dynamic renewal pills ("Due today", "Due in 3 days") with 1-click **Log as Expense** auto-recording.

### 6. 🎯 Financial Savings Goals & Milestones
- **Target Milestones**: Establish target funds for emergencies, gadgets, travel, and real estate.
- **Deposit Contributions**: Interactive goal deposits with full contribution ledger audit histories.
- **Visual Milestones**: Interactive progress tracking with audio cues and celebration confetti upon 100% completion.

### 7. 📄 Audit Reports & Exports
- **Native PDF Engine**: Generates formatted, branded financial audit reports using Python **ReportLab**.
- **CSV Data Exports**: Timestamped spreadsheet exports filtered by date ranges and categories.

### 8. 👤 User Profile, Custom Avatars & Danger Zone
- **Smart Avatar Generation**: Automatic gender and name-based SVG avatar assignments.
- **Interactive Avatar Gallery**: Select from curated boy & girl avatars or provide custom image links.
- **⚠️ Danger Zone (Account Deletion)**: Secure option to permanently wipe all account records (expenses, categories, subscriptions, goals) with an intentional confirmation check (requires typing `DELETE`).

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.12, Flask 3.1.x, Jinja2 Templates |
| **Authentication** | Google Identity Services (GIS), `google-auth`, `bcrypt` |
| **Database** | SQLite3 with WAL persistence (Serverless resilient) |
| **PDF Generation** | ReportLab 5.x, Pillow |
| **Frontend** | HTML5, CSS3, Modern Glassmorphic FinTech UI System, JavaScript (Vanilla ES6+) |
| **Charts & Icons** | Chart.js, FontAwesome 6 Pro, Google Fonts (`Outfit`, `Plus Jakarta Sans`, `JetBrains Mono`) |
| **Deployment** | Vercel Serverless Functions, Git CI/CD |

---

## 🚀 Local Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/KrishnaTerminalOpen/expenditure-tracker-.git
cd expenditure-tracker-
```

### 2. Set up virtual environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the root directory (or copy from `.env.example`):
```env
# Flask Application Secret Key (for session cryptography)
FLASK_SECRET_KEY=your-super-secret-key-here

# Google OAuth 2.0 Web Client ID
# Obtain from: https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your-google-client-id-here.apps.googleusercontent.com
```

### 5. Initialize the database
```bash
python database.py
```

### 6. Run the application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📂 Project Structure

```
spendwise-antigravity/
├── app.py                      # Core Flask application, auth, API & view routes
├── database.py                 # SQLite schema, migrations & resilient connection helpers
├── pdf_generator.py            # ReportLab PDF report generation engine
├── avatars.py                  # Procedural & gallery avatar generator with gender heuristics
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment variable template
├── .gitignore                  # Git ignore specifications
├── README.md                   # Comprehensive documentation & setup guide
├── templates/
│   ├── base.html               # Master layout with sidebar, navbar & quick-actions
│   ├── auth.html               # Module 1: Login & Registration (Google Auth & Email)
│   ├── dashboard.html          # Module 2: KPI Dashboard & Predictive Velocity Runway
│   ├── expenses.html           # Module 3: Expense Ledger & Bank Statement CSV Parser
│   ├── categories_payments.html# Module 4: Category Pacing & Payment Methods
│   ├── budget.html             # Module 5: Monthly Budget Allocations & Thresholds
│   ├── analytics.html          # Module 6: Historical Analytics & Spending Histograms
│   ├── insights.html           # Module 7: Smart Spending Notifications & Tips
│   ├── history.html            # Module 8: Transaction Ledger, Search & CSV/PDF Exports
│   ├── subscriptions.html      # Module 9: Recurring Subscriptions & Fixed Bills Hub
│   ├── savings_goals.html      # Module 10: Financial Savings Goals & Milestones Hub
│   └── profile.html            # Profile Settings, Avatar Picker & Danger Zone Deletion
└── static/
    └── css/
        └── index.css           # Glassmorphism FinTech design system & animations
```

---

## 🔒 Security Best Practices
- **Never hardcode secrets**: Secret keys and client credentials reside in `.env` and environment variables.
- **Token Verification**: Google OAuth ID tokens are verified cryptographically via Google's public certs (`verify_oauth2_token`).
- **Data Protection**: Passwords hashed with salt via `bcrypt`.
- **Accidental Deletion Protection**: Account deletion requires explicit typing of `DELETE` before execution.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
