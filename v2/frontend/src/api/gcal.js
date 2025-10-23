/**
 * API Client - Google Calendar Dashboard
 *
 * Endpoints para painel de publicação GCal.
 */

import { fetchAPI, buildUrl } from './config';

/**
 * Busca resumo de status do GCal (contadores).
 *
 * @param {object} filters - Filtros opcionais (date_from, date_to, sector, q, status)
 * @returns {Promise<object>} { counts: { NONE, PENDING, PUBLISHED, ERROR }, total }
 */
export async function getStatusSummary(filters = {}) {
  const url = buildUrl('/gcal/status-summary/', filters);
  return await fetchAPI(url);
}

/**
 * Lista solicitações aprovadas com status GCal.
 *
 * @param {object} filters - Filtros (date_from, date_to, sector, gcal_status, q)
 * @returns {Promise<object>} Resultado paginado { results: [...], count: N }
 */
export async function listApprovedWithGCalStatus(filters = {}) {
  const url = buildUrl('/gcal/approved/', filters);
  return await fetchAPI(url);
}

/**
 * Publica múltiplas solicitações em lote no Google Calendar.
 *
 * @param {object} body - { solicitacao_ids: [...], dry_run: bool, apply_blocked: bool }
 * @returns {Promise<object>} Resultado da operação em lote
 */
export async function publishBatch(body) {
  return await fetchAPI('/gcal/publish-batch/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Remove múltiplas solicitações do Google Calendar (unpublish).
 *
 * @param {object} body - { solicitacao_ids: [...] }
 * @returns {Promise<object>} Resultado da operação em lote
 */
export async function unpublishBatch(body) {
  return await fetchAPI('/gcal/unpublish-batch/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Sincroniza solicitações bloqueadas (marca como PENDING no GCal).
 *
 * @param {object} body - { solicitacao_ids: [...] }
 * @returns {Promise<object>} Resultado da sincronização
 */
export async function syncBlocked(body) {
  return await fetchAPI('/gcal/sync-blocked/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
