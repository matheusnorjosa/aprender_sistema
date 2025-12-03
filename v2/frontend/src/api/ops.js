/**
 * API Client - Operations (Controle & DAT)
 *
 * Endpoints para importação e listagem de:
 * - COMPRAS (Controle)
 * - AÇÕES (Controle)
 * - CADASTROS (DAT)
 *
 * Issue #135: Usa ensureCsrfToken() para suportar CSRF_COOKIE_HTTPONLY=True
 */

import { API_BASE, ensureCsrfToken, fetchAPI, buildUrl } from './config';
import logger from '../utils/logger';

/**
 * Helper para upload de arquivo (multipart/form-data).
 *
 * Issue #135: Usa ensureCsrfToken() para suportar HttpOnly cookie
 *
 * @param {string} url - URL do endpoint (relativo, ex: '/controle/import-compras/')
 * @param {File} file - Arquivo a enviar
 * @param {boolean} dryRun - Se true, apenas preview (não aplica)
 * @returns {Promise<object>} Relatório de import
 */
async function postMultipart(url, file, dryRun = true) {
  const formData = new FormData();
  formData.append('file', file);

  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
  const queryParam = dryRun ? '?dry_run=true' : '?dry_run=false';

  // Obter token CSRF (Issue #135: async ensureCsrfToken)
  const csrfToken = await ensureCsrfToken();
  const headers = {};
  if (csrfToken) {
    headers['X-CSRFToken'] = csrfToken;
  } else {
    logger.error('CSRF token não encontrado para upload multipart!');
    throw new Error('CSRF token ausente. Faça login novamente.');
  }

  const response = await fetch(`${fullUrl}${queryParam}`, {
    method: 'POST',
    headers: headers,
    body: formData,
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Importa COMPRAS de CSV/XLSX.
 *
 * @param {File} file - Arquivo a enviar
 * @param {boolean} dryRun - Se true, apenas preview
 * @returns {Promise<object>} Relatório com stats e pendências
 */
export async function importCompras(file, dryRun = true) {
  return await postMultipart('/controle/import-compras/', file, dryRun);
}

/**
 * Importa AÇÕES de Controle de CSV/XLSX.
 *
 * @param {File} file - Arquivo a enviar
 * @param {boolean} dryRun - Se true, apenas preview
 * @returns {Promise<object>} Relatório com stats e pendências
 */
export async function importAcoes(file, dryRun = true) {
  return await postMultipart('/controle/import-acoes/', file, dryRun);
}

/**
 * Importa CADASTROS DAT de CSV/XLSX.
 *
 * @param {File} file - Arquivo a enviar
 * @param {boolean} dryRun - Se true, apenas preview
 * @returns {Promise<object>} Relatório com stats e pendências
 */
export async function importCadastros(file, dryRun = true) {
  return await postMultipart('/dat/import-cadastros/', file, dryRun);
}

/**
 * Lista COMPRAS com filtros opcionais.
 *
 * @param {object} filters - Filtros opcionais
 * @param {string} filters.municipio - Nome do município
 * @param {string} filters.projeto - Nome do projeto
 * @param {string} filters.uf - UF do município
 * @param {string} filters.from - Data início (YYYY-MM-DD)
 * @param {string} filters.to - Data fim (YYYY-MM-DD)
 * @param {string} filters.q - Busca em uso/código
 * @returns {Promise<Array>} Lista de compras
 */
export async function listCompras(filters = {}) {
  const url = buildUrl('/controle/compras/', filters);
  const data = await fetchAPI(url);
  return data.results || data;
}

/**
 * Lista AÇÕES de Controle com filtros opcionais.
 *
 * @param {object} filters - Filtros opcionais
 * @returns {Promise<Array>} Lista de ações
 */
export async function listAcoes(filters = {}) {
  const url = buildUrl('/controle/acoes/', filters);
  const data = await fetchAPI(url);
  return data.results || data;
}

/**
 * Lista CADASTROS DAT com filtros opcionais.
 *
 * @param {object} filters - Filtros opcionais
 * @returns {Promise<Array>} Lista de cadastros
 */
export async function listCadastros(filters = {}) {
  const url = buildUrl('/dat/acoes/', filters);
  const data = await fetchAPI(url);
  return data.results || data;
}
