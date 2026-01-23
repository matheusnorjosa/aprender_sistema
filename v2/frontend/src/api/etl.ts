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
 * ETL Report file info
 */
export interface ETLReport {
  filename: string;
  size_bytes: number;
  mtime_iso: string;
  kind: 'json' | 'csv' | 'txt' | 'other';
  path_rel: string;
}

/**
 * ETL Reports list response
 */
export interface ETLReportsResponse {
  count: number;
  limit: number;
  reports: ETLReport[];
}

/**
 * Listar relatórios ETL mais recentes
 *
 * @param limit - Número máximo de relatórios (1-100, default=20)
 */
export async function listLatestReports(limit: number = 20): Promise<ETLReportsResponse> {
  const url = buildUrl('/etl/reports/latest/', { limit });
  return await fetchAPI(url);
}

/**
 * Construir URL para download de relatório ETL
 *
 * @param filename - Nome do arquivo (path_rel do report)
 * @returns URL absoluta para download
 *
 * Nota: O download é feito via link direto (não via fetchAPI) para permitir
 * navegação direta ao arquivo. O backend serve arquivos estáticos de out_etl/.
 */
export function getReportDownloadUrl(filename: string): string {
  // Backend deve servir arquivos estáticos em /out_etl/
  // ou implementar endpoint /api/etl/reports/download/{filename}
  return `/out_etl/${encodeURIComponent(filename)}`;
}
