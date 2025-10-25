/**
 * API de Autenticação
 *
 * Endpoints:
 * - POST /api/auth/login/ - Login com username/password
 * - POST /api/auth/logout/ - Logout
 * - GET /api/me/ - Dados do usuário atual
 */

import { fetchAPI } from './config';

/**
 * Realiza login com username e senha
 */
export async function login(username, password) {
  const response = await fetchAPI('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  return response;
}

/**
 * Realiza logout
 */
export async function logout() {
  const response = await fetchAPI('/auth/logout/', {
    method: 'POST',
  });
  return response;
}

/**
 * Verifica se o usuário está autenticado
 */
export async function checkAuth() {
  try {
    const response = await fetchAPI('/me/');
    return { authenticated: true, user: response };
  } catch (error) {
    return { authenticated: false, user: null };
  }
}
