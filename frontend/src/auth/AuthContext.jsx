import React, { createContext, useContext, useState, useEffect } from 'react'
import { PublicClientApplication } from '@azure/msal-browser'
import { setAuthTokenGetter } from '../api'

// MSAL configuration
// Get redirect URI from environment variable or use current origin
const getRedirectUri = () => {
  // Allow override via environment variable
  if (import.meta.env.VITE_AZURE_REDIRECT_URI) {
    return import.meta.env.VITE_AZURE_REDIRECT_URI
  }
  // Default to current origin (works for both dev and production)
  return window.location.origin
}

const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || '',
    authority: import.meta.env.VITE_AZURE_AUTHORITY || `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID || ''}`,
    redirectUri: getRedirectUri(),
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
}

// Scopes required for the application
const loginRequest = {
  scopes: ['User.Read'],
}

// Create MSAL instance
const msalInstance = new PublicClientApplication(msalConfig)

// Initialize MSAL
msalInstance.initialize().then(() => {
  // Handle redirect response
  msalInstance.handleRedirectPromise().catch((error) => {
    console.error('Error handling redirect:', error)
  })
})

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [accessToken, setAccessToken] = useState(null)

  const getAccessToken = async () => {
    try {
      const accounts = msalInstance.getAllAccounts()
      if (accounts.length === 0) {
        console.log('No accounts found, cannot get access token')
        return null
      }

      const response = await msalInstance.acquireTokenSilent({
        ...loginRequest,
        account: accounts[0],
      })
      
      if (response && response.accessToken) {
        setAccessToken(response.accessToken)
        console.log('Access token acquired successfully')
        return response.accessToken
      }
      return null
    } catch (error) {
      console.error('Error acquiring token silently:', error)
      // If silent token acquisition fails, try interactive
      if (error.errorCode === 'interaction_required' || error.errorCode === 'consent_required') {
        console.log('Interaction required, attempting interactive login...')
        try {
          const interactiveResponse = await msalInstance.acquireTokenPopup(loginRequest)
          if (interactiveResponse && interactiveResponse.accessToken) {
            setAccessToken(interactiveResponse.accessToken)
            return interactiveResponse.accessToken
          }
        } catch (popupError) {
          console.error('Error with interactive token acquisition:', popupError)
        }
      }
      return null
    }
  }

  useEffect(() => {
    const initializeAuth = async () => {
      // Check if user is already logged in
      const accounts = msalInstance.getAllAccounts()
      if (accounts.length > 0) {
        msalInstance.setActiveAccount(accounts[0])
        setIsAuthenticated(true)
        setUser(accounts[0])
        // Get access token immediately
        const token = await getAccessToken()
        if (token) {
          console.log('Initial token acquired on mount')
        } else {
          console.warn('Failed to acquire initial token')
        }
      }
      setLoading(false)
      
      // Register token getter with API
      setAuthTokenGetter(getAccessToken)
    }
    
    initializeAuth()
  }, [])

  const login = async () => {
    try {
      const response = await msalInstance.loginPopup(loginRequest)
      msalInstance.setActiveAccount(response.account)
      setIsAuthenticated(true)
      setUser(response.account)
      setAccessToken(response.accessToken)
      return response.accessToken
    } catch (error) {
      console.error('Login error:', error)
      throw error
    }
  }

  const loginRedirect = () => {
    msalInstance.loginRedirect(loginRequest)
  }

  const logout = () => {
    msalInstance.logoutPopup({
      postLogoutRedirectUri: getRedirectUri(),
    })
    setIsAuthenticated(false)
    setUser(null)
    setAccessToken(null)
  }

  const value = {
    isAuthenticated,
    user,
    loading,
    accessToken,
    login,
    loginRedirect,
    logout,
    getAccessToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

