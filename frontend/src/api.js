import axios from 'axios'

const API_BASE_URL = '/api'

const api = {
  // Businesses
  getBusinesses: () => axios.get(`${API_BASE_URL}/businesses`),
  getBusiness: (id) => axios.get(`${API_BASE_URL}/businesses/${id}`),
  createBusiness: (data) => axios.post(`${API_BASE_URL}/businesses`, data),
  updateBusiness: (id, data) => axios.put(`${API_BASE_URL}/businesses/${id}`, data),
  deleteBusiness: (id) => axios.delete(`${API_BASE_URL}/businesses/${id}`),
  
  // Chart of Accounts
  getChartOfAccounts: (businessId) => axios.get(`${API_BASE_URL}/businesses/${businessId}/chart-of-accounts`),
  createChartOfAccount: (businessId, data) => axios.post(`${API_BASE_URL}/businesses/${businessId}/chart-of-accounts`, data),
  updateChartOfAccount: (businessId, accountId, data) => axios.put(`${API_BASE_URL}/businesses/${businessId}/chart-of-accounts/${accountId}`, data),
  getAccountTypes: () => axios.get(`${API_BASE_URL}/account-types`),
  
  // Bank Accounts
  getBankAccounts: (businessId) => axios.get(`${API_BASE_URL}/businesses/${businessId}/bank-accounts`),
  createBankAccount: (businessId, data) => axios.post(`${API_BASE_URL}/businesses/${businessId}/bank-accounts`, data),
  
  // Credit Card Accounts
  getCreditCardAccounts: (businessId) => axios.get(`${API_BASE_URL}/businesses/${businessId}/credit-card-accounts`),
  createCreditCardAccount: (businessId, data) => axios.post(`${API_BASE_URL}/businesses/${businessId}/credit-card-accounts`, data),
  
  // Loan Accounts
  getLoanAccounts: (businessId) => axios.get(`${API_BASE_URL}/businesses/${businessId}/loan-accounts`),
  createLoanAccount: (businessId, data) => axios.post(`${API_BASE_URL}/businesses/${businessId}/loan-accounts`, data),
  
  // Transactions
  getTransactions: (businessId, params = {}) => axios.get(`${API_BASE_URL}/businesses/${businessId}/transactions`, { params }),
  createTransaction: (businessId, data) => axios.post(`${API_BASE_URL}/businesses/${businessId}/transactions`, data),
  updateTransaction: (businessId, transactionId, data) => axios.put(`${API_BASE_URL}/businesses/${businessId}/transactions/${transactionId}`, data),
  bulkUpdateTransactions: (businessId, data) => axios.put(`${API_BASE_URL}/businesses/${businessId}/transactions/bulk-update`, data),
  
  // Reports
  getProfitLoss: (businessId, params = {}) => axios.get(`${API_BASE_URL}/businesses/${businessId}/reports/profit-loss`, { params }),
  getBalanceSheet: (businessId, params = {}) => axios.get(`${API_BASE_URL}/businesses/${businessId}/reports/balance-sheet`, { params }),
  getCombinedProfitLoss: (params = {}) => axios.get(`${API_BASE_URL}/reports/combined-profit-loss`, { params }),
}

export default api

