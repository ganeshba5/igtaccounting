import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'

function LoanAccounts() {
  const { businessId } = useParams()
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    account_name: '',
    lender_name: '',
    loan_number: '',
    principal_amount: '0',
    current_balance: '0',
    interest_rate: '0',
    account_code: ''
  })

  useEffect(() => {
    loadAccounts()
  }, [businessId])

  const loadAccounts = async () => {
    try {
      const response = await api.getLoanAccounts(businessId)
      setAccounts(response.data)
    } catch (error) {
      console.error('Error loading loan accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const data = {
        ...formData,
        principal_amount: parseFloat(formData.principal_amount) || 0,
        current_balance: parseFloat(formData.current_balance) || 0,
        interest_rate: parseFloat(formData.interest_rate) || 0
      }
      await api.createLoanAccount(businessId, data)
      setShowModal(false)
      setFormData({
        account_name: '',
        lender_name: '',
        loan_number: '',
        principal_amount: '0',
        current_balance: '0',
        interest_rate: '0',
        account_code: ''
      })
      loadAccounts()
    } catch (error) {
      alert('Error creating loan account: ' + (error.response?.data?.error || error.message))
    }
  }

  if (loading) {
    return <div className="container loading">Loading...</div>
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Loan Accounts</h1>
          <div>
            <Link to={`/business/${businessId}`} className="btn btn-secondary" style={{ textDecoration: 'none', marginRight: '10px' }}>
              ← Back
            </Link>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              + New Loan
            </button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Account Name</th>
              <th>Lender</th>
              <th>Loan Number</th>
              <th>Principal</th>
              <th>Current Balance</th>
              <th>Interest Rate</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((account) => (
              <tr key={account.id}>
                <td>{account.account_name}</td>
                <td>{account.lender_name || '-'}</td>
                <td>{account.loan_number || '-'}</td>
                <td>${parseFloat(account.principal_amount || 0).toFixed(2)}</td>
                <td>${parseFloat(account.current_balance || 0).toFixed(2)}</td>
                <td>{parseFloat(account.interest_rate || 0).toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>New Loan Account</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Account Name *</label>
                <input
                  type="text"
                  value={formData.account_name}
                  onChange={(e) => setFormData({ ...formData, account_name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Lender Name</label>
                <input
                  type="text"
                  value={formData.lender_name}
                  onChange={(e) => setFormData({ ...formData, lender_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Loan Number</label>
                <input
                  type="text"
                  value={formData.loan_number}
                  onChange={(e) => setFormData({ ...formData, loan_number: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Principal Amount</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.principal_amount}
                  onChange={(e) => setFormData({ ...formData, principal_amount: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Current Balance</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.current_balance}
                  onChange={(e) => setFormData({ ...formData, current_balance: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Interest Rate (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.interest_rate}
                  onChange={(e) => setFormData({ ...formData, interest_rate: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Account Code</label>
                <input
                  type="text"
                  value={formData.account_code}
                  onChange={(e) => setFormData({ ...formData, account_code: e.target.value })}
                />
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default LoanAccounts

