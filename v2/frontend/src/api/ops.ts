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
 * Import operation result
 */
export interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: Array<{ row: number; message: string }>;
  warnings: string[];
}

/**
 * Compra record
 */
export interface Compra {
  id: number;
  municipio: string;
  projeto: string;
  uf: string;
  data: string;
  codigo: string;
  uso: string;
  quantidade: number;
}

/**
 * Acao record
 */
export interface Acao {
  id: number;
  municipio: string;
  projeto: string;
  uf: string;
  data: string;
  descricao: string;
  status: string;
}

/**
 * Cadastro record
 */
export interface Cadastro {
  id: number;
  municipio: string;
  projeto: string;
  uf: string;
  data: string;
  tipo: string;
  status: string;
}

/**
 * Compras filter parameters
 */
export interface ComprasFilters {
  municipio?: string;
  projeto?: string;
  uf?: string;
  from?: string;
  to?: string;
  q?: string;
  [key: string]: string | undefined;
}

/**
 * Generic filter parameters
 */
export interface GenericFilters {
  [key: string]: string | number | undefined;
}

/**
 * Helper para upload de arquivo (multipart/form-data).
 *
 * Issue #135: Usa ensureCsrfToken() para suportar HttpOnly cookie
 *
 * @param url - URL do endpoint (relativo, ex: '/controle/import-compras/')
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview (não aplica)
 */
async function postMultipart(url: string, file: File, dryRun: boolean = true): Promise<ImportResult> {
  const formData = new FormData();
  formData.append('file', file);

  const fullUrl = url.startsWith('http') ? url : `${API_BASE}${url}`;
  const queryParam = dryRun ? '?dry_run=true' : '?dry_run=false';

  // Obter token CSRF (Issue #135: async ensureCsrfToken)
  const csrfToken = await ensureCsrfToken();
  const headers: Record<string, string> = {};
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

  const raw: unknown = await response.json();
  return normalizeImportResponse(raw);
}

/**
 * Adapt backend `{stats, pendencias, dry_run, file}` shape to `ImportResult`.
 *
 * Backend service responses are not uniform across importers, so the raw JSON
 * must be reshaped before the page-level adapters (`toValidationResult` /
 * `toApplyResult`) can read it as `{created, updated, skipped, errors}`.
 *
 * Variants seen in production:
 *   - bloqueios / usuarios / municipios / colecoes / produtos / equipe_gerencia /
 *     acoes / deslocamentos / cadastros:
 *       stats = { created, updated, unchanged, skipped: {cat1: N, cat2: N, ...} }
 *       pendencias = { cat1: [{linha, erro, ...}], ... }
 *   - compras (controle_imports):
 *       stats = { created, updated, skipped: N, errors: N }
 *       pendencias = { municipios: [...], projetos: [...], linhas_invalidas: [...] }
 *   - eventos (eventos_import):
 *       stats = { solicitacoes: {created, updated, unchanged}, participations: {...}, skipped: {...} }
 *       pendencias = { ... }
 *
 * The adapter also accepts already-flat payloads (`{created, updated, errors}`)
 * so future endpoints conforming to ImportResult directly keep working.
 */
function normalizeImportResponse(raw: unknown): ImportResult {
  if (!raw || typeof raw !== 'object') {
    return { created: 0, updated: 0, skipped: 0, errors: [], warnings: [] };
  }
  const r = raw as Record<string, unknown>;

  const toNum = (v: unknown): number => {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  };

  // Pass-through if response already matches the ImportResult contract
  if (Array.isArray(r.errors) && typeof r.created !== 'undefined') {
    return {
      created: toNum(r.created),
      updated: toNum(r.updated),
      skipped: toNum(r.skipped),
      errors: r.errors as Array<{ row: number; message: string }>,
      warnings: Array.isArray(r.warnings) ? (r.warnings as string[]) : [],
    };
  }

  const stats = (r.stats ?? {}) as Record<string, unknown>;

  // eventos returns stats.solicitacoes = {created, updated, unchanged}
  const nested = stats.solicitacoes;
  const baseStats =
    nested && typeof nested === 'object'
      ? (nested as Record<string, unknown>)
      : stats;

  // stats.skipped may be a number (compras) or an object keyed by skip reason
  let skippedTotal = 0;
  const sk = stats.skipped;
  if (typeof sk === 'number') {
    skippedTotal = sk;
  } else if (sk && typeof sk === 'object') {
    for (const v of Object.values(sk as Record<string, unknown>)) {
      skippedTotal += toNum(v);
    }
  }
  // `unchanged` rows are also "non-mutating" — surface them in the same bucket
  // so the page label "registros não alterados" reflects everything that
  // didn't create or update.
  skippedTotal += toNum(baseStats.unchanged);

  // Flatten pendencias dict-of-arrays into errors[]
  const pendencias = (r.pendencias ?? {}) as Record<string, unknown>;
  const errors: Array<{ row: number; message: string }> = [];
  for (const [cat, items] of Object.entries(pendencias)) {
    if (!Array.isArray(items)) continue;
    for (const e of items) {
      if (typeof e !== 'object' || e === null) continue;
      const item = e as Record<string, unknown>;
      const rowNum = toNum(item.linha ?? item.linha_num ?? item.row);
      const detail = [item.erro, item.nome, item.message]
        .filter((x): x is string => typeof x === 'string' && x.length > 0)
        .join(' — ');
      errors.push({
        row: rowNum,
        message: detail ? `[${cat}] ${detail}` : `[${cat}]`,
      });
    }
  }

  return {
    created: toNum(baseStats.created),
    updated: toNum(baseStats.updated),
    skipped: skippedTotal,
    errors,
    warnings: [],
  };
}

