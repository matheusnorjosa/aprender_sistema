/**
 * PR16: API helpers para Lookup (Autocomplete) e Validação
 *
 * Endpoints:
 * - GET /api/lookup/municipios/?q=...
 * - GET /api/lookup/projetos/?q=...
 * - GET /api/lookup/tipos-evento/?q=...
 * - GET /api/lookup/usuarios/?q=...&role=...
 * - POST /api/solicitacoes/validate/
 */

const API_BASE = '/api';

/**
 * Helper genérico para fetch com credentials
 */
async function fetchAPI(url, options = {}) {
  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * Buscar municípios (autocomplete)
 * @param {string} q - Query string
 * @returns {Promise<Array<{id, label, kind}>>}
 */
export async function lookupMunicipios(q = '') {
  const params = new URLSearchParams();
  if (q) params.append('q', q);

  const url = `${API_BASE}/lookup/municipios/?${params.toString()}`;
  return await fetchAPI(url);
}

/**
 * Buscar projetos (autocomplete)
 * @param {string} q - Query string
 * @returns {Promise<Array<{id, label, kind}>>}
 */
export async function lookupProjetos(q = '') {
  const params = new URLSearchParams();
  if (q) params.append('q', q);

  const url = `${API_BASE}/lookup/projetos/?${params.toString()}`;
  return await fetchAPI(url);
}

/**
 * Buscar tipos de evento (autocomplete)
 * @param {string} q - Query string
 * @returns {Promise<Array<{id, label, kind}>>}
 */
export async function lookupTiposEvento(q = '') {
  const params = new URLSearchParams();
  if (q) params.append('q', q);

  const url = `${API_BASE}/lookup/tipos-evento/?${params.toString()}`;
  return await fetchAPI(url);
}

/**
 * Buscar usuários (autocomplete)
 * @param {string} q - Query string
 * @param {string} role - Filtro por role/grupo (opcional)
 * @returns {Promise<Array<{id, label, kind, email}>>}
 */
export async function lookupUsuarios(q = '', role = '') {
  const params = new URLSearchParams();
  if (q) params.append('q', q);
  if (role) params.append('role', role);

  const url = `${API_BASE}/lookup/usuarios/?${params.toString()}`;
  return await fetchAPI(url);
}

/**
 * Validar dados de solicitação antes do submit
 * @param {Object} payload - Dados da solicitação
 * @returns {Promise<{ok: boolean, errors: Array, canonical: Object}>}
 */
export async function validateSolic(payload) {
  const url = `${API_BASE}/solicitacoes/validate/`;
  return await fetchAPI(url, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
