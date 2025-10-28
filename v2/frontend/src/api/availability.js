/**
 * API Client - Availability Blocks
 *
 * Consome endpoints do backend AS v2 para gerenciar bloqueios de disponibilidade.
 */

import { fetchAPI, buildUrl } from './config';

/**
 * Busca informações do usuário atual.
 *
 * @returns {Promise<object>} Dados do usuário (id, username, email, first_name, last_name, groups, is_superuser, etc.)
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
  const url = buildUrl('/availability-blocks/', { owner });
  const data = await fetchAPI(url);

  // DRF retorna { results: [...], count: N } quando paginado
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
  const url = buildUrl('/availability/check/', {
    usuario_id,
    inicio,
    fim,
    municipio_id,
  });

  return await fetchAPI(url);
}

/**
 * Busca grade mensal de disponibilidade.
 *
 * @param {object} params - Parâmetros da consulta
 * @param {number} params.year - Ano (YYYY)
 * @param {number} params.month - Mês (1..12)
 * @param {string} params.role - Role ("FORMADOR" | "COORDENADOR")
 * @param {string} params.sector - Filtro por setor (opcional)
 * @param {string} params.q - Filtro por nome/email (opcional)
 * @returns {Promise<object>} Grade mensal { days, legend, people, cells, details_index }
 */
export async function getMonthlyAvailability({ year, month, role, sector, q }) {
  const url = buildUrl('/availability/monthly/', {
    year,
    month,
    role,
    sector,
    q,
  });

  return await fetchAPI(url);
}

/**
 * Busca grade mensal de disponibilidade (versão genérica).
 *
 * @param {Record<string, string | number>} params - Parâmetros da consulta
 * @returns {Promise<object>} Grade mensal { days, legend, people, cells, details_index }
 */
export async function getMonthly(params) {
  const url = buildUrl('/availability/monthly/', params);
  return await fetchAPI(url);
}

/**
 * Busca feature flags do sistema.
 *
 * @returns {Promise<object>} Feature flags { apply_blocked, GCAL_CLIENT, PREVIEW_ONLY, ... }
 */
export async function getFeatures() {
  return await fetchAPI('/features/');
}
