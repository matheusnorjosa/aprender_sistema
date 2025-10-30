/**
 * API Client - Solicitações
 *
 * Consome endpoints do backend AS v2 para gerenciar solicitações de eventos.
 */

import { fetchAPI, buildUrl } from './config';

// Mapeamento de aliases de status (inglês → português)
// Mantido para compatibilidade com código legado
const STATUS_MAP = {
  pending: 'pendente',
  approved: 'aprovado',
  rejected: 'reprovado',
};

/**
 * Lista solicitações de eventos com filtros.
 *
 * @param {object} filters - Parâmetros de filtro
 * @param {string} filters.status - Filtro por status (aceita EN ou PT)
 * @param {string} filters.mine - Forçar filtro por usuário ('true' para minhas solicitações)
 * @param {string} filters.flow - Filtro por fluxo ('SUPER' ou 'NAO_SUPER')
 * @param {string} filters.q - Busca textual multi-campo
 * @param {string} filters.sector - Filtro por setor/projeto (nome parcial)
 * @param {string} filters.date_from - Data inicial (YYYY-MM-DD)
 * @param {string} filters.date_to - Data final (YYYY-MM-DD)
 * @param {number} filters.page - Número da página (default: 1)
 * @param {string} filters.search - Busca por usuário/município/tipo (alias de q)
 * @returns {Promise<object>} Resultado paginado { results: [...], count: N }
 */
export async function listSolicitacoes(filters = {}) {
  // Mapear status aliases (inglês→português) se necessário
  const normalizedFilters = { ...filters };

  if (normalizedFilters.status) {
    normalizedFilters.status = STATUS_MAP[normalizedFilters.status] ?? normalizedFilters.status;
  }

  const url = buildUrl('/solicitacoes/', normalizedFilters);
  return await fetchAPI(url);
}

/**
 * Cria uma nova solicitação de evento.
 *
 * @param {object} body - Dados da solicitação
 * @returns {Promise<object>} Solicitação criada
 */
export async function createSolicitacao(body) {
  console.log('=== createSolicitacao DEBUG ===');
  console.log('Body enviado:', body);
  console.log('JSON stringificado:', JSON.stringify(body));

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

/**
 * Republicar solicitação no Google Calendar (força UPDATE) - Fase 4.
 *
 * Reseta gcal_payload_hash para forçar UPDATE mesmo se já publicado.
 * Enfileira task_publish_solicitacao_to_gcal para republicação.
 *
 * @param {number} id - ID da solicitação aprovada
 * @returns {Promise<object>} { detail, task_id, solicitacao_id }
 */
export async function resyncSolicitacao(id) {
  return await fetchAPI(`/solicitacoes/${id}/resync-gcal/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

/**
 * Cancelar evento no Google Calendar e limpar campos - Fase 4.
 *
 * Deleta evento do Calendar (trata 404 como sucesso - idempotência) e limpa
 * todos os campos relacionados: external_event_id, meet_link, gcal_payload_hash.
 *
 * @param {number} id - ID da solicitação com evento publicado
 * @returns {Promise<object>} { detail, task_id, solicitacao_id }
 */
export async function cancelSolicitacao(id) {
  return await fetchAPI(`/solicitacoes/${id}/cancel-gcal/`, {
    method: 'POST',
    body: JSON.stringify({}),
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
  const url = buildUrl('/options/usuarios/', params);
  return await fetchAPI(url);
}

// Re-exportar checkAvailability de availability.js
export { checkAvailability } from './availability.js';
