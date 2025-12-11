import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Businesses from './components/Businesses'
import BusinessDashboard from './components/BusinessDashboard'
import ChartOfAccounts from './components/ChartOfAccounts'
import BankAccounts from './components/BankAccounts'
import CreditCardAccounts from './components/CreditCardAccounts'
import LoanAccounts from './components/LoanAccounts'
import Transactions from './components/Transactions'
import Reports from './components/Reports'
import ImportTransactions from './components/ImportTransactions'
import CombinedProfitLoss from './components/CombinedProfitLoss'

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <Routes>
          <Route path="/" element={<Businesses />} />
          <Route path="/business/:businessId" element={<BusinessDashboard />} />
          <Route path="/business/:businessId/chart-of-accounts" element={<ChartOfAccounts />} />
          <Route path="/business/:businessId/bank-accounts" element={<BankAccounts />} />
          <Route path="/business/:businessId/credit-cards" element={<CreditCardAccounts />} />
          <Route path="/business/:businessId/loans" element={<LoanAccounts />} />
          <Route path="/business/:businessId/transactions/import" element={<ImportTransactions />} />
          <Route path="/business/:businessId/transactions" element={<Transactions />} />
          <Route path="/transactions/import" element={<ImportTransactions />} />
          <Route path="/business/:businessId/reports" element={<Reports />} />
          <Route path="/reports/combined-profit-loss" element={<CombinedProfitLoss />} />
        </Routes>
      </div>
    </Router>
  )
}

function Navbar() {
  return (
    <nav className="navbar">
      <Link to="/">Home</Link>
    </nav>
  )
}

export default App

