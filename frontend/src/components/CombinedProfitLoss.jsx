import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

function CombinedProfitLoss() {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  
  const [filters, setFilters] = useState({
    dateFilterType: 'currentYearToDate',
    selectedYear: (new Date().getFullYear() - 1).toString(),
    start_date: '',
    end_date: ''
  })

  // Helper function to get date range
  const getDateRange = (filterType, selectedYear = null, customStartDate = '', customEndDate = '') => {
    const now = new Date()
    const currentYear = now.getFullYear()

    switch (filterType) {
      case 'currentMonthToDate':
        return {
          start_date: new Date(currentYear, now.getMonth(), 1).toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        }
      case 'lastMonth':
        const lastMonth = new Date(currentYear, now.getMonth() - 1, 1)
        const lastMonthEnd = new Date(currentYear, now.getMonth(), 0)
        return {
          start_date: lastMonth.toISOString().split('T')[0],
          end_date: lastMonthEnd.toISOString().split('T')[0]
        }
      case 'currentYearToDate':
        return {
          start_date: new Date(currentYear, 0, 1).toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        }
      case 'lastYear':
        const year = selectedYear ? parseInt(selectedYear) : currentYear - 1
        return {
          start_date: new Date(year, 0, 1).toISOString().split('T')[0],
          end_date: new Date(year, 11, 31).toISOString().split('T')[0]
        }
      case 'custom':
        return {
          start_date: customStartDate || '',
          end_date: customEndDate || ''
        }
      default:
        return {
          start_date: new Date(currentYear, 0, 1).toISOString().split('T')[0],
          end_date: now.toISOString().split('T')[0]
        }
    }
  }

  const getYearOptions = () => {
    const currentYear = new Date().getFullYear()
    return [
      currentYear - 3,
      currentYear - 2,
      currentYear - 1,
      currentYear
    ]
  }

  const loadReport = async () => {
    setLoading(true)
    try {
      const dateRange = getDateRange(
        filters.dateFilterType,
        filters.selectedYear,
        filters.start_date,
        filters.end_date
      )
      
      if (filters.dateFilterType === 'custom' && (!dateRange.start_date || !dateRange.end_date)) {
        alert('Please select both start and end dates for custom date range')
        setLoading(false)
        return
      }

      const response = await api.getCombinedProfitLoss(dateRange)
      setReport(response.data)
    } catch (error) {
      console.error('Error loading combined P&L:', error)
      alert('Error loading report: ' + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReport()
  }, [])

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2
    }).format(amount)
  }

  const renderHierarchy = (items, level = 0) => {
    if (!items || items.length === 0) return null

    return (
      <div style={{ marginLeft: level > 0 ? `${level * 20}px` : '0' }}>
        {items.map((item, idx) => (
          <div key={idx} style={{ marginBottom: '5px' }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '5px 10px',
              backgroundColor: level === 0 ? '#f0f0f0' : level === 1 ? '#f5f5f5' : 'transparent',
              fontWeight: level <= 1 ? 'bold' : 'normal',
              borderLeft: level > 0 ? '3px solid #ccc' : 'none',
              marginLeft: level > 0 ? '10px' : '0'
            }}>
              <span>{item.account_name || item.business_name || item.account_type_name}</span>
              <span style={{ fontFamily: 'monospace' }}>{formatCurrency(item.total)}</span>
            </div>
            
            {item.children && renderHierarchy(item.children, level + 1)}
            
            {item.businesses && item.businesses.map((business, bizIdx) => (
              <div key={bizIdx} style={{ marginLeft: '20px' }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '5px 10px',
                  backgroundColor: '#fafafa',
                  fontWeight: 'bold',
                  borderLeft: '3px solid #999'
                }}>
                  <span>{business.business_name}</span>
                  <span style={{ fontFamily: 'monospace' }}>{formatCurrency(business.total)}</span>
                </div>
                
                {business.accounts && business.accounts.map((account, accIdx) => (
                  <div key={accIdx} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: '3px 10px',
                    marginLeft: '20px',
                    borderLeft: '2px solid #ddd'
                  }}>
                    <span>{account.account_name}</span>
                    <span style={{ fontFamily: 'monospace' }}>{formatCurrency(account.balance)}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>
    )
  }

  if (loading && !report) {
    return <div className="container loading">Loading...</div>
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Combined Profit & Loss Report</h1>
          <Link to="/" className="btn btn-secondary">Back to Home</Link>
        </div>

        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '5px' }}>
          <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div>
              <label style={{ marginRight: '5px' }}>Date Range:</label>
              <select
                value={filters.dateFilterType}
                onChange={(e) => setFilters({ ...filters, dateFilterType: e.target.value })}
              >
                <option value="currentMonthToDate">Current Month To Date</option>
                <option value="lastMonth">Last Month</option>
                <option value="currentYearToDate">Current Year To Date</option>
                <option value="lastYear">Last Year</option>
                <option value="custom">Custom Date Range</option>
              </select>
            </div>

            {filters.dateFilterType === 'lastYear' && (
              <div>
                <label style={{ marginRight: '5px' }}>Year:</label>
                <select
                  value={filters.selectedYear}
                  onChange={(e) => setFilters({ ...filters, selectedYear: e.target.value })}
                >
                  {getYearOptions().map(year => (
                    <option key={year} value={year.toString()}>{year}</option>
                  ))}
                </select>
              </div>
            )}

            {filters.dateFilterType === 'custom' && (
              <>
                <div>
                  <label style={{ marginRight: '5px' }}>Start Date:</label>
                  <input
                    type="date"
                    value={filters.start_date}
                    onChange={(e) => setFilters({ ...filters, start_date: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ marginRight: '5px' }}>End Date:</label>
                  <input
                    type="date"
                    value={filters.end_date}
                    onChange={(e) => setFilters({ ...filters, end_date: e.target.value })}
                  />
                </div>
              </>
            )}

            <button className="btn btn-primary" onClick={loadReport} disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {report && (
            <div style={{ marginTop: '10px', fontSize: '14px', color: '#666' }}>
              <strong>Period:</strong> {report.start_date} to {report.end_date}
            </div>
          )}
        </div>

        {report && (
          <>
            <h2>Revenue</h2>
            {report.revenue.length === 0 ? (
              <p>No revenue data for this period.</p>
            ) : (
              renderHierarchy(report.revenue)
            )}

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '10px',
              marginTop: '20px',
              backgroundColor: '#e8f5e9',
              fontWeight: 'bold',
              fontSize: '16px'
            }}>
              <span>Total Revenue</span>
              <span style={{ fontFamily: 'monospace' }}>{formatCurrency(report.total_revenue)}</span>
            </div>

            <h2 style={{ marginTop: '30px' }}>Expenses</h2>
            {report.expenses.length === 0 ? (
              <p>No expense data for this period.</p>
            ) : (
              renderHierarchy(report.expenses)
            )}

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '10px',
              marginTop: '20px',
              backgroundColor: '#ffebee',
              fontWeight: 'bold',
              fontSize: '16px'
            }}>
              <span>Total Expenses</span>
              <span style={{ fontFamily: 'monospace' }}>{formatCurrency(report.total_expenses)}</span>
            </div>

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '15px',
              marginTop: '20px',
              backgroundColor: report.net_income >= 0 ? '#c8e6c9' : '#ffcdd2',
              fontWeight: 'bold',
              fontSize: '18px',
              border: '2px solid #4caf50'
            }}>
              <span>Net Income</span>
              <span style={{ fontFamily: 'monospace' }}>{formatCurrency(report.net_income)}</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default CombinedProfitLoss

