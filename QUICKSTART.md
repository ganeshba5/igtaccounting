# Quick Start Guide

## Initial Setup

### 1. Create Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize Database

The database will be automatically initialized when you start the backend server, but you can also initialize it manually:

```bash
cd backend
python database.py
```

**Note:** Make sure your virtual environment is activated.

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

## Running the Application

### Option 1: Using the Startup Scripts

**Terminal 1 - Start Backend:**
```bash
./start_backend.sh
```

**Terminal 2 - Start Frontend:**
```bash
./start_frontend.sh
```

### Option 2: Manual Start

**Terminal 1 - Start Backend:**
```bash
source venv/bin/activate  # Activate virtual environment first
cd backend
python app.py
```

Or use the startup script:
```bash
./start_backend.sh
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run dev
```

## Access the Application

Open your browser and navigate to: **http://localhost:3000**

## Getting Started Workflow

1. **Create a Business**
   - Click "+ New Business" on the home page
   - Enter a business name

2. **Set Up Chart of Accounts**
   - Click on your business
   - Go to "Chart of Accounts"
   - Add accounts using account codes and names
   - Select appropriate account types (Asset, Liability, Equity, Revenue, Expense)

3. **Add Bank Accounts**
   - Navigate to "Bank Accounts"
   - Add your business bank accounts with opening balances

4. **Add Credit Cards and Loans** (optional)
   - Add credit card accounts
   - Add loan accounts

5. **Record Transactions**
   - Go to "Transactions"
   - Create transactions using double-entry bookkeeping
   - Each transaction must have balanced debits and credits

6. **View Reports**
   - Navigate to "Reports"
   - View Profit & Loss (by year or custom date range)
   - View Balance Sheet (as of a specific date)

## Example Transaction

When recording a transaction, you need at least two lines:
- One account debited
- One account credited
- Total debits must equal total credits

Example: Paying rent from a bank account
- Debit: Rent Expense $1,000
- Credit: Bank Account $1,000

## Tips

- Start with setting up your Chart of Accounts before recording transactions
- The system uses double-entry bookkeeping - all transactions must balance
- Account codes should be unique per business
- Use meaningful account names and codes for easier reporting

