import React, { useState } from 'react'
import { useAuth } from '../auth/AuthContext'

function Login() {
  const { login, loginRedirect } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleLogin = async (usePopup = true) => {
    setLoading(true)
    setError(null)
    try {
      if (usePopup) {
        await login()
      } else {
        loginRedirect()
      }
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
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <button
              className="btn btn-primary"
              onClick={() => handleLogin(true)}
              disabled={loading}
              style={{ width: '100%', padding: '12px' }}
            >
              {loading ? 'Signing in...' : 'Sign in with Microsoft (Popup)'}
            </button>
            
            <button
              className="btn btn-secondary"
              onClick={() => handleLogin(false)}
              disabled={loading}
              style={{ width: '100%', padding: '12px' }}
            >
              Sign in with Microsoft (Redirect)
            </button>
          </div>
          
          <div style={{ marginTop: '30px', padding: '20px', background: '#f8f9fa', borderRadius: '4px' }}>
            <p style={{ fontSize: '12px', color: '#666', margin: 0 }}>
              <strong>Note:</strong> This application uses Microsoft Single Sign-On (SSO) for secure authentication.
              You'll be redirected to Microsoft's login page to sign in with your work or personal Microsoft account.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login

