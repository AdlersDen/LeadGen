// This file is intentionally minimal.
// All API calls are made via src/api/apiClient.js pointing at http://localhost:8000
// No external BaaS or low-code SDK is used.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
