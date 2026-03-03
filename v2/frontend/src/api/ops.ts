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

  return response.json();
}

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
