/**
 * AS v2 — Axios Instance (Configured)
 *
 * Configured axios instance with:
 * - Base URL: /api
 * - Credentials: include (for session cookies)
 * - CSRF token in headers for mutating requests
 *
 * Used by hooks and components.
 */

import axios from 'axios';
import { getCsrfToken, API_BASE } from './api/config';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add CSRF token to all mutating requests
api.interceptors.request.use((config) => {
  const method = config.method?.toUpperCase();

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCsrfToken();

    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    } else {
      console.warn('CSRF token not found for mutating request');
    }
  }

  return config;
});

export default api;
