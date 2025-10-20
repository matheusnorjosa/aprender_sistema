/**
 * API Client - Availability Blocks
 *
 * Consome endpoints do backend AS v2 para gerenciar bloqueios de disponibilidade.
 *
 * Autenticação: sessão/cookie do Django (credentials: 'include')
 * CSRF: header X-CSRFToken (lido do cookie csrftoken)
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002/api';

/**
 * Extrai token CSRF do cookie.
 *
 * @returns {string|null} CSRF token ou null se não encontrado
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
 *
 * @param {string} url - URL relativa ou absoluta
 * @param {object} options - Opções do fetch
 * @returns {Promise<object>} Response JSON
 */
async function fetchAPI(url, options = {}) {
  const fullUrl = url.startsWith('http') ? url : `${API_URL}${url}`;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // Adicionar CSRF para métodos mutantes
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase())) {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken;
    }
  }

  const response = await fetch(fullUrl, {
    ...options,
    headers,
    credentials: 'include', // Incluir cookies de sessão
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Busca informações do usuário atual.
 *
 * @returns {Promise<object>} Dados do usuário (id, username, email, first_name, last_name)
 */
export async function getMe() {
  return await fetchAPI('/me/');
}

/**
 * Lista bloqueios de disponibilidade.
 *
 * @param {object} params - Parâmetros de filtro
 * @param {string} params.owner - Filtro por dono ('me' para usuário atual)
 * @returns {Promise<Array>} Lista de bloqueios (extrai 'results' da paginação DRF)
 */
export async function getBlocks({ owner = 'me' } = {}) {
  const params = new URLSearchParams();
  if (owner) params.append('owner', owner);

  const url = `/availability-blocks/?${params.toString()}`;
  const data = await fetchAPI(url);

  // DRF retorna { results: [...], count: N } quando paginado
  // Se results existe, retorna ele; senão retorna data como array
  return data.results || data;
}

/**
 * Cria novo bloqueio de disponibilidade.
 *
 * @param {object} data - Dados do bloqueio
 * @param {string} data.inicio - Data/hora início (ISO8601)
 * @param {string} data.fim - Data/hora fim (ISO8601)
 * @param {string} data.tipo - Tipo de bloqueio ('T' ou 'P')
 * @param {string} data.motivo - Motivo do bloqueio (opcional)
 * @param {number} data.municipio - ID do município (opcional)
 * @returns {Promise<object>} Bloqueio criado
 */
export async function createBlock(data) {
  return await fetchAPI('/availability-blocks/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Remove bloqueio de disponibilidade.
 *
 * Apenas bloqueios com status='pendente' podem ser removidos.
 *
 * @param {number} id - ID do bloqueio
 * @returns {Promise<void>}
 */
export async function deleteBlock(id) {
  await fetchAPI(`/availability-blocks/${id}/`, {
    method: 'DELETE',
  });
}

/**
 * Checa disponibilidade de um usuário (consultivo).
 *
 * @param {object} params - Parâmetros da checagem
 * @param {number} params.usuario_id - ID do usuário
 * @param {string} params.inicio - Data/hora início (ISO8601)
 * @param {string} params.fim - Data/hora fim (ISO8601)
 * @param {number} params.municipio_id - ID do município (opcional)
 * @returns {Promise<object>} Resultado { ok: bool, conflicts: [{code, title, detail, ref_id}] }
 */
export async function checkAvailability({ usuario_id, inicio, fim, municipio_id }) {
  const params = new URLSearchParams();
  params.append('usuario_id', usuario_id);
  params.append('inicio', inicio);
  params.append('fim', fim);
  if (municipio_id) params.append('municipio_id', municipio_id);

  const url = `/availability/check/?${params.toString()}`;
  return await fetchAPI(url);
}
