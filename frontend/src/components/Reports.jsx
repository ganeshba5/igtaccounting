import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'

function Reports() {
  const { businessId } = useParams()
  const [activeTab, setActiveTab] = useState('profit-loss')
  const [profitLoss, setProfitLoss] = useState(null)
  const [balanceSheet, setBalanceSheet] = useState(null)
  const [transactionDetailsByAccount, setTransactionDetailsByAccount] = useState(null)
  const [loading, setLoading] = useState(false)
  const [drillDownAccount, setDrillDownAccount] = useState(null)
  const [drillDownTransactions, setDrillDownTransactions] = useState([])
  const [loadingTransactions, setLoadingTransactions] = useState(false)
  const [business, setBusiness] = useState(null)
  
  const [plFilters, setPlFilters] = useState({
    dateFilterType: 'currentYearToDate', // 'currentMonthToDate', 'lastMonth', 'currentYearToDate', 'lastYear', 'custom'
    selectedYear: (new Date().getFullYear() - 1).toString(), // For lastYear option
    start_date: '',
    end_date: ''
  })

  // Helper function to get date range based on filter type
  const getDateRange = (filterType, selectedYear = null, customStartDate = '', customEndDate = '') => {
    const now = new Date()
    const currentYear = now.getFullYear()
    const currentMonth = now.getMonth()

    switch (filterType) {
      case 'currentMonthToDate':
        return {
          start_date: new Date(currentYear, currentMonth, 1).toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        }
      
      case 'lastMonth':
        const lastMonth = new Date(currentYear, currentMonth - 1, 1)
        const lastMonthEnd = new Date(currentYear, currentMonth, 0)
        return {
          start_date: lastMonth.toISOString().split('T')[0],
          end_date: lastMonthEnd.toISOString().split('T')[0]
        }
      
      case 'currentYearToDate':
        return {
          start_date: `${currentYear}-01-01`,
          end_date: now.toISOString().split('T')[0]
        }
      
      case 'lastYear':
        const year = selectedYear ? parseInt(selectedYear) : currentYear - 1
        return {
          start_date: `${year}-01-01`,
          end_date: `${year}-12-31`
        }
      
      case 'custom':
        return {
          start_date: customStartDate || '',
          end_date: customEndDate || ''
        }
      
      default:
        return {
          start_date: new Date(currentYear, currentMonth, 1).toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        }
    }
  }

  // Generate list of years (current year and 3 years prior)
  const getYearOptions = () => {
    const currentYear = new Date().getFullYear()
    return [
      currentYear - 3,
      currentYear - 2,
      currentYear - 1,
      currentYear
    ]
  }
  
  const currentYear = new Date().getFullYear()
  const [bsFilters, setBsFilters] = useState({
    year: currentYear.toString(),
    as_of_date: new Date().toISOString().split('T')[0]
  })

  const loadProfitLoss = async () => {
    setLoading(true)
    try {
      const dateRange = getDateRange(
        plFilters.dateFilterType,
        plFilters.selectedYear,
        plFilters.start_date,
        plFilters.end_date
      )
      
      // Validate custom date range
      if (plFilters.dateFilterType === 'custom' && (!dateRange.start_date || !dateRange.end_date)) {
        alert('Please select both start and end dates for custom date range')
        setLoading(false)
        return
      }
      
      const params = {
        start_date: dateRange.start_date,
        end_date: dateRange.end_date
      }
      
      console.log('Loading P&L with params:', params) // Debug log
      const response = await api.getProfitLoss(businessId, params)
      console.log('P&L Response:', response.data) // Debug log
      setProfitLoss(response.data)
    } catch (error) {
      console.error('Error loading profit & loss:', error)
      alert('Error loading report: ' + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
    }
  }

  const loadBalanceSheet = async () => {
    setLoading(true)
    try {
      const params = {
        year: bsFilters.year,
        as_of_date: bsFilters.as_of_date
      }
      const response = await api.getBalanceSheet(businessId, params)
      setBalanceSheet(response.data)
    } catch (error) {
      console.error('Error loading balance sheet:', error)
      alert('Error loading report: ' + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
    }
  }

  const buildAccountIdMaps = (accounts, bid) => {
    const byCanonical = new Map()
    const lineIdToCanonical = new Map()
    for (const acc of accounts) {
      if (acc.id === null || acc.id === undefined) continue
      const docId = String(acc.id)
      byCanonical.set(docId, acc)
      lineIdToCanonical.set(docId, docId)
      const legacy = acc.account_id
      if (legacy != null && legacy !== '') {
        lineIdToCanonical.set(String(legacy), docId)
        lineIdToCanonical.set(`account-${bid}-${legacy}`, docId)
      }
    }
    return { byCanonical, lineIdToCanonical }
  }

  const loadTransactionDetailsByAccount = async () => {
    setLoading(true)
    try {
      const dateRange = getDateRange(
        plFilters.dateFilterType,
        plFilters.selectedYear,
        plFilters.start_date,
        plFilters.end_date
      )
      if (plFilters.dateFilterType === 'custom' && (!dateRange.start_date || !dateRange.end_date)) {
        alert('Please select both start and end dates for custom date range')
        setLoading(false)
        return
      }

      const [txnRes, coaRes] = await Promise.all([
        api.getTransactions(businessId, {
          start_date: dateRange.start_date,
          end_date: dateRange.end_date
        }),
        api.getChartOfAccounts(businessId)
      ])

      const transactions = Array.isArray(txnRes.data) ? txnRes.data : []
      const accounts = Array.isArray(coaRes.data) ? coaRes.data : []
      const bid = parseInt(businessId, 10)
      const { byCanonical, lineIdToCanonical } = buildAccountIdMaps(accounts, bid)

      const groupsMap = new Map()

      const ensureGroup = (canonicalId, lineFallback) => {
        if (!groupsMap.has(canonicalId)) {
          const fromCoa = byCanonical.get(canonicalId)
          groupsMap.set(canonicalId, {
            canonicalId,
            account_code: fromCoa?.account_code ?? lineFallback?.account_code ?? '—',
            account_name: fromCoa?.account_name ?? lineFallback?.account_name ?? 'Unknown account',
            rows: [],
            totalDebit: 0,
            totalCredit: 0
          })
        }
        return groupsMap.get(canonicalId)
      }

      for (const txn of transactions) {
        for (const line of txn.lines || []) {
          const rawCoa = line.chart_of_account_id
          if (rawCoa === null || rawCoa === undefined || rawCoa === '') continue

          const rawStr = String(rawCoa)
          const canonicalId = lineIdToCanonical.get(rawStr) || rawStr
          const lineFallback = {
            account_code: line.account_code,
            account_name: line.account_name
          }
          const g = ensureGroup(canonicalId, lineFallback)
          const debit = parseFloat(line.debit_amount) || 0
          const credit = parseFloat(line.credit_amount) || 0
          g.rows.push({
            key: `${txn.id}-${g.rows.length}-${rawStr}`,
            transactionId: txn.id,
            date: txn.transaction_date,
            description: txn.description,
            reference: txn.reference_number,
            debit,
            credit,
            netAmount: debit > 0 ? debit : -credit
          })
          g.totalDebit += debit
          g.totalCredit += credit
        }
      }

      const groups = Array.from(groupsMap.values())
      for (const g of groups) {
        g.rows.sort((a, b) => {
          const da = String(a.date || '').split('T')[0]
          const db = String(b.date || '').split('T')[0]
          if (da !== db) return da.localeCompare(db)
          return String(a.transactionId).localeCompare(String(b.transactionId))
        })
      }
      groups.sort((a, b) => {
        const ca = a.account_code || ''
        const cb = b.account_code || ''
        const codeCmp = ca.localeCompare(cb, undefined, { numeric: true })
        if (codeCmp !== 0) return codeCmp
        return (a.account_name || '').localeCompare(b.account_name || '')
      })

      let grandDebit = 0
      let grandCredit = 0
      for (const g of groups) {
        grandDebit += g.totalDebit
        grandCredit += g.totalCredit
      }

      setTransactionDetailsByAccount({
        start_date: dateRange.start_date,
        end_date: dateRange.end_date,
        groups,
        grandDebit,
        grandCredit
      })
    } catch (error) {
      console.error('Error loading transaction details by account:', error)
      alert('Error loading report: ' + (error.response?.data?.error || error.message))
      setTransactionDetailsByAccount(null)
    } finally {
      setLoading(false)
    }
  }

  // Update as_of_date when year changes
  useEffect(() => {
    if (bsFilters.year) {
      const yearInt = parseInt(bsFilters.year)
      const isCurrentYear = yearInt === currentYear
      if (isCurrentYear) {
        // For current year, allow editing as_of_date, default to today
        if (!bsFilters.as_of_date || bsFilters.as_of_date.split('-')[0] !== bsFilters.year) {
          setBsFilters(prev => ({ ...prev, as_of_date: new Date().toISOString().split('T')[0] }))
        }
      } else {
        // For prior years, set to last day of that year (readonly)
        setBsFilters(prev => ({ ...prev, as_of_date: `${yearInt}-12-31` }))
      }
    }
  }, [bsFilters.year, currentYear])

  const loadAccountTransactions = async (account, startDate, endDate) => {
    setLoadingTransactions(true)
    setDrillDownAccount(account)
    try {
      const params = {
        account_id: account.id,
        start_date: startDate,
        end_date: endDate
      }
      console.log('DEBUG loadAccountTransactions:', {
        accountId: account.id,
        accountIdType: typeof account.id,
        accountCode: account.account_code,
        accountName: account.account_name,
        startDate,
        endDate,
        params
      })
      const response = await api.getTransactions(businessId, params)
      console.log('DEBUG loadAccountTransactions response:', {
        transactionCount: response.data.length,
        transactions: response.data.map(t => ({
          id: t.id,
          date: t.transaction_date,
          description: t.description,
          lines: t.lines?.map(l => ({
            chart_of_account_id: l.chart_of_account_id,
            debit: l.debit_amount,
            credit: l.credit_amount
          }))
        }))
      })
      setDrillDownTransactions(response.data)
    } catch (error) {
      console.error('Error loading account transactions:', error)
      alert('Error loading transactions: ' + (error.response?.data?.error || error.message))
      setDrillDownAccount(null)
    } finally {
      setLoadingTransactions(false)
    }
  }

  const loadBalanceSheetAccountTransactions = async (account, asOfDate) => {
    console.log('loadBalanceSheetAccountTransactions called:', { account, asOfDate, accountId: account.id })
    if (!account.id) {
      console.error('Account has no id:', account)
      alert('Cannot load transactions: Account ID is missing')
      return
    }
    setLoadingTransactions(true)
    setDrillDownAccount(account)
    try {
      // Load all transactions up to the as_of_date for this account
      const params = {
        account_id: account.id,
        end_date: asOfDate
      }
      console.log('Loading transactions with params:', params)
      const response = await api.getTransactions(businessId, params)
      console.log('Transactions loaded:', response.data.length, 'transactions')
      setDrillDownTransactions(response.data)
    } catch (error) {
      console.error('Error loading account transactions:', error)
      alert('Error loading transactions: ' + (error.response?.data?.error || error.message))
      setDrillDownAccount(null)
    } finally {
      setLoadingTransactions(false)
    }
  }

  const closeDrillDown = () => {
    setDrillDownAccount(null)
    setDrillDownTransactions([])
  }

  useEffect(() => {
    if (businessId) {
      loadBusiness()
    }
  }, [businessId])

  const loadBusiness = async () => {
    try {
      const response = await api.getBusiness(businessId)
      setBusiness(response.data)
    } catch (error) {
      console.error('Error loading business:', error)
    }
  }

  useEffect(() => {
    if (activeTab === 'profit-loss') {
      loadProfitLoss()
    } else if (activeTab === 'balance-sheet') {
      loadBalanceSheet()
    } else if (activeTab === 'transaction-details-by-account') {
      loadTransactionDetailsByAccount()
    }
  }, [activeTab])

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount || 0)
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Financial Reports</h1>
          <Link to={`/business/${businessId}`} className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            ← Back
          </Link>
        </div>

        <div className="tabs">
          <button
            className={`tab ${activeTab === 'profit-loss' ? 'active' : ''}`}
            onClick={() => setActiveTab('profit-loss')}
          >
            Profit & Loss
          </button>
          <button
            className={`tab ${activeTab === 'balance-sheet' ? 'active' : ''}`}
            onClick={() => setActiveTab('balance-sheet')}
          >
            Balance Sheet
          </button>
          <button
            className={`tab ${activeTab === 'transaction-details-by-account' ? 'active' : ''}`}
            onClick={() => setActiveTab('transaction-details-by-account')}
          >
            Transaction Details by Account
          </button>
        </div>

        {activeTab === 'profit-loss' && (
          <div>
            <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '4px' }}>
              <h3 style={{ marginTop: 0, marginBottom: '15px' }}>Date Filter</h3>
              
              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label>Period</label>
                <select
                  value={plFilters.dateFilterType}
                  onChange={(e) => {
                    const newType = e.target.value
                    setPlFilters({ 
                      ...plFilters, 
                      dateFilterType: newType,
                      // Reset custom dates when switching away from custom
                      start_date: newType === 'custom' ? plFilters.start_date : '',
                      end_date: newType === 'custom' ? plFilters.end_date : ''
                    })
                  }}
                  style={{ width: '100%', maxWidth: '400px' }}
                >
                  <option value="currentMonthToDate">Current Month To Date</option>
                  <option value="lastMonth">Last Month</option>
                  <option value="currentYearToDate">Current Year To Date</option>
                  <option value="lastYear">Last Year</option>
                  <option value="custom">Custom Date Range</option>
                </select>
              </div>

              {plFilters.dateFilterType === 'lastYear' && (
                <div className="form-group" style={{ marginBottom: '15px' }}>
                  <label>Select Year</label>
                  <select
                    value={plFilters.selectedYear}
                    onChange={(e) => setPlFilters({ ...plFilters, selectedYear: e.target.value })}
                    style={{ width: '100%', maxWidth: '200px' }}
                  >
                    {getYearOptions().map(year => (
                      <option key={year} value={year.toString()}>
                        {year}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {plFilters.dateFilterType === 'custom' && (
                <div className="form-group" style={{ marginBottom: '15px' }}>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      From:
                      <input
                        type="date"
                        value={plFilters.start_date}
                        onChange={(e) => setPlFilters({ ...plFilters, start_date: e.target.value })}
                      />
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      To:
                      <input
                        type="date"
                        value={plFilters.end_date}
                        onChange={(e) => setPlFilters({ ...plFilters, end_date: e.target.value })}
                      />
                    </label>
                  </div>
                </div>
              )}

              <div style={{ marginTop: '15px' }}>
                <button className="btn btn-primary" onClick={loadProfitLoss} disabled={loading}>
                  {loading ? 'Loading...' : 'Load Report'}
                </button>
              </div>
            </div>

            {profitLoss && (
              <div>
                <h2>Profit and Loss Statement{business ? ` for ${business.name}` : ''}</h2>
                <p>
                  Period: {new Date(profitLoss.start_date).toLocaleDateString()} - {new Date(profitLoss.end_date).toLocaleDateString()}
                </p>

                <table>
                  <thead>
                    <tr>
                      <th>Revenue</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profitLoss.revenue && profitLoss.revenue.length > 0 ? (
                      profitLoss.revenue.map((typeGroup) => (
                        <React.Fragment key={typeGroup.account_type_id}>
                          <tr style={{ fontWeight: 'bold', backgroundColor: '#f8f9fa' }}>
                            <td>{typeGroup.account_type_name}</td>
                            <td style={{ textAlign: 'right' }}>{formatCurrency(typeGroup.total)}</td>
                          </tr>
                          {typeGroup.accounts.map((account) => (
                            <tr key={account.id} style={{ paddingLeft: '20px' }}>
                              <td style={{ paddingLeft: '30px' }}>{account.account_code} - {account.account_name}</td>
                              <td style={{ textAlign: 'right' }}>
                                <a
                                  href="#"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    const dateRange = getDateRange(
                                      plFilters.dateFilterType,
                                      plFilters.selectedYear,
                                      plFilters.start_date,
                                      plFilters.end_date
                                    )
                                    loadAccountTransactions(account, dateRange.start_date, dateRange.end_date)
                                  }}
                                  style={{ color: '#007bff', textDecoration: 'underline', cursor: 'pointer' }}
                                >
                                  {formatCurrency(account.balance)}
                                </a>
                              </td>
                            </tr>
                          ))}
                        </React.Fragment>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" style={{ textAlign: 'center', color: '#999' }}>No revenue for this period</td>
                      </tr>
                    )}
                    <tr style={{ fontWeight: 'bold', borderTop: '2px solid #333' }}>
                      <td>Total Revenue</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(profitLoss.total_revenue)}</td>
                    </tr>
                  </tbody>
                </table>

                <table style={{ marginTop: '20px' }}>
                  <thead>
                    <tr>
                      <th>Expenses</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profitLoss.expenses && profitLoss.expenses.length > 0 ? (
                      profitLoss.expenses.map((typeGroup) => (
                        <React.Fragment key={typeGroup.account_type_id}>
                          <tr style={{ fontWeight: 'bold', backgroundColor: '#f8f9fa' }}>
                            <td>{typeGroup.account_type_name}</td>
                            <td style={{ textAlign: 'right' }}>{formatCurrency(typeGroup.total)}</td>
                          </tr>
                          {typeGroup.accounts.map((account) => (
                            <tr key={account.id} style={{ paddingLeft: '20px' }}>
                              <td style={{ paddingLeft: '30px' }}>{account.account_code} - {account.account_name}</td>
                              <td style={{ textAlign: 'right' }}>
                                <a
                                  href="#"
                                  onClick={(e) => {
                                    e.preventDefault()
                                    const dateRange = getDateRange(
                                      plFilters.dateFilterType,
                                      plFilters.selectedYear,
                                      plFilters.start_date,
                                      plFilters.end_date
                                    )
                                    loadAccountTransactions(account, dateRange.start_date, dateRange.end_date)
                                  }}
                                  style={{ color: '#007bff', textDecoration: 'underline', cursor: 'pointer' }}
                                >
                                  {formatCurrency(account.balance)}
                                </a>
                              </td>
                            </tr>
                          ))}
                        </React.Fragment>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" style={{ textAlign: 'center', color: '#999' }}>No expenses for this period</td>
                      </tr>
                    )}
                    <tr style={{ fontWeight: 'bold', borderTop: '2px solid #333' }}>
                      <td>Total Expenses</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(profitLoss.total_expenses)}</td>
                    </tr>
                  </tbody>
                </table>

                <table style={{ marginTop: '20px' }}>
                  <tbody>
                    <tr style={{ fontWeight: 'bold', fontSize: '18px', borderTop: '2px solid #333' }}>
                      <td>Net Income</td>
                      <td style={{ textAlign: 'right', color: profitLoss.net_income >= 0 ? '#28a745' : '#dc3545' }}>
                        {formatCurrency(profitLoss.net_income)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}

          </div>
        )}

        {/* Drill-down Transaction Report Modal - Shared for both P&L and Balance Sheet */}
        {drillDownAccount && (
          <div className="modal" onClick={closeDrillDown}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '900px', maxHeight: '80vh', overflow: 'auto' }}>
              <div className="modal-header">
                <h2>Transaction Details</h2>
                <button className="close-btn" onClick={closeDrillDown}>&times;</button>
              </div>
              
              <div style={{ marginBottom: '15px' }}>
                <p><strong>Account:</strong> {drillDownAccount.account_code} - {drillDownAccount.account_name}</p>
                {profitLoss && (
                  <p><strong>Period:</strong> {`${new Date(profitLoss.start_date).toLocaleDateString()} - ${new Date(profitLoss.end_date).toLocaleDateString()}`}</p>
                )}
                {balanceSheet && (
                  <p><strong>As of:</strong> {new Date(balanceSheet.as_of_date).toLocaleDateString()}</p>
                )}
                <p><strong>Total:</strong> {formatCurrency(drillDownAccount.balance)}</p>
              </div>

              {loadingTransactions ? (
                <div style={{ textAlign: 'center', padding: '20px' }}>Loading transactions...</div>
              ) : drillDownTransactions.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>No transactions found for this account in the selected period.</div>
              ) : (
                <div>
                  <table style={{ width: '100%', fontSize: '14px' }}>
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Description</th>
                        <th>Reference</th>
                        <th style={{ textAlign: 'right' }}>Debit</th>
                        <th style={{ textAlign: 'right' }}>Credit</th>
                        <th style={{ textAlign: 'right' }}>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {drillDownTransactions.map((txn) => {
                        // Find the line for this account - account IDs might be in different formats
                        // (UUID, integer, or old format strings) so we need to match all variants
                        const accountIdStr = String(drillDownAccount.id)
                        
                        // Build account ID variants to match (same logic as backend)
                        // The account object from P&L has id (UUID) but might not have account_id
                        // So we need to match by UUID, and also try to match by looking at all lines
                        const accountIdVariants = new Set([accountIdStr])
                        
                        // If account_id is available, add it as a variant
                        if (drillDownAccount.account_id !== undefined) {
                          accountIdVariants.add(String(drillDownAccount.account_id))
                          // Also add old format "account-{business_id}-{account_id}"
                          if (businessId) {
                            accountIdVariants.add(`account-${businessId}-${drillDownAccount.account_id}`)
                          }
                        }
                        
                        // Find the matching line - check against all variants
                        let accountLine = txn.lines?.find(line => {
                          const lineAccountId = line.chart_of_account_id
                          if (!lineAccountId) return false
                          // Check if line account ID matches any variant
                          const lineAccountIdStr = String(lineAccountId)
                          return accountIdVariants.has(lineAccountIdStr)
                        })
                        
                        // Fallback: If no match found, try to match by account_code
                        // This handles cases where account IDs don't match but we know the account_code
                        if (!accountLine && drillDownAccount.account_code && txn.lines) {
                          accountLine = txn.lines.find(line => {
                            // Try to match by account_code if available in the line
                            return line.account_code === drillDownAccount.account_code
                          })
                        }
                        
                        // Convert amounts to numbers, handling null/undefined/string values
                        const debitAmount = accountLine ? (parseFloat(accountLine.debit_amount) || 0) : 0
                        const creditAmount = accountLine ? (parseFloat(accountLine.credit_amount) || 0) : 0
                        const amount = debitAmount || -creditAmount
                        
                        return (
                          <tr key={txn.id}>
                            <td>{new Date(txn.transaction_date).toLocaleDateString()}</td>
                            <td>{txn.description || '-'}</td>
                            <td>{txn.reference_number || '-'}</td>
                            <td style={{ textAlign: 'right' }}>{debitAmount > 0 ? formatCurrency(debitAmount) : '-'}</td>
                            <td style={{ textAlign: 'right' }}>{creditAmount > 0 ? formatCurrency(creditAmount) : '-'}</td>
                            <td style={{ textAlign: 'right', fontWeight: 'bold' }}>{formatCurrency(amount)}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                    <tfoot>
                      <tr style={{ fontWeight: 'bold', borderTop: '2px solid #333' }}>
                        <td colSpan="5" style={{ textAlign: 'right' }}>Total:</td>
                        <td style={{ textAlign: 'right' }}>{formatCurrency(drillDownAccount.balance)}</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'transaction-details-by-account' && (
          <div>
            <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '4px' }}>
              <h3 style={{ marginTop: 0, marginBottom: '15px' }}>Date Filter</h3>

              <div className="form-group" style={{ marginBottom: '15px' }}>
                <label>Period</label>
                <select
                  value={plFilters.dateFilterType}
                  onChange={(e) => {
                    const newType = e.target.value
                    setPlFilters({
                      ...plFilters,
                      dateFilterType: newType,
                      start_date: newType === 'custom' ? plFilters.start_date : '',
                      end_date: newType === 'custom' ? plFilters.end_date : ''
                    })
                  }}
                  style={{ width: '100%', maxWidth: '400px' }}
                >
                  <option value="currentMonthToDate">Current Month To Date</option>
                  <option value="lastMonth">Last Month</option>
                  <option value="currentYearToDate">Current Year To Date</option>
                  <option value="lastYear">Last Year</option>
                  <option value="custom">Custom Date Range</option>
                </select>
              </div>

              {plFilters.dateFilterType === 'lastYear' && (
                <div className="form-group" style={{ marginBottom: '15px' }}>
                  <label>Select Year</label>
                  <select
                    value={plFilters.selectedYear}
                    onChange={(e) => setPlFilters({ ...plFilters, selectedYear: e.target.value })}
                    style={{ width: '100%', maxWidth: '200px' }}
                  >
                    {getYearOptions().map(year => (
                      <option key={year} value={year.toString()}>
                        {year}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {plFilters.dateFilterType === 'custom' && (
                <div className="form-group" style={{ marginBottom: '15px' }}>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      From:
                      <input
                        type="date"
                        value={plFilters.start_date}
                        onChange={(e) => setPlFilters({ ...plFilters, start_date: e.target.value })}
                      />
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      To:
                      <input
                        type="date"
                        value={plFilters.end_date}
                        onChange={(e) => setPlFilters({ ...plFilters, end_date: e.target.value })}
                      />
                    </label>
                  </div>
                </div>
              )}

              <div style={{ marginTop: '15px' }}>
                <button className="btn btn-primary" onClick={loadTransactionDetailsByAccount} disabled={loading}>
                  {loading ? 'Loading...' : 'Load Report'}
                </button>
              </div>
            </div>

            {transactionDetailsByAccount && (
              <div>
                <h2>Transaction Details by Account{business ? ` — ${business.name}` : ''}</h2>
                <p>
                  Period:{' '}
                  {new Date(transactionDetailsByAccount.start_date).toLocaleDateString()} —{' '}
                  {new Date(transactionDetailsByAccount.end_date).toLocaleDateString()}
                </p>

                {transactionDetailsByAccount.groups.length === 0 ? (
                  <p style={{ color: '#999' }}>No line items in this period.</p>
                ) : (
                  <>
                    {transactionDetailsByAccount.groups.map((g) => (
                      <div key={g.canonicalId} style={{ marginBottom: '28px' }}>
                        <h3 style={{ marginBottom: '10px', fontSize: '1.05rem' }}>
                          {g.account_code} — {g.account_name}
                        </h3>
                        <table style={{ width: '100%', fontSize: '14px' }}>
                          <thead>
                            <tr>
                              <th>Date</th>
                              <th>Description</th>
                              <th>Reference</th>
                              <th style={{ textAlign: 'right' }}>Debit</th>
                              <th style={{ textAlign: 'right' }}>Credit</th>
                              <th style={{ textAlign: 'right' }}>Amount</th>
                            </tr>
                          </thead>
                          <tbody>
                            {g.rows.map((row) => (
                              <tr key={row.key}>
                                <td>{row.date ? new Date(row.date).toLocaleDateString() : '—'}</td>
                                <td>{row.description || '—'}</td>
                                <td>{row.reference || '—'}</td>
                                <td style={{ textAlign: 'right' }}>
                                  {row.debit > 0 ? formatCurrency(row.debit) : '—'}
                                </td>
                                <td style={{ textAlign: 'right' }}>
                                  {row.credit > 0 ? formatCurrency(row.credit) : '—'}
                                </td>
                                <td style={{ textAlign: 'right', fontWeight: '500' }}>
                                  {formatCurrency(row.netAmount)}
                                </td>
                              </tr>
                            ))}
                            <tr style={{ fontWeight: 'bold', borderTop: '1px solid #ccc' }}>
                              <td colSpan="3" style={{ textAlign: 'right' }}>Account total</td>
                              <td style={{ textAlign: 'right' }}>{formatCurrency(g.totalDebit)}</td>
                              <td style={{ textAlign: 'right' }}>{formatCurrency(g.totalCredit)}</td>
                              <td style={{ textAlign: 'right' }}>
                                {formatCurrency(g.totalDebit - g.totalCredit)}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    ))}

                    <table style={{ marginTop: '8px', width: '100%', maxWidth: '480px' }}>
                      <tbody>
                        <tr style={{ fontWeight: 'bold', fontSize: '16px', borderTop: '2px solid #333' }}>
                          <td>Report totals (all debits / credits)</td>
                          <td style={{ textAlign: 'right' }}>
                            {formatCurrency(transactionDetailsByAccount.grandDebit)} /{' '}
                            {formatCurrency(transactionDetailsByAccount.grandCredit)}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'balance-sheet' && (
          <div>
            <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '4px' }}>
              <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div className="form-group">
                  <label>Year</label>
                  <select
                    value={bsFilters.year}
                    onChange={(e) => setBsFilters({ ...bsFilters, year: e.target.value })}
                    style={{ width: '150px' }}
                  >
                    {getYearOptions().map(y => (
                      <option key={y} value={y.toString()}>{y}</option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>As of Date</label>
                  <input
                    type="date"
                    value={bsFilters.as_of_date}
                    onChange={(e) => setBsFilters({ ...bsFilters, as_of_date: e.target.value })}
                    disabled={parseInt(bsFilters.year) !== currentYear}
                    readOnly={parseInt(bsFilters.year) !== currentYear}
                    style={{ width: '200px', opacity: parseInt(bsFilters.year) !== currentYear ? 0.6 : 1 }}
                  />
                </div>
                <button className="btn btn-primary" onClick={loadBalanceSheet} disabled={loading}>
                  {loading ? 'Loading...' : 'Load Report'}
                </button>
              </div>
            </div>

            {balanceSheet && (
              <div>
                <h2>Balance Sheet{business ? ` for ${business.name}` : ''}</h2>
                <p>As of: {new Date(balanceSheet.as_of_date).toLocaleDateString()}</p>

                <table>
                  <thead>
                    <tr>
                      <th>Assets</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {balanceSheet.assets.map((item, index) => {
                      // Make clickable if account has an ID (has chart of account, can have transactions)
                      const hasTransactions = !!item.id
                      const handleClick = (e) => {
                        e.preventDefault()
                        console.log('Account clicked:', item)
                        if (!item.id) {
                          console.error('Account has no id:', item)
                          alert('Cannot load transactions: Account ID is missing')
                          return
                        }
                        loadBalanceSheetAccountTransactions(item, balanceSheet.as_of_date)
                      }
                      return (
                        <tr key={index}>
                          <td>
                            {hasTransactions ? (
                              <a
                                href="#"
                                onClick={handleClick}
                                style={{ color: '#007bff', textDecoration: 'underline', cursor: 'pointer' }}
                              >
                                {item.account_code || '-'} - {item.account_name}
                              </a>
                            ) : (
                              `${item.account_code || '-'} - ${item.account_name}`
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                        </tr>
                      )
                    })}
                    <tr style={{ fontWeight: 'bold', borderTop: '2px solid #333' }}>
                      <td>Total Assets</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(balanceSheet.total_assets)}</td>
                    </tr>
                  </tbody>
                </table>

                <table style={{ marginTop: '20px' }}>
                  <thead>
                    <tr>
                      <th>Liabilities</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {balanceSheet.liabilities.map((item, index) => {
                      // Make clickable if account has an ID (has chart of account, can have transactions)
                      const hasTransactions = !!item.id
                      const handleClick = (e) => {
                        e.preventDefault()
                        console.log('Account clicked:', item)
                        if (!item.id) {
                          console.error('Account has no id:', item)
                          alert('Cannot load transactions: Account ID is missing')
                          return
                        }
                        loadBalanceSheetAccountTransactions(item, balanceSheet.as_of_date)
                      }
                      return (
                        <tr key={index}>
                          <td>
                            {hasTransactions ? (
                              <a
                                href="#"
                                onClick={handleClick}
                                style={{ color: '#007bff', textDecoration: 'underline', cursor: 'pointer' }}
                              >
                                {item.account_code || '-'} - {item.account_name}
                              </a>
                            ) : (
                              `${item.account_code || '-'} - ${item.account_name}`
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                        </tr>
                      )
                    })}
                    <tr style={{ fontWeight: 'bold', borderTop: '2px solid #333' }}>
                      <td>Total Liabilities</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(balanceSheet.total_liabilities)}</td>
                    </tr>
                  </tbody>
                </table>

                <table style={{ marginTop: '20px' }}>
                  <thead>
                    <tr>
                      <th>Equity</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {balanceSheet.equity.map((item, index) => {
                      // Skip retained earnings if it's a separate entry - we'll show it separately
                      if (item.is_retained_earnings) {
                        return null
                      }
                      
                      // Make clickable if account has an ID (has chart of account, can have transactions)
                      const hasTransactions = !!item.id
                      const handleClick = (e) => {
                        e.preventDefault()
                        console.log('Account clicked:', item)
                        if (!item.id) {
                          console.error('Account has no id:', item)
                          alert('Cannot load transactions: Account ID is missing')
                          return
                        }
                        loadBalanceSheetAccountTransactions(item, balanceSheet.as_of_date)
                      }
                      return (
                        <tr key={index}>
                          <td>
                            {hasTransactions ? (
                              <a
                                href="#"
                                onClick={handleClick}
                                style={{ color: '#007bff', textDecoration: 'underline', cursor: 'pointer' }}
                              >
                                {item.account_code || '-'} - {item.account_name}
                              </a>
                            ) : (
                              `${item.account_code || '-'} - ${item.account_name}`
                            )}
                          </td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.balance)}</td>
                        </tr>
                      )
                    })}
                    {/* Retained Earnings Breakdown */}
                    {balanceSheet.retained_earnings && (
                      <>
                        <tr>
                          <td style={{ paddingLeft: '20px' }}>
                            Prior Years Net Income (including Opening Balance)
                          </td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(balanceSheet.retained_earnings.prior_years_net_income)}</td>
                        </tr>
                        <tr>
                          <td style={{ paddingLeft: '20px' }}>
                            Net Income {balanceSheet.year ? `(${balanceSheet.year})` : '(Current Year)'} to {new Date(balanceSheet.as_of_date).toLocaleDateString()}
                          </td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(balanceSheet.retained_earnings.current_year_net_income)}</td>
                        </tr>
                        <tr style={{ fontWeight: 'bold' }}>
                          <td>Total Retained Earnings</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(balanceSheet.retained_earnings.total)}</td>
                        </tr>
                      </>
                    )}
                    <tr style={{ fontWeight: 'bold', borderTop: '2px solid #333' }}>
                      <td>Total Equity</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(balanceSheet.total_equity)}</td>
                    </tr>
                  </tbody>
                </table>

                <table style={{ marginTop: '20px' }}>
                  <tbody>
                    <tr style={{ fontWeight: 'bold', fontSize: '18px', borderTop: '2px solid #333' }}>
                      <td>Total Liabilities and Equity</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(balanceSheet.total_liabilities_and_equity)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default Reports

