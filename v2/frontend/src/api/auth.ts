/**
 * API de Autenticação
 *
 * Endpoints:
 * - POST /api/auth/login/ - Login com username/password
 * - POST /api/auth/logout/ - Logout
 * - GET /api/me/ - Dados do usuário atual
 */

import { fetchAPI, clearCsrfCache } from './config';
import type { LoginResponse, AuthCheckResponse } from '../types';
import { assertCurrentUserPayload } from '../types';
import { isAuthError } from '../utils/errors';

/**
 * Realiza login com username e senha
 *
 * Nota: Django rotaciona o CSRF token após login bem-sucedido.
 * Limpamos o cache para forçar obtenção de token fresco.
 */
export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetchAPI<LoginResponse>('/auth/login/', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  // Limpar cache de CSRF token após login (Django rotaciona o token)
  clearCsrfCache();
  return response;
}

/**
 * Realiza logout
 */
export async function logout(): Promise<{ detail: string }> {
  const response = await fetchAPI<{ detail: string }>('/auth/logout/', {
    method: 'POST',
  });
  // Limpar cache de CSRF token após logout
  clearCsrfCache();
  return response;
}

/**
 * Verifica se o usuário está autenticado
 */
export async function checkAuth(): Promise<AuthCheckResponse> {
  try {
    const payload = await fetchAPI<unknown>('/me/');
    const user = assertCurrentUserPayload(payload);
    return { authenticated: true, user };
  } catch (error) {
    // #1741 (F2): só 401/403 significam "não autenticado". Um erro transitório
    // (5xx, blip de rede, throw de validação) NÃO deve se disfarçar de sessão
    // ausente — relança para o caller distinguir "deslogado" de "falhou".
    if (isAuthError(error)) {
      return { authenticated: false, user: null };
    }
    throw error;
  }
}
