/**
 * AS v2 — Axios Instance (Configured)
 *
 * Configured axios instance with:
 * - Base URL: /api
 * - Credentials: include (for session cookies)
 * - CSRF token in headers for mutating requests
 *
 * Issue #135: Usa ensureCsrfToken() para suportar CSRF_COOKIE_HTTPONLY=True
 *
 * Used by hooks and components.
 */

import axios from 'axios';
import { ensureCsrfToken, API_BASE } from './api/config';
import logger from './utils/logger';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add CSRF token to all mutating requests (Issue #135: async interceptor)
api.interceptors.request.use(async (config) => {
  const method = config.method?.toUpperCase();

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = await ensureCsrfToken();

    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    } else {
      logger.warn('CSRF token not found for mutating request');
      throw new Error('CSRF token ausente. Faça login novamente.');
    }
  }

  return config;
});

export default api;
