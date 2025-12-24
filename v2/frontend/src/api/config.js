/**
 * API Configuration - Centralized
 *
 * Provides:
 * - API_BASE: Base URL for all API calls
 * - CSRF helpers: getCsrfToken, ensureCsrfToken
 * - fetchAPI: Unified fetch wrapper with credentials and CSRF
 */
import logger from '../utils/logger';

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
 * Limpa o cache de CSRF token (usar no logout).
 */
export function clearCsrfCache() {
  cachedCsrfToken = null;
}

/**
 * Busca um token CSRF fresco do servidor.
 *
 * @returns {Promise<string|null>} CSRF token fresco
 */
async function fetchFreshCsrfToken() {
  try {
    const response = await fetch(`${API_BASE}/csrf/`, {
      method: 'GET',
      credentials: 'include',
    });

    if (response.ok) {
      const data = await response.json();
      const token = data.csrfToken;

      if (token) {
        cachedCsrfToken = token;
        return token;
      }
    }
  } catch (error) {
    logger.warn('Erro ao obter CSRF token via /api/csrf/:', error);
  }
  return null;
}

/**
 * Garante que CSRF token existe, caso contrário faz request para obtê-lo.
 *
 * Issue #135: Suporta CSRF_COOKIE_HTTPONLY=True usando endpoint /api/csrf/
 * que retorna o token no body da resposta (acessível ao JavaScript).
 *
 * Estratégia:
 * 1. Tenta ler do cookie (retrocompatibilidade se HttpOnly=False)
 * 2. Se não conseguir, busca token fresco do servidor
 *
 * @param {boolean} forceRefresh - Se true, ignora cache e busca token fresco
 * @returns {Promise<string|null>} CSRF token
 */
export async function ensureCsrfToken(forceRefresh = false) {
  // Se forceRefresh, buscar token fresco diretamente
  if (forceRefresh) {
    return await fetchFreshCsrfToken();
  }

  // Tentativa 1: Ler do cookie (retrocompatibilidade)
  let token = getCsrfToken();
  if (token) {
    cachedCsrfToken = token; // Atualizar cache
    return token;
  }

  // Tentativa 2: Usar cache em memória (se não muito antigo)
  if (cachedCsrfToken) {
    return cachedCsrfToken;
  }

  // Tentativa 3: Obter via endpoint /api/csrf/ (Issue #135)
  return await fetchFreshCsrfToken();
}

/**
 * Wrapper genérico para fetch com autenticação, CSRF e tratamento de erros.
 *
 * Issue #135: Usa ensureCsrfToken() para suportar CSRF_COOKIE_HTTPONLY=True
 * Retry automático: Se receber erro CSRF (403 com "CSRF"), busca token fresco e retenta.
 *
 * @param {string} url - URL relativa (ex: '/solicitacoes/') ou absoluta
 * @param {object} options - Opções do fetch (method, body, headers, etc.)
 * @param {boolean} isRetry - Flag interna para evitar loop infinito de retry
 * @returns {Promise<object>} Response JSON
 * @throws {Error} Se request falhar ou CSRF estiver ausente
 */
export async function fetchAPI(url, options = {}, isRetry = false) {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Adicionar CSRF para métodos mutantes (Issue #135: usa ensureCsrfToken)
  const method = options.method?.toUpperCase() || 'GET';
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    // Se é retry, forçar refresh do token
    const csrfToken = await ensureCsrfToken(isRetry);

    if (!csrfToken) {
      logger.error('CSRF token não encontrado! Verifique se está autenticado.');
      throw new Error('CSRF token ausente. Faça login novamente.');
    }

    headers['X-CSRFToken'] = csrfToken;
  }

  logger.debug('=== fetchAPI ===');
  logger.debug('URL:', fullUrl);
  logger.debug('Method:', method);
  logger.debug('Headers:', headers);
  if (options.body) {
    logger.debug('Body:', options.body);
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers,
    credentials: 'include', // Sempre incluir cookies de sessão
  });

  if (!response.ok) {
    const errorBody = await response.text();

    // Detectar erro de CSRF e fazer retry com token fresco (apenas uma vez)
    if (response.status === 403 && errorBody.includes('CSRF') && !isRetry) {
      logger.warn('CSRF token inválido, buscando token fresco e retentando...');
      clearCsrfCache();
      return fetchAPI(url, options, true); // Retry com flag
    }

    logger.error('=== fetchAPI ERROR ===');
    logger.error('Status:', response.status);
    logger.error('StatusText:', response.statusText);
    logger.error('Response body:', errorBody);

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
