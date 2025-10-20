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

/**
 * Lista solicitações de eventos com filtros.
 *
 * @param {object} params - Parâmetros de filtro
 * @param {string} params.status - Filtro por status ('pendente', 'aprovado', 'reprovado')
 * @param {number} params.page - Número da página (default: 1)
 * @param {string} params.search - Busca por usuário/município/tipo
 * @returns {Promise<object>} Resultado paginado { results: [...], count: N }
 */
export async function listSolicitacoes({ status = 'pendente', page = 1, search = '' } = {}) {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (page) params.append('page', page);
  if (search) params.append('search', search);

  const url = `/solicitacoes/?${params.toString()}`;
  const data = await fetchAPI(url);

  // DRF retorna { results: [...], count: N } quando paginado
  return data;
}

/**
 * Aprova uma solicitação pendente.
 *
 * @param {number} id - ID da solicitação
 * @returns {Promise<object>} Solicitação atualizada
 */
export async function approveSolicitacao(id) {
  return await fetchAPI(`/solicitacoes/${id}/approve/`, {
    method: 'PATCH',
  });
}

/**
 * Reprova uma solicitação pendente.
 *
 * @param {number} id - ID da solicitação
 * @param {object} data - Dados da reprovação
 * @param {string} data.justificativa - Justificativa obrigatória para reprovação
 * @returns {Promise<object>} Solicitação atualizada
 */
export async function rejectSolicitacao(id, { justificativa }) {
  return await fetchAPI(`/solicitacoes/${id}/reject/`, {
    method: 'PATCH',
    body: JSON.stringify({ justificativa }),
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
