import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'

function CreditCardAccounts() {
  const { businessId } = useParams()
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    account_name: '',
    card_number_last4: '',
    issuer: '',
    credit_limit: '0',
    current_balance: '0',
    account_code: ''
  })

  useEffect(() => {
    loadAccounts()
  }, [businessId])

  const loadAccounts = async () => {
    try {
      const response = await api.getCreditCardAccounts(businessId)
      setAccounts(response.data)
    } catch (error) {
      console.error('Error loading credit card accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const data = {
        ...formData,
        credit_limit: parseFloat(formData.credit_limit) || 0,
        current_balance: parseFloat(formData.current_balance) || 0
      }
      await api.createCreditCardAccount(businessId, data)
      setShowModal(false)
      setFormData({
        account_name: '',
        card_number_last4: '',
        issuer: '',
        credit_limit: '0',
        current_balance: '0',
        account_code: ''
      })
      loadAccounts()
    } catch (error) {
      alert('Error creating credit card account: ' + (error.response?.data?.error || error.message))
    }
  }

  if (loading) {
    return <div className="container loading">Loading...</div>
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Credit Card Accounts</h1>
          <div>
            <Link to={`/business/${businessId}`} className="btn btn-secondary" style={{ textDecoration: 'none', marginRight: '10px' }}>
              ← Back
            </Link>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              + New Credit Card
            </button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Account Name</th>
              <th>Issuer</th>
              <th>Card Number (Last 4)</th>
              <th>Credit Limit</th>
              <th>Current Balance</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((account) => (
              <tr key={account.id}>
                <td>{account.account_name}</td>
                <td>{account.issuer || '-'}</td>
                <td>{account.card_number_last4 || '-'}</td>
                <td>${parseFloat(account.credit_limit || 0).toFixed(2)}</td>
                <td>${parseFloat(account.current_balance || 0).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal" onClick={() => setShowModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>New Credit Card Account</h2>
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
                <label>Issuer</label>
                <input
                  type="text"
                  value={formData.issuer}
                  onChange={(e) => setFormData({ ...formData, issuer: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Card Number (Last 4 digits)</label>
                <input
                  type="text"
                  maxLength="4"
                  value={formData.card_number_last4}
                  onChange={(e) => setFormData({ ...formData, card_number_last4: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Credit Limit</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.credit_limit}
                  onChange={(e) => setFormData({ ...formData, credit_limit: e.target.value })}
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

export default CreditCardAccounts

