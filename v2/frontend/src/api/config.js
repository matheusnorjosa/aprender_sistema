/**
 * API Configuration - Centralized
 *
 * Provides:
 * - API_BASE: Base URL for all API calls
 * - CSRF helpers: getCsrfToken, ensureCsrfToken
 * - fetchAPI: Unified fetch wrapper with credentials and CSRF
 */

/**
 * Base API URL (can be overridden by VITE_API_URL env var)
 */
export const API_BASE = import.meta.env.VITE_API_URL || '/api';

/**
 * Extrai token CSRF do cookie 'csrftoken'.
 *
 * @returns {string|null} CSRF token ou null se não encontrado
 */
export function getCsrfToken() {
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

// Cache de token CSRF em memória (Issue #135 - suporte a HttpOnly)
let cachedCsrfToken = null;

/**
 * Garante que CSRF token existe, caso contrário faz request para obtê-lo.
 *
 * Issue #135: Suporta CSRF_COOKIE_HTTPONLY=True usando endpoint /api/csrf/
 * que retorna o token no body da resposta (acessível ao JavaScript).
 *
 * Estratégia:
 * 1. Tenta ler do cookie (retrocompatibilidade se HttpOnly=False)
 * 2. Se não conseguir, usa cache em memória
 * 3. Se cache vazio, chama /api/csrf/ e lê do body da resposta
 *
 * @returns {Promise<string|null>} CSRF token
 */
export async function ensureCsrfToken() {
  // Tentativa 1: Ler do cookie (retrocompatibilidade)
  let token = getCsrfToken();
  if (token) {
    cachedCsrfToken = token; // Atualizar cache
    return token;
  }

  // Tentativa 2: Usar cache em memória
  if (cachedCsrfToken) {
    return cachedCsrfToken;
  }

  // Tentativa 3: Obter via endpoint /api/csrf/ (Issue #135)
  try {
    const response = await fetch(`${API_BASE}/csrf/`, {
      method: 'GET',
      credentials: 'include',
    });

    if (response.ok) {
      const data = await response.json();
      token = data.csrfToken;

      if (token) {
        cachedCsrfToken = token; // Cachear em memória
        return token;
      }
    }
  } catch (error) {
    console.warn('Erro ao obter CSRF token via /api/csrf/:', error);
  }

  // Fallback: retornar null e deixar request falhar com mensagem clara
  return null;
}

/**
 * Wrapper genérico para fetch com autenticação, CSRF e tratamento de erros.
 *
 * Issue #135: Usa ensureCsrfToken() para suportar CSRF_COOKIE_HTTPONLY=True
 *
 * @param {string} url - URL relativa (ex: '/solicitacoes/') ou absoluta
 * @param {object} options - Opções do fetch (method, body, headers, etc.)
 * @returns {Promise<object>} Response JSON
 * @throws {Error} Se request falhar ou CSRF estiver ausente
 */
export async function fetchAPI(url, options = {}) {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Adicionar CSRF para métodos mutantes (Issue #135: usa ensureCsrfToken)
  const method = options.method?.toUpperCase() || 'GET';
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = await ensureCsrfToken();

    if (!csrfToken) {
      console.error('CSRF token não encontrado! Verifique se está autenticado.');
      throw new Error('CSRF token ausente. Faça login novamente.');
    }

    headers['X-CSRFToken'] = csrfToken;
  }

  console.log('=== fetchAPI DEBUG ===');
  console.log('URL:', fullUrl);
  console.log('Method:', method);
  console.log('Headers:', headers);
  if (options.body) {
    console.log('Body:', options.body);
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers,
    credentials: 'include', // Sempre incluir cookies de sessão
  });

  if (!response.ok) {
    console.error('=== fetchAPI ERROR ===');
    console.error('Status:', response.status);
    console.error('StatusText:', response.statusText);

    const errorBody = await response.text();
    console.error('Response body:', errorBody);

    let error;
    try {
      error = JSON.parse(errorBody);
    } catch {
      error = { detail: `HTTP ${response.status}: ${response.statusText}` };
    }

    throw new Error(error.detail || error.message || `Erro ${response.status}`);
  }

  return response.json();
}

/**
 * Helper para construir URL com query params.
 *
 * @param {string} path - Caminho relativo (ex: '/solicitacoes/')
 * @param {object} params - Objeto com query params
 * @returns {string} URL completa com params
 *
 * @example
 * buildUrl('/solicitacoes/', { status: 'pendente', q: 'sobral' })
 * // => '/api/solicitacoes/?status=pendente&q=sobral'
 */
export function buildUrl(path, params = {}) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, value);
    }
  });

  const queryString = searchParams.toString();
  const separator = path.includes('?') ? '&' : '?';

  return queryString ? `${path}${separator}${queryString}` : path;
}
