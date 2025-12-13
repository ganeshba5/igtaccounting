import axios from 'axios'

// Support environment-based API URL
// In development: uses relative '/api' (proxied by Vite)
// In production: uses environment variable or detects Static Web Apps and uses backend URL
const getApiBaseUrl = () => {
  // If environment variable is set (build time), use it
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }
  
  // Detect production Static Web Apps environment
  const hostname = window.location.hostname
  if (hostname.includes('azurestaticapps.net')) {
    // Production: point to backend API
    return 'https://igtacct-api-azaghzb4chhagvc3.eastus-01.azurewebsites.net/api'
  }
  
  // Development: use relative path (proxied by Vite)
  return '/api'
}

const API_BASE_URL = getApiBaseUrl()

// Create axios instance with interceptor for auth tokens
// Note: baseURL is set to '/api', so API calls should NOT include '/api' prefix
const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
})

// Interceptor to add auth token to requests
let getAccessToken = null

export const setAuthTokenGetter = (tokenGetter) => {
  getAccessToken = tokenGetter
}

axiosInstance.interceptors.request.use(
  async (config) => {
    if (getAccessToken) {
      try {
        const token = await getAccessToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
          console.log('Token added to request:', config.url)
        } else {
          console.warn('No token available for request:', config.url)
        }
      } catch (error) {
        console.error('Error getting token for request:', error)
      }
    } else {
      console.warn('Token getter not registered')
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Export axiosInstance for use in components
export { axiosInstance }

// Handle 401 responses (unauthorized)
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - user will need to re-login
      console.error('Authentication failed (401). Error:', error.response?.data)
      console.error('Request URL:', error.config?.url)
      console.error('Request headers:', error.config?.headers)
    } else if (error.response) {
      console.error('API Error:', error.response.status, error.response.data)
    } else {
      console.error('Network Error:', error.message)
    }
    return Promise.reject(error)
  }
)

// Store axiosInstance in api object for access
const api = {
  axiosInstance,
  // Businesses
  // Note: baseURL is already '/api', so paths should NOT include '/api' prefix
  getBusinesses: () => axiosInstance.get('/businesses'),
  getBusiness: (id) => axiosInstance.get(`/businesses/${id}`),
  createBusiness: (data) => axiosInstance.post('/businesses', data),
  updateBusiness: (id, data) => axiosInstance.put(`/businesses/${id}`, data),
  deleteBusiness: (id) => axiosInstance.delete(`/businesses/${id}`),
  
  // Chart of Accounts
  getChartOfAccounts: (businessId) => axiosInstance.get(`/businesses/${businessId}/chart-of-accounts`),
  createChartOfAccount: (businessId, data) => axiosInstance.post(`/businesses/${businessId}/chart-of-accounts`, data),
  updateChartOfAccount: (businessId, accountId, data) => axiosInstance.put(`/businesses/${businessId}/chart-of-accounts/${accountId}`, data),
  getAccountTypes: () => axiosInstance.get('/account-types'),
  
  // Bank Accounts
  getBankAccounts: (businessId) => axiosInstance.get(`/businesses/${businessId}/bank-accounts`),
  createBankAccount: (businessId, data) => axiosInstance.post(`/businesses/${businessId}/bank-accounts`, data),
  
  // Credit Card Accounts
  getCreditCardAccounts: (businessId) => axiosInstance.get(`/businesses/${businessId}/credit-card-accounts`),
  createCreditCardAccount: (businessId, data) => axiosInstance.post(`/businesses/${businessId}/credit-card-accounts`, data),
  
  // Loan Accounts
  getLoanAccounts: (businessId) => axiosInstance.get(`/businesses/${businessId}/loan-accounts`),
  createLoanAccount: (businessId, data) => axiosInstance.post(`/businesses/${businessId}/loan-accounts`, data),
  
  // Transactions
  getTransactions: (businessId, params = {}) => axiosInstance.get(`/businesses/${businessId}/transactions`, { params }),
  createTransaction: (businessId, data) => axiosInstance.post(`/businesses/${businessId}/transactions`, data),
  updateTransaction: (businessId, transactionId, data) => axiosInstance.put(`/businesses/${businessId}/transactions/${transactionId}`, data),
  bulkUpdateTransactions: (businessId, data) => axiosInstance.put(`/businesses/${businessId}/transactions/bulk-update`, data),
  
  // Reports
  getProfitLoss: (businessId, params = {}) => axiosInstance.get(`/businesses/${businessId}/reports/profit-loss`, { params }),
  getBalanceSheet: (businessId, params = {}) => axiosInstance.get(`/businesses/${businessId}/reports/balance-sheet`, { params }),
  getCombinedProfitLoss: (params = {}) => axiosInstance.get('/reports/combined-profit-loss', { params }),
}

export default api

