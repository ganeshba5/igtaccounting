# Business Accounting Application

A comprehensive multi-business accounting system with support for bank accounts, credit cards, loans, chart of accounts, transactions, and financial reports.

## Features

- **Multiple Businesses**: Support for managing multiple businesses in a single system
- **Bank Accounts**: Track multiple bank accounts per business
- **Credit Cards**: Manage credit card accounts
- **Loans**: Track loan accounts with principal, balance, and interest rates
- **Chart of Accounts**: Configurable chart of accounts for each business
- **Double-Entry Bookkeeping**: All transactions use double-entry accounting
- **Financial Reports**:
  - Profit & Loss (by year or custom date range)
  - Balance Sheet

## Technology Stack

- **Backend**: Python Flask with SQLite
- **Frontend**: React with Vite
- **Database**: SQLite (accounting.db)

## Architecture Overview

The application can run in **two modes**:

### 1. **Two-Server Mode (Development)** - Recommended for Development
- **Backend**: Flask API server on port 5001
- **Frontend**: Vite dev server on port 3000
- **Advantages**: 
  - Hot Module Replacement (instant updates)
  - Fast development experience
  - Separate processes for debugging
- **Disadvantages**: 
  - Two servers to manage
  - Two ports to configure

### 2. **Single-Server Mode (Production)** - Recommended for Deployment
- **Single Server**: Flask serves both API and frontend on port 5001
- **Advantages**: 
  - One server to manage
  - Simpler deployment
  - Single port configuration
  - Better for production
- **Disadvantages**: 
  - No hot reload (must rebuild frontend after changes)
  - Slower development cycle

**Choose based on your needs:**
- **Development**: Use two-server mode (`./start_backend.sh` + `./start_frontend.sh`)
- **Production/Deployment**: Use single-server mode (`./start_single_server.sh`)

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn

### Option A: Two-Server Mode (Development)

#### Backend Setup

1. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
cd backend
python database.py
```

4. Start the Flask server:
```bash
cd backend
python app.py
```

**Note:** Make sure your virtual environment is activated before running the above commands.

The backend API will be running on http://localhost:5001 (also accessible from LAN at http://YOUR_IP:5001)

### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will be running on http://localhost:3000 (also accessible from LAN at http://YOUR_IP:3000)

**Quick Start (Two-Server Mode):**
```bash
# Terminal 1
./start_backend.sh

# Terminal 2
./start_frontend.sh
```

### Option B: Single-Server Mode (Production)

Run everything from a single Flask server:

```bash
./start_single_server.sh
```

This script will:
1. Build the frontend (`npm run build`)
2. Start Flask server serving both API and frontend
3. Access at http://localhost:5001

**Note:** In single-server mode, you must rebuild the frontend after making changes:
```bash
cd frontend && npm run build
```

## Accessing from Other Devices on Your Network (LAN)

The application is configured to be accessible from other devices on your local network.

### Quick Start

1. **Get your local IP address:**
   ```bash
   ./get_ip.sh
   ```
   Or manually find your IP:
   - **macOS/Linux**: Run `ifconfig` or `ipconfig getifaddr en0`
   - **Windows**: Run `ipconfig` and look for IPv4 Address

2. **Start both servers:**
   ```bash
   # Terminal 1 - Backend
   ./start_backend.sh
   
   # Terminal 2 - Frontend
   ./start_frontend.sh
   ```

3. **Access from other devices:**
   - Open a browser on any device connected to the same network
   - Navigate to: `http://YOUR_IP_ADDRESS:3000`
   - Example: `http://192.168.86.179:3000`

### Configuration

- **Backend**: Already configured to listen on `0.0.0.0:5001` (accessible from LAN)
- **Frontend**: Configured to listen on `0.0.0.0:3000` (accessible from LAN)
- The frontend automatically proxies API requests to the backend

### Firewall Notes

If you can't access from other devices, you may need to allow incoming connections:

