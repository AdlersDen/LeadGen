import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60s — discovery + pitch gen can be slow
});

// Global response interceptor for error normalization
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail =
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred';
    return Promise.reject(new Error(detail));
  }
);

export default apiClient;
