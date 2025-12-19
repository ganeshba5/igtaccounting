import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'

function ChartOfAccounts() {
  const { businessId } = useParams()
  const [accounts, setAccounts] = useState([])
  const [accountTypes, setAccountTypes] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingAccount, setEditingAccount] = useState(null)
  const [formData, setFormData] = useState({
    account_code: '',
    account_name: '',
    account_type_id: '',
    description: '',
    parent_account_id: ''
  })

  useEffect(() => {
    loadData()
  }, [businessId])

  const loadData = async () => {
    try {
      const [accountsRes, typesRes] = await Promise.all([
        api.getChartOfAccounts(businessId),
        api.getAccountTypes()
      ])
      setAccounts(accountsRes.data)
      setAccountTypes(typesRes.data)
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (account) => {
    setEditingAccount(account)
    setFormData({
      account_code: account.account_code || '',
      account_name: account.account_name || '',
      account_type_id: account.account_type_id || '',
      description: account.description || '',
      parent_account_id: account.parent_account_id || ''
    })
    setShowModal(true)
  }

  const handleCancel = () => {
    setShowModal(false)
    setEditingAccount(null)
    setFormData({ account_code: '', account_name: '', account_type_id: '', description: '', parent_account_id: '' })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingAccount) {
        await api.updateChartOfAccount(businessId, editingAccount.id, formData)
      } else {
        await api.createChartOfAccount(businessId, formData)
      }
      handleCancel()
      loadData()
    } catch (error) {
      alert(`Error ${editingAccount ? 'updating' : 'creating'} account: ` + (error.response?.data?.error || error.message))
    }
  }

  const handleDelete = async (account) => {
    if (!window.confirm(`Are you sure you want to delete "${account.account_code} - ${account.account_name}"?\n\nThis action cannot be undone.`)) {
      return
    }
    
    try {
      await api.deleteChartOfAccount(businessId, account.id)
      loadData()
    } catch (error) {
      const errorMessage = error.response?.data?.error || error.response?.data?.message || error.message
      alert(`Error deleting account: ${errorMessage}`)
    }
  }

  if (loading) {
    return <div className="container loading">Loading...</div>
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Chart of Accounts</h1>
          <div>
            <Link to={`/business/${businessId}`} className="btn btn-secondary" style={{ textDecoration: 'none', marginRight: '10px' }}>
              ← Back
            </Link>
            <button className="btn btn-primary" onClick={() => {
              setEditingAccount(null)
              setFormData({ account_code: '', account_name: '', account_type_id: '', description: '', parent_account_id: '' })
              setShowModal(true)
            }}>
              + New Account
            </button>
          </div>
        </div>

        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Account Name</th>
              <th>Parent Account</th>
              <th>Type</th>
              <th>Category</th>
              <th>Normal Balance</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {accounts.map((account) => {
              const parentAccount = accounts.find(acc => acc.id === account.parent_account_id)
              const indentLevel = account.parent_account_id ? 1 : 0
              return (
                <tr key={account.id}>
                  <td>{account.account_code}</td>
                  <td style={{ paddingLeft: `${indentLevel * 20}px` }}>
                    {account.parent_account_id && <span style={{ color: '#999' }}>└─ </span>}
                    {account.account_name}
                  </td>
                  <td>{parentAccount ? `${parentAccount.account_code} - ${parentAccount.account_name}` : '-'}</td>
                  <td>{account.account_type_name || '-'}</td>
                  <td>{account.category || '-'}</td>
                  <td>{account.normal_balance || '-'}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        className="btn btn-secondary" 
                        onClick={() => handleEdit(account)}
                        style={{ padding: '5px 10px', fontSize: '12px' }}
                      >
                        Edit
                      </button>
                      <button 
                        className="btn btn-secondary" 
                        onClick={() => handleDelete(account)}
                        style={{ padding: '5px 10px', fontSize: '12px', backgroundColor: '#dc3545', color: 'white', border: 'none' }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal" onClick={handleCancel}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingAccount ? 'Edit Account' : 'New Account'}</h2>
              <button className="close-btn" onClick={handleCancel}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Account Code *</label>
                <input
                  type="text"
                  value={formData.account_code}
                  onChange={(e) => setFormData({ ...formData, account_code: e.target.value })}
                  required
                  disabled={!!editingAccount}
                />
                {editingAccount && (
                  <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
                    Account code cannot be changed after creation
                  </small>
                )}
              </div>
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
                <label>Account Type</label>
                <select
                  value={formData.account_type_id}
                  onChange={(e) => setFormData({ ...formData, account_type_id: e.target.value })}
                >
                  <option value="">Select an account type</option>
                  {accountTypes.map((type) => (
                    <option key={type.id} value={type.id}>
                      {type.name} ({type.category})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Parent Account (Optional)</label>
                <select
                  value={formData.parent_account_id}
                  onChange={(e) => setFormData({ ...formData, parent_account_id: e.target.value })}
                >
                  <option value="">None (Top-level account)</option>
                  {accounts
                    .filter(acc => acc.id !== editingAccount?.id) // Prevent self-reference if editing
                    .map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.account_code} - {account.account_name}
                      </option>
                    ))}
                </select>
                <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
                  Select a parent account to create a hierarchical structure
                </small>
              </div>
              <div className="form-group">
                <label>Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows="3"
                />
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={handleCancel}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingAccount ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default ChartOfAccounts

