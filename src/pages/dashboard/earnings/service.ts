// In your service.ts or api configuration file

import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 0, // NO TIMEOUT - requests will wait indefinitely
  headers: {
    'Content-Type': 'application/json'
  }
});

// Or if you want a very long timeout instead of none:
// timeout: 60000, // 60 seconds

// Add request interceptor to include auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token') || 
                  localStorage.getItem('token') || 
                  localStorage.getItem('authToken');
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;

// Export earnings API endpoints
// In your service.ts file, update the earningsAPI object:

export const earningsAPI = {
  getCurrentUser: () => api.get('/user/me'),
  getReferralStats: () => api.get('/api/referrals/stats'),
  getEarningsSummary: () => api.get('/earnings/summary'),
  getMonthlyPerformance: (year: number, month: number) => 
    api.get(`/earnings/monthly/${year}/${month}`),
  getAvailableYears: () => api.get('/earnings/available-years')
};