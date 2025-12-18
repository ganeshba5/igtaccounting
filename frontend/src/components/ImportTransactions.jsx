import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api, { axiosInstance } from '../api'

function ImportTransactions() {
  const { businessId } = useParams()
  const [businesses, setBusinesses] = useState([])
  const [selectedBusinessId, setSelectedBusinessId] = useState(businessId || '')
  const [bankAccounts, setBankAccounts] = useState([])
  const [chartAccounts, setChartAccounts] = useState([])
  const [selectedBankAccount, setSelectedBankAccount] = useState('')
  const [selectedExpenseAccount, setSelectedExpenseAccount] = useState('')
  const [selectedRevenueAccount, setSelectedRevenueAccount] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const [previewData, setPreviewData] = useState(null)

  useEffect(() => {
    loadBusinesses()
    if (businessId) {
      setSelectedBusinessId(businessId)
    }
  }, [businessId])

  useEffect(() => {
    if (selectedBusinessId) {
      loadAccounts(selectedBusinessId)
    }
  }, [selectedBusinessId])

  const loadBusinesses = async () => {
    try {
      const response = await api.getBusinesses()
      setBusinesses(response.data)
    } catch (error) {
      console.error('Error loading businesses:', error)
    }
  }

  const loadAccounts = async (bid) => {
    try {
      const [banksRes, chartRes] = await Promise.all([
        api.getBankAccounts(bid),
        api.getChartOfAccounts(bid)
      ])
      setBankAccounts(banksRes.data)
      setChartAccounts(chartRes.data)
      
      // Auto-select bank account if only one exists and none is selected
      if (banksRes.data.length === 1 && !selectedBankAccount) {
        setSelectedBankAccount(banksRes.data[0].id.toString())
      }
    } catch (error) {
      console.error('Error loading accounts:', error)
    }
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      previewCSV(selectedFile)
    }
  }

  // Simple CSV parser that handles quoted fields with embedded commas
  const parseCSVLine = (line) => {
    const values = []
    let current = ''
    let inQuotes = false
    
    for (let i = 0; i < line.length; i++) {
      const char = line[i]
      const nextChar = line[i + 1]
      
      if (char === '"') {
        if (inQuotes && nextChar === '"') {
          // Escaped quote (double quote)
          current += '"'
          i++ // Skip next quote
        } else {
          // Toggle quote state
          inQuotes = !inQuotes
        }
      } else if (char === ',' && !inQuotes) {
        // Comma outside quotes - field separator
        values.push(current.trim())
        current = ''
      } else {
        current += char
      }
    }
    // Add the last field
    values.push(current.trim())
    
    return values
  }

  const previewCSV = (file) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target.result
      const lines = text.split(/\r?\n/).filter(line => line.trim())
      if (lines.length > 0) {
        // Parse header
        const headerValues = parseCSVLine(lines[0])
        const headers = headerValues.map(h => h.replace(/^"|"$/g, '').trim())
        
        // Parse preview rows (first 5 data rows)
        const previewRows = lines.slice(1, 6).map(line => {
          const values = parseCSVLine(line)
          const row = {}
          headers.forEach((header, idx) => {
            // Remove surrounding quotes if present
            let value = values[idx] || ''
            value = value.replace(/^"|"$/g, '')
            row[header] = value
          })
          return row
        })
        
        setPreviewData({ headers, rows: previewRows, totalRows: lines.length - 1 })
      }
    }
    reader.readAsText(file)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    
    console.log('Form submitted', {
      file: !!file,
      selectedBusinessId,
      selectedBankAccount,
      selectedExpenseAccount,
      selectedRevenueAccount
    })
    
    if (!file) {
      alert('Please select a CSV file')
      return
    }
    
    if (!selectedBusinessId) {
      alert('Please select a business')
      return
    }
    
    if (!selectedBankAccount) {
      alert('Please select a bank account')
      return
    }
    
    // Expense and revenue accounts are optional - will default to "Uncategorized"
    
    console.log('Starting import...')
    setLoading(true)
    setImportResult(null)
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('bank_account_id', selectedBankAccount)
      if (selectedExpenseAccount) {
        formData.append('expense_account_id', selectedExpenseAccount)
      }
      if (selectedRevenueAccount) {
        formData.append('revenue_account_id', selectedRevenueAccount)
      }
      
      console.log('Sending request to:', `/businesses/${selectedBusinessId}/transactions/import-csv`)
      console.log('FormData contents:', {
        hasFile: formData.has('file'),
        bank_account_id: formData.get('bank_account_id'),
        expense_account_id: formData.get('expense_account_id'),
        revenue_account_id: formData.get('revenue_account_id')
      })
      
      // Use axiosInstance which includes auth token and proper base URL
      const response = await axiosInstance.post(
        `/businesses/${selectedBusinessId}/transactions/import-csv`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      
      console.log('Response received:', response.data)
      
      setImportResult(response.data)
      
      if (response.data.imported > 0) {
        // Reset file input
        setFile(null)
        setPreviewData(null)
        const fileInput = document.querySelector('input[type="file"]')
        if (fileInput) fileInput.value = ''
      }
    } catch (error) {
      console.error('Error importing CSV:', error)
      alert('Error importing CSV: ' + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
    }
  }

  // Filter accounts by category for expense and revenue
  const expenseAccounts = chartAccounts.filter(
    acc => acc.category === 'EXPENSE' || acc.account_type_code === 'EXPENSE'
  )
  const revenueAccounts = chartAccounts.filter(
    acc => acc.category === 'REVENUE' || acc.account_type_code === 'REVENUE'
  )

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Import Transactions from CSV</h1>
          {businessId && (
            <Link to={`/business/${businessId}`} className="btn btn-secondary" style={{ textDecoration: 'none' }}>
              ← Back
            </Link>
          )}
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Business *</label>
            <select
              value={selectedBusinessId}
              onChange={(e) => setSelectedBusinessId(e.target.value)}
              required
              disabled={!!businessId}
            >
              <option value="">Select a business</option>
              {businesses.map((business) => (
                <option key={business.id} value={business.id}>
                  {business.name}
                </option>
              ))}
            </select>
          </div>

          {selectedBusinessId && (
            <>
              <div className="form-group">
                <label>Bank Account *</label>
                <select
                  value={selectedBankAccount}
                  onChange={(e) => setSelectedBankAccount(e.target.value)}
                  required
                  disabled={bankAccounts.length === 1}
                >
                  <option value="">Select a bank account</option>
                  {bankAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.account_name} {account.account_number ? `(${account.account_number})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Expense Account (for DEBIT transactions)</label>
                <select
                  value={selectedExpenseAccount}
                  onChange={(e) => setSelectedExpenseAccount(e.target.value)}
                >
                  <option value="">Uncategorized Expense (default)</option>
                  {expenseAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.account_code} - {account.account_name}
                    </option>
                  ))}
                </select>
                <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
                  Optional: Defaults to "Uncategorized Expense" if not selected. Used for DEBIT/WITHDRAWAL transactions.
                </small>
              </div>

              <div className="form-group">
                <label>Revenue Account (for CREDIT transactions)</label>
                <select
                  value={selectedRevenueAccount}
                  onChange={(e) => setSelectedRevenueAccount(e.target.value)}
                >
                  <option value="">Uncategorized Revenue (default)</option>
                  {revenueAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.account_code} - {account.account_name}
                    </option>
                  ))}
                </select>
                <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
                  Optional: Defaults to "Uncategorized Revenue" if not selected. Used for CREDIT/DEPOSIT transactions.
                </small>
              </div>

              <div className="form-group">
                <label>CSV File *</label>
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileChange}
                  required
                />
                <small style={{ color: '#666', marginTop: '5px', display: 'block' }}>
                  Supported CSV formats:
                  <br />Format 1: Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
                  <br />Format 2: Posting Date, Description, Amount, Balance (Amount sign: -ve = Debit, +ve = Credit)
                  <br />Format 2 (alias): Date, Description, Amount, Running Bal. (same as Format 2)
                  <br />Format 3: Date, Description, Credit, Debit, Balance
                  <br />Note: The system will automatically skip lines until it finds the header row.
                </small>
              </div>

              {previewData && (
                <div style={{ marginTop: '20px', marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '4px' }}>
                  <h3>CSV Preview ({previewData.totalRows} rows)</h3>
                  <table style={{ marginTop: '10px', fontSize: '12px' }}>
                    <thead>
                      <tr>
                        {previewData.headers.map((header, idx) => (
                          <th key={idx}>{header}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {previewData.rows.map((row, rowIdx) => (
                        <tr key={rowIdx}>
                          {previewData.headers.map((header, colIdx) => (
                            <td key={colIdx}>{row[header] || '-'}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {importResult && (
                <div style={{ 
                  marginTop: '20px', 
                  padding: '15px', 
                  background: importResult.imported > 0 ? '#d4edda' : '#f8d7da',
                  borderRadius: '4px',
                  border: `1px solid ${importResult.imported > 0 ? '#c3e6cb' : '#f5c6cb'}`
                }}>
                  <h3>Import Results</h3>
                  <p><strong>Imported:</strong> {importResult.imported} transactions</p>
                  <p><strong>Skipped:</strong> {importResult.skipped} rows</p>
                  {importResult.errors && importResult.errors.length > 0 && (
                    <div style={{ marginTop: '10px' }}>
                      <strong>Errors:</strong>
                      <ul style={{ marginTop: '5px', fontSize: '12px' }}>
                        {importResult.errors.map((error, idx) => (
                          <li key={idx}>{error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '20px', flexDirection: 'column', alignItems: 'flex-end' }}>
                {(loading || !file || !selectedBankAccount) && (
                  <div style={{ fontSize: '12px', color: '#dc3545', marginBottom: '5px' }}>
                    {!file && 'Please select a CSV file. '}
                    {!selectedBankAccount && 'Please select a bank account. '}
                  </div>
                )}
                <button 
                  type="submit" 
                  className="btn btn-primary" 
                  disabled={loading || !file || !selectedBankAccount}
                  onClick={(e) => {
                    console.log('Button clicked', {
                      loading,
                      hasFile: !!file,
                      hasBankAccount: !!selectedBankAccount,
                      hasExpenseAccount: !!selectedExpenseAccount,
                      hasRevenueAccount: !!selectedRevenueAccount,
                      disabled: loading || !file || !selectedBankAccount || (!selectedExpenseAccount && !selectedRevenueAccount)
                    })
                    // Don't prevent default - let form submit handle it
                  }}
                >
                  {loading ? 'Importing...' : 'Import Transactions'}
                </button>
              </div>
            </>
          )}
        </form>
      </div>
    </div>
  )
}

export default ImportTransactions

