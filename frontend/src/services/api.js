import { auth } from './auth.js';

const API_BASE_URL = 'http://localhost:8001/api/v1';

class ApiService {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (auth.isAuthenticated()) {
      headers['Authorization'] = `Bearer ${auth.getToken()}`;
    }

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      
      if (response.status === 401) {
        // Unauthorized, maybe trigger logout
        auth.signOut();
        throw new Error('Unauthorized');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || errorData.message || 'API request failed');
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  get(endpoint, options) {
    return this.request(endpoint, { method: 'GET', ...options });
  }

  post(endpoint, data, options) {
    return this.request(endpoint, { method: 'POST', body: JSON.stringify(data), ...options });
  }

  put(endpoint, data, options) {
    return this.request(endpoint, { method: 'PUT', body: JSON.stringify(data), ...options });
  }

  delete(endpoint, options) {
    return this.request(endpoint, { method: 'DELETE', ...options });
  }
}

export const api = new ApiService();
