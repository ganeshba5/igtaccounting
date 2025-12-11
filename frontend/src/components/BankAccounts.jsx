import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'

function BankAccounts() {
  const { businessId } = useParams()
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({
    account_name: '',
    account_number: '',
    bank_name: '',
    routing_number: '',
    opening_balance: '0',
    account_code: ''
  })

  useEffect(() => {
    loadAccounts()
  }, [businessId])

  const loadAccounts = async () => {
    try {
      const response = await api.getBankAccounts(businessId)
      setAccounts(response.data)
    } catch (error) {
      console.error('Error loading bank accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const data = {
        ...formData,
        opening_balance: parseFloat(formData.opening_balance) || 0
      }
      await api.createBankAccount(businessId, data)
      setShowModal(false)
      setFormData({
        account_name: '',
        account_number: '',
        bank_name: '',
        routing_number: '',
        opening_balance: '0',
        account_code: ''
      })
      loadAccounts()
    } catch (error) {
      alert('Error creating bank account: ' + (error.response?.data?.error || error.message))
    }
  }

  if (loading) {
    return <div className="container loading">Loading...</div>
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Bank Accounts</h1>
          <div>
            <Link to={`/business/${businessId}`} className="btn btn-secondary" style={{ textDecoration: 'none', marginRight: '10px' }}>
              ← Back
            </Link>
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              + New Bank Account
            </button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Account Name</th>
              <th>Bank Name</th>
              <th>Account Number</th>
              <th>Current Balance</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((account) => (
              <tr key={account.id}>
                <td>{account.account_name}</td>
                <td>{account.bank_name || '-'}</td>
                <td>{account.account_number || '-'}</td>
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
              <h2>New Bank Account</h2>
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
                <label>Bank Name</label>
                <input
                  type="text"
                  value={formData.bank_name}
                  onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Account Number</label>
                <input
                  type="text"
                  value={formData.account_number}
                  onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Routing Number</label>
                <input
                  type="text"
                  value={formData.routing_number}
                  onChange={(e) => setFormData({ ...formData, routing_number: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Opening Balance</label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.opening_balance}
                  onChange={(e) => setFormData({ ...formData, opening_balance: e.target.value })}
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

export default BankAccounts

