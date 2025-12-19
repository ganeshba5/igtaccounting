import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'

function Hub() {
  const navigate = useNavigate()
  const [showNewBusinessModal, setShowNewBusinessModal] = useState(false)
  const [showMigrateModal, setShowMigrateModal] = useState(false)
  const [newBusinessName, setNewBusinessName] = useState('')
  const [sourceBusinessId, setSourceBusinessId] = useState('')
  const [targetBusinessId, setTargetBusinessId] = useState('')
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading] = useState(false)

  React.useEffect(() => {
    loadBusinesses()
  }, [])

  const loadBusinesses = async () => {
    try {
      const response = await api.getBusinesses()
      setBusinesses(response.data || [])
    } catch (error) {
      console.error('Error loading businesses:', error)
    }
  }

  const handleNewBusiness = async (e) => {
    e.preventDefault()
    if (!newBusinessName.trim()) {
      alert('Business name is required')
      return
    }
    setLoading(true)
    try {
      const response = await api.createBusiness({ name: newBusinessName })
      setShowNewBusinessModal(false)
      setNewBusinessName('')
      navigate(`/business/${response.data.id}`)
    } catch (error) {
      console.error('Error creating business:', error)
      alert('Error creating business: ' + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
    }
  }

  const handleMigrateChartOfAccounts = async (e) => {
    e.preventDefault()
    if (!sourceBusinessId || !targetBusinessId) {
      alert('Please select both source and target businesses')
      return
    }
    if (sourceBusinessId === targetBusinessId) {
      alert('Source and target businesses must be different')
      return
    }
    setLoading(true)
    try {
      // Get source chart of accounts
      const sourceAccounts = await api.getChartOfAccounts(sourceBusinessId)
      
      // Create accounts in target business
      let createdCount = 0
      let skippedCount = 0
      for (const account of sourceAccounts.data || []) {
        try {
          await api.createChartOfAccount(targetBusinessId, {
            account_code: account.account_code,
            account_name: account.account_name,
            description: account.description || '',
            account_type_id: account.account_type_id,
            parent_account_id: null // We'll handle parent relationships separately if needed
          })
          createdCount++
        } catch (error) {
          if (error.response?.status === 400 && error.response?.data?.error?.includes('already exists')) {
            skippedCount++
          } else {
            console.error(`Error creating account ${account.account_code}:`, error)
          }
        }
      }
      
      setShowMigrateModal(false)
      setSourceBusinessId('')
      setTargetBusinessId('')
      alert(`Migration complete! Created ${createdCount} accounts, skipped ${skippedCount} duplicates.`)
      navigate(`/business/${targetBusinessId}/chart-of-accounts`)
    } catch (error) {
      console.error('Error migrating chart of accounts:', error)
      alert('Error migrating chart of accounts: ' + (error.response?.data?.error || error.message))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Hub</h1>
          <Link to="/" className="btn btn-secondary" style={{ textDecoration: 'none' }}>
            ← Back to Businesses
          </Link>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div 
            className="card" 
            style={{ cursor: 'pointer', textAlign: 'center', padding: '30px' }}
            onClick={() => setShowNewBusinessModal(true)}
          >
            <div style={{ fontSize: '48px', marginBottom: '15px' }}>➕</div>
            <h3>New Business</h3>
            <p>Create a new business</p>
          </div>

          <Link 
            to="/reports/combined-profit-loss" 
            style={{ textDecoration: 'none' }}
          >
            <div className="card" style={{ cursor: 'pointer', textAlign: 'center', padding: '30px' }}>
              <div style={{ fontSize: '48px', marginBottom: '15px' }}>📊</div>
              <h3>Combined P&L Report</h3>
              <p>View combined profit and loss across all businesses</p>
            </div>
          </Link>

          <div 
            className="card" 
            style={{ cursor: 'pointer', textAlign: 'center', padding: '30px' }}
            onClick={() => setShowMigrateModal(true)}
          >
            <div style={{ fontSize: '48px', marginBottom: '15px' }}>📋</div>
            <h3>Migrate Chart of Accounts</h3>
            <p>Clone chart of accounts from one business to another</p>
          </div>
        </div>
      </div>

      {/* New Business Modal */}
      {showNewBusinessModal && (
        <div className="modal" onClick={() => setShowNewBusinessModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>New Business</h2>
              <button className="close-btn" onClick={() => setShowNewBusinessModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleNewBusiness}>
              <div className="form-group">
                <label>Business Name *</label>
                <input
                  type="text"
                  value={newBusinessName}
                  onChange={(e) => setNewBusinessName(e.target.value)}
                  required
                  autoFocus
                  disabled={loading}
                />
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setShowNewBusinessModal(false)}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Migrate Chart of Accounts Modal */}
      {showMigrateModal && (
        <div className="modal" onClick={() => setShowMigrateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Migrate (Clone) Chart of Accounts</h2>
              <button className="close-btn" onClick={() => setShowMigrateModal(false)}>&times;</button>
            </div>
            <form onSubmit={handleMigrateChartOfAccounts}>
              <div className="form-group">
                <label>Source Business (Copy From) *</label>
                <select
                  value={sourceBusinessId}
                  onChange={(e) => setSourceBusinessId(e.target.value)}
                  required
                  disabled={loading}
                >
                  <option value="">Select source business...</option>
                  {businesses.map(business => (
                    <option key={business.id} value={business.id}>{business.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Target Business (Copy To) *</label>
                <select
                  value={targetBusinessId}
                  onChange={(e) => setTargetBusinessId(e.target.value)}
                  required
                  disabled={loading}
                >
                  <option value="">Select target business...</option>
                  {businesses.map(business => (
                    <option key={business.id} value={business.id}>{business.name}</option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: '15px', padding: '10px', background: '#f8f9fa', borderRadius: '4px' }}>
                <small style={{ color: '#666' }}>
                  This will copy all chart of accounts from the source business to the target business. 
                  Accounts with duplicate codes will be skipped.
                </small>
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setShowMigrateModal(false)}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Migrating...' : 'Migrate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Hub

