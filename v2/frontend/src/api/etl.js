/**
 * API Client - ETL Observability
 *
 * Endpoints para listar e acessar relatórios ETL gerados pelos
 * comandos de importação (etl_upsert_*, etl_import_*, etc).
 *
 * Fase 5 - Desligamento gradual de planilhas
 */

import { fetchAPI, buildUrl } from './config';

/**
 * Listar relatórios ETL mais recentes
 *
 * @param {number} limit - Número máximo de relatórios (1-100, default=20)
 * @returns {Promise<{count: number, limit: number, reports: Array}>}
 *
 * Cada report contém:
 * - filename: string - Nome do arquivo
 * - size_bytes: number - Tamanho em bytes
 * - mtime_iso: string - Data/hora modificação (ISO 8601)
 * - kind: string - Tipo do arquivo (json, csv, txt, other)
 * - path_rel: string - Caminho relativo (para download)
 */
export async function listLatestReports(limit = 20) {
  const url = buildUrl('/etl/reports/latest/', { limit });
  return await fetchAPI(url);
}

/**
 * Construir URL para download de relatório ETL
 *
 * @param {string} filename - Nome do arquivo (path_rel do report)
 * @returns {string} URL absoluta para download
 *
 * Nota: O download é feito via link direto (não via fetchAPI) para permitir
 * navegação direta ao arquivo. O backend serve arquivos estáticos de out_etl/.
 */
export function getReportDownloadUrl(filename) {
  // Backend deve servir arquivos estáticos em /out_etl/
  // ou implementar endpoint /api/etl/reports/download/{filename}
  return `/out_etl/${filename}`;
}
