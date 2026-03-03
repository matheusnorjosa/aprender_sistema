/**
 * API Configuration - Centralized
 *
 * Provides:
 * - API_BASE: Base URL for all API calls
 * - CSRF helpers: getCsrfToken, ensureCsrfToken
 * - fetchAPI: Unified fetch wrapper with credentials and CSRF
 */
import logger from '../utils/logger';
import { TIMING } from '../constants';

/**
 * Fetch options for API calls
 */
export interface FetchOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
}

/**
 * Query parameters for building URLs
 */
export type QueryParams = Record<string, string | number | boolean | null | undefined>;

/**
 * Base API URL (can be overridden by VITE_API_URL env var)
 */
export const API_BASE: string = import.meta.env.VITE_API_URL || '/api';

/**
 * Extrai token CSRF do cookie 'csrftoken'.
 */
export function getCsrfToken(): string | null {
  const name = 'csrftoken';
  let cookieValue: string | null = null;

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
// Issue #258: Adiciona TTL para evitar token stale
let cachedCsrfToken: string | null = null;
let csrfTokenTimestamp: number | null = null;

/**
 * Limpa o cache de CSRF token (usar no logout ou em erro 401/403).
 */
export function clearCsrfCache(): void {
  cachedCsrfToken = null;
  csrfTokenTimestamp = null;
}

/**
 * Verifica se o token CSRF em cache ainda é válido (não expirou).
 */
function isCsrfTokenValid(): boolean {
  if (!cachedCsrfToken || !csrfTokenTimestamp) {
    return false;
  }
  const elapsed = Date.now() - csrfTokenTimestamp;
  return elapsed < TIMING.CSRF_TOKEN_TTL_MS;
}

/**
 * Busca um token CSRF fresco do servidor.
 */
async function fetchFreshCsrfToken(): Promise<string | null> {
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
        csrfTokenTimestamp = Date.now(); // Issue #258: Salvar timestamp
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
 * @param forceRefresh - Se true, ignora cache e busca token fresco
 */
export async function ensureCsrfToken(forceRefresh: boolean = false): Promise<string | null> {
  // Se forceRefresh, buscar token fresco diretamente
  if (forceRefresh) {
    return await fetchFreshCsrfToken();
  }

  // Tentativa 1: Ler do cookie (retrocompatibilidade)
  const token = getCsrfToken();
  if (token) {
    cachedCsrfToken = token;
    csrfTokenTimestamp = Date.now(); // Issue #258: Atualizar timestamp
    return token;
  }

  // Tentativa 2: Usar cache em memória se válido (Issue #258: verificar TTL)
  if (isCsrfTokenValid()) {
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
 * @param url - URL relativa (ex: '/solicitacoes/') ou absoluta
 * @param options - Opções do fetch (method, body, headers, etc.)
 * @param isRetry - Flag interna para evitar loop infinito de retry
 * @throws Error Se request falhar ou CSRF estiver ausente
 */
export async function fetchAPI<T = unknown>(url: string, options: FetchOptions = {}, isRetry: boolean = false): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;

  const headers: Record<string, string> = {
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

    // Issue #258: Invalidar cache em 401 (sessão expirada)
    if (response.status === 401) {
      clearCsrfCache();
    }

    const isAuthError = response.status === 401 || response.status === 403;
    const log = isAuthError ? logger.warn : logger.error;

    log('=== fetchAPI ERROR ===');
    log('Status:', response.status);
    log('StatusText:', response.statusText);
    log('Response body:', errorBody);

    let error: { detail?: string; message?: string };
    try {
      error = JSON.parse(errorBody);
    } catch {
      error = { detail: `HTTP ${response.status}: ${response.statusText}` };
    }

    const err = new Error(error.detail || error.message || `Erro ${response.status}`) as Error & {
      status?: number;
      response?: {
        status: number;
        data: unknown;
      };
    };
    err.status = response.status;
    err.response = {
      status: response.status,
      data: error,
    };
    throw err;
  }

  return response.json();
}

/**
 * Inicializa CSRF token proativamente.
 *
 * Chame no início do app para garantir que o token CSRF esteja disponível
 * antes de qualquer interação do usuário. Isso evita race conditions
 * onde o usuário tenta fazer login antes do token estar pronto.
 */
export async function initCsrfToken(): Promise<void> {
  try {
    await ensureCsrfToken();
    logger.debug('CSRF token inicializado com sucesso');
  } catch (error) {
    logger.warn('Falha ao inicializar CSRF token:', error);
  }
}

// Inicializar CSRF token automaticamente quando o módulo carrega
// Isso garante que o token está disponível assim que o app iniciar
initCsrfToken();

/**
 * Helper para construir URL com query params.
 *
 * @param path - Caminho relativo (ex: '/solicitacoes/')
 * @param params - Objeto com query params
 *
 * @example
 * buildUrl('/solicitacoes/', { status: 'pendente', q: 'sobral' })
 * // => '/api/solicitacoes/?status=pendente&q=sobral'
 */
export function buildUrl(path: string, params: QueryParams = {}): string {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      searchParams.append(key, String(value));
    }
  });

  const queryString = searchParams.toString();
  const separator = path.includes('?') ? '&' : '?';

  return queryString ? `${path}${separator}${queryString}` : path;
}
