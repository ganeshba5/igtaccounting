import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api'

function BusinessDashboard() {
  const { businessId } = useParams()
  const [business, setBusiness] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBusiness()
  }, [businessId])

  const loadBusiness = async () => {
    try {
      const response = await api.getBusiness(businessId)
      setBusiness(response.data)
    } catch (error) {
      console.error('Error loading business:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="container loading">Loading...</div>
  }

  if (!business) {
    return <div className="container">Business not found</div>
  }

  return (
    <div className="container">
      <div className="card">
        <h1>{business.name}</h1>
        <p style={{ color: '#666', marginTop: '10px' }}>
          <Link to="/">← Back to Businesses</Link>
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
        <Link to={`/business/${businessId}/chart-of-accounts`} style={{ textDecoration: 'none' }}>
          <div className="card" style={{ cursor: 'pointer' }}>
            <h3>Chart of Accounts</h3>
            <p>Manage your accounts</p>
          </div>
        </Link>

        <Link to={`/business/${businessId}/bank-accounts`} style={{ textDecoration: 'none' }}>
          <div className="card" style={{ cursor: 'pointer' }}>
            <h3>Bank Accounts</h3>
            <p>Manage bank accounts</p>
          </div>
        </Link>

        <Link to={`/business/${businessId}/credit-cards`} style={{ textDecoration: 'none' }}>
          <div className="card" style={{ cursor: 'pointer' }}>
            <h3>Credit Cards</h3>
            <p>Manage credit card accounts</p>
          </div>
        </Link>

        <Link to={`/business/${businessId}/loans`} style={{ textDecoration: 'none' }}>
          <div className="card" style={{ cursor: 'pointer' }}>
            <h3>Loans</h3>
            <p>Manage loan accounts</p>
          </div>
        </Link>

        <Link to={`/business/${businessId}/transactions`} style={{ textDecoration: 'none' }}>
          <div className="card" style={{ cursor: 'pointer' }}>
            <h3>Transactions</h3>
            <p>Record and view transactions</p>
          </div>
        </Link>

        <Link to={`/business/${businessId}/reports`} style={{ textDecoration: 'none' }}>
          <div className="card" style={{ cursor: 'pointer' }}>
            <h3>Reports</h3>
            <p>View financial reports</p>
          </div>
        </Link>
      </div>
    </div>
  )
}

export default BusinessDashboard

