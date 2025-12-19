import React, { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'

function Businesses() {
  const navigate = useNavigate()
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingBusinessId, setEditingBusinessId] = useState(null)
  const [formData, setFormData] = useState({ name: '' })
  const [showHubDropdown, setShowHubDropdown] = useState(false)
  const [showNewBusinessModal, setShowNewBusinessModal] = useState(false)
  const [showMigrateModal, setShowMigrateModal] = useState(false)
  const [newBusinessName, setNewBusinessName] = useState('')
  const [sourceBusinessId, setSourceBusinessId] = useState('')
  const [targetBusinessId, setTargetBusinessId] = useState('')
  const [migrateLoading, setMigrateLoading] = useState(false)
  const hubDropdownRef = useRef(null)

  useEffect(() => {
    loadBusinesses()
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (hubDropdownRef.current && !hubDropdownRef.current.contains(event.target)) {
        setShowHubDropdown(false)
      }
    }
    if (showHubDropdown) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showHubDropdown])

  const loadBusinesses = async () => {
    try {
      const response = await api.getBusinesses()
      setBusinesses(response.data || [])
    } catch (error) {
      console.error('Error loading businesses:', error)
      // Show user-friendly error message
      if (error.response?.status === 401) {
        alert('Authentication failed. Please sign in again.')
      } else {
        alert('Error loading businesses: ' + (error.response?.data?.error || error.message))
      }
      setBusinesses([]) // Set empty array on error
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      if (editingBusinessId) {
        await api.updateBusiness(editingBusinessId, formData)
      } else {
        await api.createBusiness(formData)
      }
      setShowModal(false)
      setEditingBusinessId(null)
      setFormData({ name: '' })
      loadBusinesses()
    } catch (error) {
      console.error(`Error ${editingBusinessId ? 'updating' : 'creating'} business:`, error)
      alert(`Error ${editingBusinessId ? 'updating' : 'creating'} business: ` + (error.response?.data?.error || error.message))
    }
  }

  const handleEdit = (business) => {
    setFormData({ name: business.name, passphrase: '' })
    setEditingBusinessId(business.id)
    setShowModal(true)
  }

  const handleCloseModal = () => {
    setShowModal(false)
    setEditingBusinessId(null)
    setFormData({ name: '' })
  }

  const handleNewBusiness = async (e) => {
    e.preventDefault()
    if (!newBusinessName.trim()) {
      alert('Business name is required')
      return
    }
    try {
      const response = await api.createBusiness({ name: newBusinessName })
      setShowNewBusinessModal(false)
      setShowHubDropdown(false)
      setNewBusinessName('')
      navigate(`/business/${response.data.id}`)
    } catch (error) {
      console.error('Error creating business:', error)
      alert('Error creating business: ' + (error.response?.data?.error || error.message))
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
    setMigrateLoading(true)
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
            parent_account_id: null
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
      setShowHubDropdown(false)
      setSourceBusinessId('')
      setTargetBusinessId('')
      alert(`Migration complete! Created ${createdCount} accounts, skipped ${skippedCount} duplicates.`)
      navigate(`/business/${targetBusinessId}/chart-of-accounts`)
    } catch (error) {
      console.error('Error migrating chart of accounts:', error)
      alert('Error migrating chart of accounts: ' + (error.response?.data?.error || error.message))
    } finally {
      setMigrateLoading(false)
    }
  }

  if (loading) {
    return <div className="container loading">Loading...</div>
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', position: 'relative' }}>
          <h1>Businesses</h1>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', position: 'relative' }} ref={hubDropdownRef}>
            <button 
              className="btn btn-primary" 
              onClick={() => setShowHubDropdown(!showHubDropdown)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <span style={{ fontSize: '18px' }}>⚙️</span>
              <span>Hub</span>
            </button>
            
            {showHubDropdown && (
              <div style={{
                position: 'fixed',
                top: '80px',
                right: '20px',
                backgroundColor: 'white',
                border: '1px solid #ddd',
                borderRadius: '8px',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                minWidth: '250px',
                zIndex: 1000,
                padding: '10px 0'
              }}>
                <div 
                  style={{
                    padding: '12px 20px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    borderBottom: '1px solid #eee'
                  }}
                  onClick={() => {
                    setShowNewBusinessModal(true)
                    setShowHubDropdown(false)
                  }}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#f5f5f5'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                >
                  <span style={{ fontSize: '20px' }}>➕</span>
                  <span>New Business</span>
                </div>
                
                <Link 
                  to="/reports/combined-profit-loss"
                  style={{ textDecoration: 'none', color: 'inherit' }}
                  onClick={() => setShowHubDropdown(false)}
                >
                  <div 
                    style={{
                      padding: '12px 20px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      borderBottom: '1px solid #eee'
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = '#f5f5f5'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                  >
                    <span style={{ fontSize: '20px' }}>📊</span>
                    <span>Combined P&L Report</span>
                  </div>
                </Link>
                
                <div 
                  style={{
                    padding: '12px 20px',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px'
                  }}
                  onClick={() => {
                    setShowMigrateModal(true)
                    setShowHubDropdown(false)
                  }}
                  onMouseEnter={(e) => e.target.style.backgroundColor = '#f5f5f5'}
                  onMouseLeave={(e) => e.target.style.backgroundColor = 'white'}
                >
                  <span style={{ fontSize: '20px' }}>📋</span>
                  <span>Migrate Chart of Accounts</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {businesses.length === 0 ? (
          <p>No businesses found. Create your first business to get started.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {businesses.map((business) => (
                <tr key={business.id}>
                  <td>
                    <Link to={`/business/${business.id}`}>{business.name}</Link>
                  </td>
                  <td>{new Date(business.created_at).toLocaleDateString()}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button
                        className="btn btn-secondary"
                        onClick={() => handleEdit(business)}
                        style={{ padding: '5px 10px', fontSize: '12px' }}
                      >
                        Edit
                      </button>
                      <Link to={`/business/${business.id}`} className="btn btn-primary" style={{ textDecoration: 'none', display: 'inline-block', padding: '5px 10px', fontSize: '12px' }}>
                        Open
                      </Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="modal" onClick={handleCloseModal}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingBusinessId ? 'Edit Business' : 'New Business'}</h2>
              <button className="close-btn" onClick={handleCloseModal}>&times;</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Business Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  autoFocus
                />
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button type="button" className="btn btn-secondary" onClick={handleCloseModal}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  {editingBusinessId ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Business Modal from Hub */}
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
                />
              </div>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  onClick={() => setShowNewBusinessModal(false)}
                >
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
                  disabled={migrateLoading}
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
                  disabled={migrateLoading}
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
                  disabled={migrateLoading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={migrateLoading}>
                  {migrateLoading ? 'Migrating...' : 'Migrate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Businesses

