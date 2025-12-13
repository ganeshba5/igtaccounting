import React, { useState } from 'react'
import { useAuth } from '../auth/AuthContext'

function Login() {
  const { login } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleLogin = async () => {
    setLoading(true)
    setError(null)
    try {
      await login()
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.')
      setLoading(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: '500px', margin: '100px auto' }}>
      <div className="card">
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <h1>Accounting System</h1>
          <p style={{ color: '#666', marginBottom: '30px' }}>
            Sign in with your Microsoft account to continue
          </p>
          
          {error && (
            <div style={{ 
              background: '#fee', 
              color: '#c33', 
              padding: '10px', 
              borderRadius: '4px', 
              marginBottom: '20px' 
            }}>
              {error}
            </div>
          )}
          
          <button
            className="btn btn-primary"
            onClick={handleLogin}
            disabled={loading}
            style={{ width: '100%', padding: '12px' }}
          >
            {loading ? 'Signing in...' : 'Sign in with Microsoft'}
          </button>
          
          <div style={{ marginTop: '30px', padding: '20px', background: '#f8f9fa', borderRadius: '4px' }}>
            <p style={{ fontSize: '12px', color: '#666', margin: 0 }}>
              <strong>Note:</strong> This application uses Microsoft Single Sign-On (SSO) for secure authentication.
              A popup window will open for you to sign in with your work or personal Microsoft account.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login