export const __testing = { normalizeImportResponse };

/**
 * Importa COMPRAS de CSV/XLSX.
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importCompras(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/controle/import-compras/', file, dryRun);
}

/**
 * Importa AÇÕES de Controle de CSV/XLSX.
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importAcoes(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/controle/import-acoes/', file, dryRun);
}

/**
 * Importa CADASTROS DAT de CSV/XLSX.
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importCadastros(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/dat/import-cadastros/', file, dryRun);
}

/**
 * Importa BLOQUEIOS (AvailabilityBlock) de CSV/XLSX.
 *
 * Colunas esperadas: usuario, inicio, fim, tipo (T/P), motivo
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importBloqueios(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/disponibilidade/import-bloqueios/', file, dryRun);
}

/**
 * Importa Deslocamentos de CSV/XLSX.
 *
 * Colunas esperadas: usuario, origem, destino, data_inicio, data_fim, observacao
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importDeslocamentos(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/deslocamentos/import/', file, dryRun);
}

/**
 * Importa EVENTOS (Solicitacao + Participation) de CSV/XLSX.
 *
 * Colunas esperadas:
 * - municipio, projeto, tipo_evento (obrigatorios)
 * - data, hora_inicio, hora_fim (obrigatorios)
 * - coordenador (obrigatorio)
 * - formador1-5 (opcionais)
 * - encontro, segmento, local (opcionais)
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importEventos(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/solicitacoes/import/', file, dryRun);
}

/**
 * Importa USUARIOS de CSV/XLSX.
 *
 * Colunas esperadas:
 * - cpf, nome (obrigatorios)
 * - email, telefone, cargo (opcionais)
 * - grupos (opcional, separados por virgula)
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importUsuarios(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/usuarios/import/', file, dryRun);
}

/**
 * Importa MUNICIPIOS de CSV/XLSX.
 *
 * Colunas esperadas:
 * - nome, uf (obrigatorios)
 * - ibge_code, ativo (opcionais)
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importMunicipios(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/municipios/import/', file, dryRun);
}

/**
 * Importa COLECOES de CSV/XLSX.
 *
 * Colunas esperadas:
 * - codigo, nome, projeto (obrigatorios)
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importColecoes(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/colecoes/import/', file, dryRun);
}

/**
 * Importa EQUIPE GERENCIA (vinculos usuario-gerencia) de CSV/XLSX.
 *
 * Colunas esperadas:
 * - usuario (cpf ou email), gerencia, funcao (obrigatorios)
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importEquipeGerencia(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/equipe-gerencia/import/', file, dryRun);
}

/**
 * Importa PRODUTOS de CSV/XLSX.
 *
 * Colunas esperadas:
 * - codigo, nome, projeto (obrigatorios)
 * - descricao (opcional)
 *
 * @param file - Arquivo a enviar
 * @param dryRun - Se true, apenas preview
 */
export async function importProdutos(file: File, dryRun: boolean = true): Promise<ImportResult> {
  return await postMultipart('/produtos/import/', file, dryRun);
}

/**
 * Lista COMPRAS com filtros opcionais.
 */
export async function listCompras(filters: ComprasFilters = {}): Promise<Compra[]> {
  const url = buildUrl('/controle/compras/', filters);
  const data = await fetchAPI<{ results?: Compra[] } | Compra[]>(url);
  return (data as { results: Compra[] }).results || (data as Compra[]);
}

/**
 * Lista AÇÕES de Controle com filtros opcionais.
 */
export async function listAcoes(filters: GenericFilters = {}): Promise<Acao[]> {
  const url = buildUrl('/controle/acoes/', filters);
  const data = await fetchAPI<{ results?: Acao[] } | Acao[]>(url);
  return (data as { results: Acao[] }).results || (data as Acao[]);
}

/**
 * Lista CADASTROS DAT com filtros opcionais.
 */
export async function listCadastros(filters: GenericFilters = {}): Promise<Cadastro[]> {
  const url = buildUrl('/dat/acoes/', filters);
  const data = await fetchAPI<{ results?: Cadastro[] } | Cadastro[]>(url);
  return (data as { results: Cadastro[] }).results || (data as Cadastro[]);
}
