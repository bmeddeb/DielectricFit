/**
 * API Utilities - Shared API client functionality
 * Provides standardized API calls with CSRF protection and error handling
 */

// CSRF token utility
function getCsrfToken() {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Generic API client class
class ApiClient {
  constructor() {
    this.csrfToken = getCsrfToken();
  }
  
  // GET request
  async get(url) {
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin'
      });
      return await response.json();
    } catch (error) {
      console.error('API GET error:', error);
      throw error;
    }
  }
  
  // POST request
  async post(url, data = {}) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken
        },
        body: JSON.stringify(data),
        credentials: 'same-origin'
      });
      return await response.json();
    } catch (error) {
      console.error('API POST error:', error);
      throw error;
    }
  }
  
  // PUT request
  async put(url, data = {}) {
    try {
      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.csrfToken
        },
        body: JSON.stringify(data),
        credentials: 'same-origin'
      });
      return await response.json();
    } catch (error) {
      console.error('API PUT error:', error);
      throw error;
    }
  }
  
  // DELETE request
  async delete(url) {
    try {
      const response = await fetch(url, {
        method: 'DELETE',
        headers: {
          'X-CSRFToken': this.csrfToken
        },
        credentials: 'same-origin'
      });
      return await response.json();
    } catch (error) {
      console.error('API DELETE error:', error);
      throw error;
    }
  }
  
  // Form data POST (for file uploads)
  async postFormData(url, formData) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': this.csrfToken
        },
        body: formData,
        credentials: 'same-origin'
      });
      return await response.json();
    } catch (error) {
      console.error('API Form POST error:', error);
      throw error;
    }
  }
}

// Global API client instance
const api = new ApiClient();

// Specific API endpoints for common operations
const ApiEndpoints = {
  // Dataset endpoints
  datasets: {
    list: () => api.get('/api/datasets/'),
    upload: (formData) => api.postFormData('/api/datasets/upload/', formData),
    update: (id, data) => api.post(`/api/datasets/${id}/update/`, data),
    delete: (id) => api.delete(`/api/datasets/${id}/`),
    move: (id, targetProjectId) => api.post(`/api/datasets/${id}/move/`, { target_project_id: targetProjectId }),
    getData: (id) => api.get(`/api/datasets/${id}/data/`)
  },
  
  // Project endpoints  
  projects: {
    list: () => api.get('/api/projects/'),
    create: (data) => api.post('/api/projects/create/', data),
    update: (id, data) => api.post(`/api/projects/${id}/update/`, data),
    delete: (id) => api.delete(`/api/projects/${id}/delete/`),
    switch: (projectId) => api.post('/api/projects/switch/', { project_id: projectId })
  },
  
  // Profile endpoints
  profile: {
    update: (data) => api.post('/api/profile/update/', data),
    getProjects: () => api.get('/api/profile/projects/')
  }
};

// Error handling wrapper for API calls
async function handleApiCall(apiCall, errorMessage = 'An error occurred') {
  try {
    const result = await apiCall();
    return result;
  } catch (error) {
    console.error('API call failed:', error);
    if (typeof showNotification === 'function') {
      showNotification('Error', errorMessage, 'error');
    }
    throw error;
  }
}

// Export for module systems if available
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ApiClient, api, ApiEndpoints, handleApiCall, getCsrfToken };
}