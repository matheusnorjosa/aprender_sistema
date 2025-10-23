/**
 * API Client - Google Calendar Dashboard (PR14)
 *
 * Endpoints para painel de publicação GCal.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002/api';

/**
 * Extrai token CSRF do cookie.
 */
function getCSRFToken() {
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

/**
 * Wrapper genérico para fetch com autenticação e CSRF.
 */
async function fetchAPI(url, options = {}) {
  const fullUrl = url.startsWith('http') ? url : `${API_URL}${url}`;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase())) {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Busca resumo de status do GCal (contadores).
 *
 * @param {object} filters - Filtros opcionais (date_from, date_to, sector, q, status)
 * @returns {Promise<object>} { counts: { NONE, PENDING, PUBLISHED, ERROR }, total }
 */
export async function getStatusSummary(filters = {}) {
  const params = new URLSearchParams();

  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  if (filters.sector) params.append('sector', filters.sector);
  if (filters.q) params.append('q', filters.q);
  if (filters.status) params.append('status', filters.status);

  const url = `/gcal/status-summary/?${params.toString()}`;
  return await fetchAPI(url);
}

/**
 * Lista solicitações com campos GCal.
 *
 * @param {object} filters - Filtros opcionais
 * @returns {Promise<object>} { results: [...], count: N }
 */
export async function getGCalList(filters = {}) {
  const params = new URLSearchParams();

  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  if (filters.sector) params.append('sector', filters.sector);
  if (filters.q) params.append('q', filters.q);
  if (filters.status) params.append('status', filters.status);

  const url = `/gcal/list/?${params.toString()}`;
  return await fetchAPI(url);
}

/**
 * Detecta drift (solicitações publicadas com payload alterado).
 *
 * @param {object} filters - Filtros opcionais
 * @returns {Promise<object>} { count: N, items: [...] }
 */
export async function getGCalDrift(filters = {}) {
  const params = new URLSearchParams();

  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  if (filters.sector) params.append('sector', filters.sector);
  if (filters.q) params.append('q', filters.q);

  const url = `/gcal/drift/?${params.toString()}`;
  return await fetchAPI(url);
}

/**
 * Reenfileira publicação em lote.
 *
 * @param {object} body - { ids: [...], dry_run: boolean }
 * @returns {Promise<object>} { queued: N, errors: [...], dry_run: boolean }
 */
export async function bulkReapply(body) {
  return await fetchAPI('/gcal/reapply/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
