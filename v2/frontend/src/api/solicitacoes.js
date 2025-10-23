/**
 * API Client - Solicitações
 *
 * Consome endpoints do backend AS v2 para gerenciar solicitações de eventos.
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

// PR15: Mapeamento de aliases de status (inglês → português)
const STATUS_MAP = {
  pending: 'pendente',
  approved: 'aprovado',
  rejected: 'reprovado',
};

/**
 * Lista solicitações de eventos com filtros.
 *
 * @param {object} params - Parâmetros de filtro
 * @param {string} params.status - Filtro por status (EN: 'pending'/'approved'/'rejected' ou PT direto)
 * @param {string} params.mine - Forçar filtro por usuário ('true' para minhas solicitações)
 * @param {string} params.flow - Filtro por fluxo ('SUPER' ou 'NAO_SUPER')
 * @param {string} params.q - Busca textual multi-campo
 * @param {string} params.sector - Filtro por setor/projeto (nome parcial)
 * @param {string} params.date_from - Data inicial (YYYY-MM-DD)
 * @param {string} params.date_to - Data final (YYYY-MM-DD)
 * @param {number} params.page - Número da página (default: 1)
 * @param {string} params.search - Busca por usuário/município/tipo (alias de q)
 * @returns {Promise<object>} Resultado paginado { results: [...], count: N }
 */
export async function listSolicitacoes(filters = {}) {
  const params = new URLSearchParams();

  // PR15: Mapear status alias
  if (filters.status) {
    const mappedStatus = STATUS_MAP[filters.status] ?? filters.status;
    params.append('status', mappedStatus);
  }

  if (filters.mine) params.append('mine', filters.mine);
  if (filters.flow) params.append('flow', filters.flow);
  if (filters.q) params.append('q', filters.q);
  if (filters.search) params.append('search', filters.search);
  if (filters.sector) params.append('sector', filters.sector);
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  if (filters.page) params.append('page', filters.page);

  const url = `/solicitacoes/?${params.toString()}`;
  const data = await fetchAPI(url);

  // DRF retorna { results: [...], count: N } quando paginado
  return data;
}

/**
 * Cria uma nova solicitação de evento.
 *
 * @param {object} body - Dados da solicitação
 * @returns {Promise<object>} Solicitação criada
 */
export async function createSolicitacao(body) {
  return await fetchAPI('/solicitacoes/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Aprova uma solicitação pendente.
 *
 * @param {number} id - ID da solicitação
 * @param {string} reason - Motivo/justificativa (opcional)
 * @returns {Promise<object>} Solicitação atualizada
 */
export async function approveSolicitacao(id, reason = '') {
  return await fetchAPI(`/solicitacoes/${id}/approve/`, {
    method: 'PATCH',
    body: JSON.stringify(reason ? { reason } : {}),
  });
}

/**
 * Reprova uma solicitação pendente.
 *
 * @param {number} id - ID da solicitação
 * @param {string} reason - Motivo/justificativa (obrigatório)
 * @returns {Promise<object>} Solicitação atualizada
 */
export async function rejectSolicitacao(id, reason) {
  return await fetchAPI(`/solicitacoes/${id}/reject/`, {
    method: 'PATCH',
    body: JSON.stringify({ reason }),
  });
}

/**
 * Busca detalhes de uma solicitação específica.
 *
 * @param {number} id - ID da solicitação
 * @returns {Promise<object>} Detalhes da solicitação
 */
export async function getSolicitacao(id) {
  return await fetchAPI(`/solicitacoes/${id}/`);
}

/**
 * Preview do payload GCal de uma solicitação.
 *
 * @param {number} id - ID da solicitação
 * @returns {Promise<object>} Payload GCal
 */
export async function previewSolicitacao(id) {
  return await fetchAPI(`/solicitacoes/${id}/preview-gcal/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

/**
 * Publica solicitação no Google Calendar.
 *
 * @param {number} id - ID da solicitação
 * @param {object} body - Opções (dry_run, apply_blocked, etc.)
 * @returns {Promise<object>} Resultado da publicação
 */
export async function publishSolicitacao(id, body = {}) {
  return await fetchAPI(`/solicitacoes/${id}/publish/`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

// ========================================
// Endpoints de opções (dropdowns/selects)
// ========================================

/**
 * Lista municípios para seleção.
 *
 * @returns {Promise<Array>} Lista de municípios { id, nome, uf }
 */
export async function listMunicipiosOptions() {
  return await fetchAPI('/options/municipios/');
}

/**
 * Lista projetos para seleção.
 *
 * @returns {Promise<Array>} Lista de projetos { id, nome, codigo }
 */
export async function listProjetosOptions() {
  return await fetchAPI('/options/projetos/');
}

/**
 * Lista tipos de evento para seleção.
 *
 * @returns {Promise<Array>} Lista de tipos { id, nome }
 */
export async function listTiposEventoOptions() {
  return await fetchAPI('/options/tipos-evento/');
}

/**
 * Lista usuários para seleção.
 *
 * @param {object} params - Parâmetros opcionais (ex: search)
 * @returns {Promise<Array>} Lista de usuários { id, first_name, last_name, email }
 */
export async function listUsuariosOptions(params = {}) {
  const query = new URLSearchParams(params);
  const queryString = query.toString();
  return await fetchAPI(`/options/usuarios/${queryString ? `?${queryString}` : ''}`);
}

// Re-exportar checkAvailability de availability.js
export { checkAvailability } from './availability.js';
