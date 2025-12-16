import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'

function Transactions() {
  const { businessId } = useParams()
  const [transactions, setTransactions] = useState([])
  const [filteredTransactions, setFilteredTransactions] = useState([])
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [showBulkEditModal, setShowBulkEditModal] = useState(false)
  const [editingTransactionId, setEditingTransactionId] = useState(null)
  const [selectedTransactions, setSelectedTransactions] = useState([])
  const [descriptionFilter, setDescriptionFilter] = useState('')
  const [descriptionInput, setDescriptionInput] = useState('') // Local state for input
  const [accountFilter, setAccountFilter] = useState('')
  const [bulkEditData, setBulkEditData] = useState({
    chart_of_account_id: '',
    line_filter: 'ALL'
  })
  const [formData, setFormData] = useState({
    transaction_date: new Date().toISOString().split('T')[0],
    description: '',
    reference_number: '',
    lines: [
      { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' },
      { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' }
    ]
  })

  const loadData = async () => {
    try {
      setLoading(true)
      const params = {}
      if (accountFilter) {
        params.account_id = accountFilter
      }
      if (descriptionFilter) {
        params.description = descriptionFilter
      }
      
      const [txnsRes, accountsRes] = await Promise.all([
        api.getTransactions(businessId, params),
        api.getChartOfAccounts(businessId)
      ])
      setTransactions(txnsRes.data)
      setAccounts(accountsRes.data)
      setFilteredTransactions(txnsRes.data)
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Debounce description filter to avoid losing focus on each keystroke
  useEffect(() => {
    const timer = setTimeout(() => {
      setDescriptionFilter(descriptionInput)
    }, 300) // Wait 300ms after user stops typing

    return () => clearTimeout(timer)
  }, [descriptionInput])

  useEffect(() => {
    if (businessId) {
      loadData()
    }
  }, [businessId, accountFilter, descriptionFilter])

  const addLine = () => {
    setFormData({
      ...formData,
      lines: [...formData.lines, { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' }]
    })
  }

  const updateLine = (index, field, value) => {
    const newLines = [...formData.lines]
    newLines[index] = { ...newLines[index], [field]: value }
    
    // Auto-set opposite amount to 0 when one is entered
    if (field === 'debit_amount' && parseFloat(value) > 0) {
      newLines[index].credit_amount = '0'
    } else if (field === 'credit_amount' && parseFloat(value) > 0) {
      newLines[index].debit_amount = '0'
    }
    
    setFormData({ ...formData, lines: newLines })
  }

  const removeLine = (index) => {
    if (formData.lines.length > 2) {
      const newLines = formData.lines.filter((_, i) => i !== index)
      setFormData({ ...formData, lines: newLines })
    }
  }

  const validateLines = () => {
    const totalDebits = formData.lines.reduce((sum, line) => sum + (parseFloat(line.debit_amount) || 0), 0)
    const totalCredits = formData.lines.reduce((sum, line) => sum + (parseFloat(line.credit_amount) || 0), 0)
    return Math.abs(totalDebits - totalCredits) < 0.01
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!validateLines()) {
      alert('Debits must equal credits. Please check your transaction lines.')
      return
    }

    try {
      const data = {
        ...formData,
        lines: formData.lines
          .filter(line => line.chart_of_account_id)
          .map(line => ({
            chart_of_account_id: parseInt(line.chart_of_account_id),
            debit_amount: parseFloat(line.debit_amount) || 0,
            credit_amount: parseFloat(line.credit_amount) || 0
          }))
      }
      
      if (editingTransactionId) {
        await api.updateTransaction(businessId, editingTransactionId, data)
      } else {
        await api.createTransaction(businessId, data)
      }
      
      setShowModal(false)
      setEditingTransactionId(null)
      setFormData({
        transaction_date: new Date().toISOString().split('T')[0],
        description: '',
        reference_number: '',
        lines: [
          { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' },
          { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' }
        ]
      })
      loadData()
    } catch (error) {
      alert(`Error ${editingTransactionId ? 'updating' : 'creating'} transaction: ` + (error.response?.data?.error || error.message))
    }
  }

  const handleEdit = (transaction) => {
    // Populate form with transaction data
    const transactionDate = new Date(transaction.transaction_date).toISOString().split('T')[0]
    setFormData({
      transaction_date: transactionDate,
      description: transaction.description || '',
      reference_number: transaction.reference_number || '',
      lines: transaction.lines && transaction.lines.length > 0
        ? transaction.lines.map(line => ({
            chart_of_account_id: String(line.chart_of_account_id),
            debit_amount: String(line.debit_amount || 0),
            credit_amount: String(line.credit_amount || 0)
          }))
        : [
            { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' },
            { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' }
          ]
    })
    setEditingTransactionId(transaction.id)
    setShowModal(true)
  }

  const handleDelete = async (transaction) => {
    if (!window.confirm(`Are you sure you want to delete this transaction?\n\nDate: ${new Date(transaction.transaction_date).toLocaleDateString()}\nDescription: ${transaction.description || 'N/A'}\n\nThis action cannot be undone.`)) {
      return
    }

    try {
      await api.deleteTransaction(businessId, transaction.id)
      loadData()
    } catch (error) {
      alert('Error deleting transaction: ' + (error.response?.data?.error || error.message))
    }
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setEditingTransactionId(null)
    setFormData({
      transaction_date: new Date().toISOString().split('T')[0],
      description: '',
      reference_number: '',
      lines: [
        { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' },
        { chart_of_account_id: '', debit_amount: '0', credit_amount: '0' }
      ]
    })
  }

  const totalDebits = formData.lines.reduce((sum, line) => sum + (parseFloat(line.debit_amount) || 0), 0)
  const totalCredits = formData.lines.reduce((sum, line) => sum + (parseFloat(line.credit_amount) || 0), 0)
  const isBalanced = Math.abs(totalDebits - totalCredits) < 0.01

  const handleSelectTransaction = (transactionId) => {
    setSelectedTransactions(prev => 
      prev.includes(transactionId)
        ? prev.filter(id => id !== transactionId)
        : [...prev, transactionId]
    )
  }

  const handleSelectAll = () => {
    if (selectedTransactions.length === filteredTransactions.length) {
      setSelectedTransactions([])
    } else {
      setSelectedTransactions(filteredTransactions.map(t => t.id))
    }
  }

  const handleBulkEdit = async () => {
    if (selectedTransactions.length === 0) {
      alert('Please select at least one transaction')
      return
    }

    if (!bulkEditData.chart_of_account_id) {
      alert('Please select a chart of account')
      return
    }

    try {
      const response = await api.bulkUpdateTransactions(businessId, {
        transaction_ids: selectedTransactions,
        chart_of_account_id: parseInt(bulkEditData.chart_of_account_id),
        line_filter: bulkEditData.line_filter
      })
      setShowBulkEditModal(false)
      setSelectedTransactions([])
      setBulkEditData({ chart_of_account_id: '', line_filter: 'ALL' })
      loadData()
      alert(response.data.message || `Successfully updated ${selectedTransactions.length} transaction(s)`)
    } catch (error) {
      alert('Error updating transactions: ' + (error.response?.data?.error || error.message))
    }
  }

  if (loading) {
    return <div className="container loading">Loading...</div>
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Transactions</h1>
          <div>
            <Link to={`/business/${businessId}`} className="btn btn-secondary" style={{ textDecoration: 'none', marginRight: '10px' }}>
              ← Back
            </Link>
            {businessId && (
              <Link 
                to={`/business/${businessId}/transactions/import`} 
                className="btn btn-secondary" 
                style={{ textDecoration: 'none', marginRight: '10px', display: 'inline-block' }}
              >
                Import CSV
              </Link>
            )}
            {selectedTransactions.length > 0 && (
              <button 
                className="btn btn-secondary" 
                onClick={() => setShowBulkEditModal(true)}
                style={{ marginRight: '10px' }}
              >
                Bulk Edit ({selectedTransactions.length})
              </button>
            )}
            <button className="btn btn-primary" onClick={() => setShowModal(true)}>
              + New Transaction
            </button>
          </div>
        </div>

        <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ flex: 1, minWidth: '200px', marginBottom: 0 }}>
            <label>Filter by Account</label>
            <select
              value={accountFilter}
              onChange={(e) => setAccountFilter(e.target.value)}
              style={{ width: '100%' }}
            >
              <option value="">All Accounts</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.account_code} - {account.account_name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-group" style={{ flex: 1, minWidth: '200px', marginBottom: 0 }}>
            <label>Search by Description</label>
            <input
              type="text"
              placeholder="Filter transactions by description..."
              value={descriptionInput}
              onChange={(e) => setDescriptionInput(e.target.value)}
              style={{ width: '100%' }}
            />
          </div>
          {(accountFilter || descriptionInput) && (
            <button 
              className="btn btn-secondary" 
              onClick={() => {
                setAccountFilter('')
                setDescriptionInput('')
                setDescriptionFilter('')
              }}
              style={{ marginBottom: 0 }}
            >
              Clear Filters
            </button>
          )}
        </div>

        <table>
          <thead>
            <tr>
              <th>
                <input
                  type="checkbox"
                  checked={selectedTransactions.length === filteredTransactions.length && filteredTransactions.length > 0}
                  onChange={handleSelectAll}
                />
              </th>
              <th>Date</th>
              <th>Description</th>
              <th>Reference</th>
              <th>Type</th>
              <th>Accounts</th>
              <th>Amount</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredTransactions.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '20px' }}>
                  {descriptionFilter ? 'No transactions match your search' : 'No transactions found'}
                </td>
              </tr>
            ) : (
              filteredTransactions.map((txn) => {
                // Get unique accounts from transaction lines
                const accounts = txn.lines && txn.lines.length > 0
                  ? [...new Map(txn.lines.map(line => [line.chart_of_account_id, {
                    code: line.account_code,
                    name: line.account_name,
                    debit: parseFloat(line.debit_amount || 0),
                    credit: parseFloat(line.credit_amount || 0)
                  }])).values()]
                  : []
                
                return (
                  <tr key={txn.id} style={{ backgroundColor: selectedTransactions.includes(txn.id) ? '#e7f3ff' : '' }}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedTransactions.includes(txn.id)}
                        onChange={() => handleSelectTransaction(txn.id)}
                      />
                    </td>
                    <td>{new Date(txn.transaction_date).toLocaleDateString()}</td>
                    <td>{txn.description || '-'}</td>
                    <td>{txn.reference_number || '-'}</td>
                    <td>{txn.transaction_type || '-'}</td>
                    <td>
                      {accounts.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {accounts.map((acc, idx) => (
                            <div key={idx} style={{ fontSize: '12px' }}>
                              <span style={{ fontWeight: 'bold', color: '#666' }}>{acc.code}</span>
                              {' - '}
                              <span>{acc.name}</span>
                              {acc.debit > 0 && <span style={{ color: '#dc3545', marginLeft: '8px' }}>(Dr: ${acc.debit.toFixed(2)})</span>}
                              {acc.credit > 0 && <span style={{ color: '#28a745', marginLeft: '8px' }}>(Cr: ${acc.credit.toFixed(2)})</span>}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span style={{ color: '#999', fontStyle: 'italic' }}>No accounts assigned</span>
                      )}
                    </td>
                    <td>${parseFloat(txn.amount || 0).toFixed(2)}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '5px' }}>
                        <button
                          className="btn btn-secondary"
                          onClick={() => handleEdit(txn)}
                          style={{ padding: '4px 8px', fontSize: '12px' }}
                        >
                          Edit
                        </button>
                        <button
                          className="btn btn-danger"
                          onClick={() => handleDelete(txn)}
                          style={{ padding: '4px 8px', fontSize: '12px' }}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '800px' }}>
            <div className="modal-header">
              <h2>{editingTransactionId ? 'Edit Transaction' : 'New Transaction'}</h2>
              <button className="close-btn" onClick={handleCloseModal}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Transaction Date *</label>
                <input
                  type="date"
                  value={formData.transaction_date}
                  onChange={(e) => setFormData({ ...formData, transaction_date: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Reference Number</label>
                <input
                  type="text"
                  value={formData.reference_number}
                  onChange={(e) => setFormData({ ...formData, reference_number: e.target.value })}
                />
              </div>

              <h3 style={{ marginTop: '20px', marginBottom: '10px' }}>Transaction Lines</h3>
              
              {formData.lines.map((line, index) => (
                <div key={index} style={{ border: '1px solid #ddd', padding: '15px', marginBottom: '10px', borderRadius: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <strong>Line {index + 1}</strong>
                    {formData.lines.length > 2 && (
                      <button type="button" className="btn btn-danger" onClick={() => removeLine(index)} style={{ padding: '5px 10px', fontSize: '12px' }}>
                        Remove
                      </button>
                    )}
                  </div>
                  <div className="form-group">
                    <label>Account *</label>
                    <select
                      value={line.chart_of_account_id}
                      onChange={(e) => updateLine(index, 'chart_of_account_id', e.target.value)}
                      required
                    >
                      <option value="">Select account</option>
                      {accounts.map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.account_code} - {account.account_name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div className="form-group">
                      <label>Debit Amount</label>
                      <input
                        type="number"
                        step="0.01"
                        value={line.debit_amount}
                        onChange={(e) => updateLine(index, 'debit_amount', e.target.value)}
                        min="0"
                      />
                    </div>
                    <div className="form-group">
                      <label>Credit Amount</label>
                      <input
                        type="number"
                        step="0.01"
                        value={line.credit_amount}
                        onChange={(e) => updateLine(index, 'credit_amount', e.target.value)}
                        min="0"
                      />
                    </div>
                  </div>
                </div>
              ))}

              <button type="button" className="btn btn-secondary" onClick={addLine} style={{ marginBottom: '15px' }}>
                + Add Line
              </button>

              <div style={{ padding: '10px', background: '#f8f9fa', borderRadius: '4px', marginBottom: '15px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong>Total Debits:</strong>
                  <span>${totalDebits.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <strong>Total Credits:</strong>
                  <span>${totalCredits.toFixed(2)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '5px', paddingTop: '5px', borderTop: '1px solid #ddd' }}>
                  <strong>Difference:</strong>
                  <span style={{ color: isBalanced ? '#28a745' : '#dc3545' }}>
                    ${Math.abs(totalDebits - totalCredits).toFixed(2)}
                  </span>
                </div>
                {!isBalanced && (
                  <div className="error" style={{ marginTop: '5px' }}>
                    Debits must equal credits
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={!isBalanced}>
                  Create Transaction
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showBulkEditModal && (
        <div className="modal" onClick={() => setShowBulkEditModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Bulk Assign Chart of Account</h2>
              <button className="close-btn" onClick={() => setShowBulkEditModal(false)}>&times;</button>
            </div>
            <div style={{ marginBottom: '15px' }}>
              <p><strong>{selectedTransactions.length}</strong> transaction(s) selected</p>
              <small style={{ color: '#666' }}>
                This will update existing transaction lines in the selected transactions to use the specified chart of account.
              </small>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); handleBulkEdit(); }}>
              <div className="form-group">
                <label>Chart of Account *</label>
                <select
                  value={bulkEditData.chart_of_account_id}
                  onChange={(e) => setBulkEditData({ ...bulkEditData, chart_of_account_id: e.target.value })}
                  required
                >
                  <option value="">Select a chart of account</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.account_code} - {account.account_name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Update Which Lines</label>
                <select
                  value={bulkEditData.line_filter}
                  onChange={(e) => setBulkEditData({ ...bulkEditData, line_filter: e.target.value })}
                >
                  <option value="ALL">All Lines</option>
                  <option value="DEBIT_ONLY">Debit Lines Only</option>
                  <option value="CREDIT_ONLY">Credit Lines Only</option>
                  <option value="FIRST_LINE">First Line Only</option>
                </select>
                <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
                  Choose which transaction lines to update in each selected transaction
                </small>
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowBulkEditModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Update {selectedTransactions.length} Transaction(s)
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Transactions

