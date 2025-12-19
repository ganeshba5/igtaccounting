import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'

function Businesses() {
  const [businesses, setBusinesses] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingBusinessId, setEditingBusinessId] = useState(null)
  const [formData, setFormData] = useState({ name: '' })

  useEffect(() => {
    loadBusinesses()
  }, [])

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

  if (loading) {
    return <div className="container loading">Loading...</div>
  }

  return (
    <div className="container">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h1>Businesses</h1>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <Link to="/hub" className="btn btn-primary" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px' }}>⚙️</span>
              <span>Hub</span>
            </Link>
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
    </div>
  )
}

export default Businesses