- **macOS**: System Preferences → Security & Privacy → Firewall → Allow incoming connections for Python and Node
- **Linux**: Check `ufw` or `iptables` settings
- **Windows**: Windows Defender Firewall → Allow an app through firewall

## Usage

1. Start both backend and frontend servers (see Setup Instructions above)

2. Open your browser to http://localhost:3000

3. Create a new business from the home page

4. For each business, you can:
   - Set up Chart of Accounts
   - Add Bank Accounts
   - Add Credit Card Accounts
   - Add Loan Accounts
   - Record Transactions (double-entry bookkeeping)
   - View Financial Reports (Profit & Loss and Balance Sheet)

## Project Structure

```
accounting/
├── accounting.db              # SQLite database
├── backend/
│   ├── app.py                # Flask API application
│   └── database.py           # Database schema and initialization
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── App.jsx          # Main app component
│   │   ├── api.js           # API client
│   │   └── index.css        # Global styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── requirements.txt          # Python dependencies
└── README.md
```

## API Endpoints

### Businesses
- `GET /api/businesses` - Get all businesses
- `POST /api/businesses` - Create a new business
- `GET /api/businesses/:id` - Get a specific business
- `PUT /api/businesses/:id` - Update a business
- `DELETE /api/businesses/:id` - Delete a business

### Chart of Accounts
- `GET /api/businesses/:id/chart-of-accounts` - Get chart of accounts
- `POST /api/businesses/:id/chart-of-accounts` - Create a new account
- `GET /api/account-types` - Get all account types

### Bank Accounts
- `GET /api/businesses/:id/bank-accounts` - Get bank accounts
- `POST /api/businesses/:id/bank-accounts` - Create a bank account

### Credit Card Accounts
- `GET /api/businesses/:id/credit-card-accounts` - Get credit card accounts
- `POST /api/businesses/:id/credit-card-accounts` - Create a credit card account

### Loan Accounts
- `GET /api/businesses/:id/loan-accounts` - Get loan accounts
- `POST /api/businesses/:id/loan-accounts` - Create a loan account

### Transactions
- `GET /api/businesses/:id/transactions` - Get transactions
- `POST /api/businesses/:id/transactions` - Create a transaction
- `POST /api/businesses/:id/transactions/import-csv` - Import transactions from CSV file

### Reports
- `GET /api/businesses/:id/reports/profit-loss` - Get Profit & Loss report
- `GET /api/businesses/:id/reports/balance-sheet` - Get Balance Sheet

## CSV Import Feature

The application supports importing transactions from CSV files. The CSV must contain the following columns:
- **Details** - Transaction details
- **Posting Date** - Transaction date (supports multiple formats: MM/DD/YYYY, YYYY-MM-DD, etc.)
- **Description** - Transaction description
- **Amount** - Transaction amount (numeric)
- **Type** - Transaction type (DEBIT, CREDIT, WITHDRAWAL, DEPOSIT, etc.)
- **Balance** - Account balance (optional, for reference)
- **Check or Slip #** - Reference number

### Using CSV Import

1. Navigate to the Transactions page for a business
2. Click "Import CSV" button
3. Select the business, bank account, and mapping accounts:
   - **Bank Account**: The bank account associated with the transactions
   - **Expense Account**: Used for DEBIT transactions (money going out)
   - **Revenue Account**: Used for CREDIT transactions (money coming in)
4. Select your CSV file
5. Review the preview and click "Import Transactions"

The system will:
- Parse each row and create double-entry transactions
- Map DEBIT transactions: Debit expense account, Credit bank account
- Map CREDIT transactions: Debit bank account, Credit revenue account
- Show a summary of imported, skipped, and error rows

## Notes

- The application uses double-entry bookkeeping for all transactions
- Each transaction must have balanced debits and credits
- The Chart of Accounts is configurable per business
- Reports can be filtered by date ranges or specific years
- CSV import automatically creates balanced double-entry transactions

