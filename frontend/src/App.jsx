import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
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
import Hub from './components/Hub'

function AppContent() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <Routes>
          <Route path="/" element={
            <ProtectedRoute>
              <Businesses />
            </ProtectedRoute>
          } />
          <Route path="/business/:businessId" element={
            <ProtectedRoute>
              <BusinessDashboard />
            </ProtectedRoute>
          } />
          <Route path="/business/:businessId/chart-of-accounts" element={
            <ProtectedRoute>
              <ChartOfAccounts />
            </ProtectedRoute>
          } />
          <Route path="/business/:businessId/bank-accounts" element={
            <ProtectedRoute>
              <BankAccounts />
            </ProtectedRoute>
          } />
          <Route path="/business/:businessId/credit-cards" element={
            <ProtectedRoute>
              <CreditCardAccounts />
            </ProtectedRoute>
          } />
          <Route path="/business/:businessId/loans" element={
            <ProtectedRoute>
              <LoanAccounts />
            </ProtectedRoute>
          } />
          <Route path="/business/:businessId/transactions/import" element={
            <ProtectedRoute>
              <ImportTransactions />
            </ProtectedRoute>
          } />
          <Route path="/business/:businessId/transactions" element={
            <ProtectedRoute>
              <Transactions />
            </ProtectedRoute>
          } />
          <Route path="/transactions/import" element={
            <ProtectedRoute>
              <ImportTransactions />
            </ProtectedRoute>
          } />
          <Route path="/business/:businessId/reports" element={
            <ProtectedRoute>
              <Reports />
            </ProtectedRoute>
          } />
          <Route path="/reports/combined-profit-loss" element={
            <ProtectedRoute>
              <CombinedProfitLoss />
            </ProtectedRoute>
          } />
          <Route path="/hub" element={
            <ProtectedRoute>
              <Hub />
            </ProtectedRoute>
          } />
        </Routes>
      </div>
    </Router>
  )
}

function Navbar() {
  const { user, logout, isAuthenticated } = useAuth()

  return (
    <nav className="navbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 20px' }}>
      <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>Home</Link>
      {isAuthenticated && user && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ fontSize: '14px', color: '#666' }}>
            {user.name || user.username || 'User'}
          </span>
          <button 
            onClick={logout} 
            className="btn btn-secondary"
            style={{ padding: '5px 10px', fontSize: '12px' }}
          >
            Sign Out
          </button>
        </div>
      )}
    </nav>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App

