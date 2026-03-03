/**
 * API Client for DAT Module endpoints
 *
 * Ref: v2/docs/SPEC_DAT_REGISTROS.md
 *
 * Endpoints:
 * - /api/dat/registros/ - DATRegistro CRUD
 * - /api/projetos-gerais/ - ProjetoGeral CRUD
 */

import type { AxiosResponse, AxiosError } from 'axios';
import api from '../api';
import type { ID, PaginatedResponse, MunicipioOption, ProjetoOption, Projeto } from '../types';

// ========== TYPE DEFINITIONS ==========

/**
 * DAT Registro record
 */
export interface DATRegistro {
  id: ID;
  municipio: ID;
  municipio_nome?: string;
  projeto_geral: ID;
  projeto_geral_nome?: string;
  projeto?: ID;
  projeto_nome?: string;
  uf: string;
  usa_avaliar: boolean;
  status_formar: string;
  created_at: string;
  updated_at: string;
}

/**
 * DAT Registro stats
 */
export interface DATRegistroStats {
  total: number;
  completos_formar: number;
  completos_avaliar: number;
  usa_avaliar: number;
  por_uf: Record<string, number>;
}

/**
 * Projeto Geral record
 */
export interface ProjetoGeral {
  id: ID;
  nome: string;
  usa_avaliar: boolean;
  tipo_calculo_codigos: string;
  divisor_aluno?: number;
  multiplicador_professor?: number;
  ativo: boolean;
}

/**
 * Projeto Geral option for dropdown
 */
export interface ProjetoGeralOption {
  id: ID;
  nome: string;
  usa_avaliar: boolean;
}

/**
 * Generic record type for CRUD operations
 */
export interface GenericRecord {
  id: ID;
  [key: string]: unknown;
}

/**
 * Generic stats response
 */
export interface GenericStats {
  [key: string]: number | Record<string, number>;
}

/**
 * Generic filter params
 */
export interface FilterParams {
  search?: string;
  page?: number;
  ordering?: string;
  [key: string]: string | number | boolean | undefined;
}

/**
 * Axios error with response
 */
interface AxiosErrorWithResponse extends AxiosError {
  response?: AxiosResponse<{ detail?: string }>;
}

/**
 * Helper to handle axios responses and errors
 */
async function apiRequest<T>(requestFn: () => Promise<AxiosResponse<T>>): Promise<T> {
  try {
    const response = await requestFn();
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosErrorWithResponse;
    let message: string;
    if (axiosError.response?.status === 403) {
      message = 'Acesso restrito ao setor DAT.';
    } else if (axiosError.response?.status === 404) {
      message = 'Registro nao encontrado.';
    } else {
      message = axiosError.response?.data?.detail || axiosError.message || `Erro HTTP ${axiosError.response?.status}`;
    }
    throw new Error(message);
  }
}

// ========== DAT REGISTROS ==========

/**
 * List DATRegistro records
 * @param params - Query parameters
 */
export async function listDATRegistros(params: FilterParams = {}): Promise<PaginatedResponse<DATRegistro>> {
  return apiRequest(() => api.get('/dat/registros/', { params }));
}

/**
 * Get single DATRegistro
 * @param id - DATRegistro ID
 */
export async function getDATRegistro(id: ID): Promise<DATRegistro> {
  return apiRequest(() => api.get(`/dat/registros/${id}/`));
}

/**
 * Create new DATRegistro
 * @param data - DATRegistro data
 */
export async function createDATRegistro(data: Partial<DATRegistro>): Promise<DATRegistro> {
  return apiRequest(() => api.post('/dat/registros/', data));
}

/**
 * Update DATRegistro
 * @param id - DATRegistro ID
 * @param data - Updated fields
 */
export async function updateDATRegistro(id: ID, data: Partial<DATRegistro>): Promise<DATRegistro> {
  return apiRequest(() => api.patch(`/dat/registros/${id}/`, data));
}

/**
 * Delete DATRegistro (requires Superintendencia)
 * @param id - DATRegistro ID
 */
export async function deleteDATRegistro(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/dat/registros/${id}/`));
}

/**
 * Get DATRegistro stats
 */
export async function getDATRegistroStats(): Promise<DATRegistroStats> {
  return apiRequest(() => api.get('/dat/registros/stats/'));
}

/**
 * Export DATRegistros to CSV
 * @param params - Filter parameters
 */
export async function exportDATRegistros(params: FilterParams = {}): Promise<Blob> {
  const response = await api.get('/dat/registros/export/', {
    params,
    responseType: 'blob',
  });
  return response.data;
}

// ========== PROJETOS GERAIS ==========

/**
 * List ProjetoGeral records
 * @param params - Query parameters
 */
export async function listProjetosGerais(params: FilterParams = {}): Promise<PaginatedResponse<ProjetoGeral>> {
  return apiRequest(() => api.get('/projetos-gerais/', { params }));
}

/**
 * Get single ProjetoGeral
 * @param id - ProjetoGeral ID
 */
export async function getProjetoGeral(id: ID): Promise<ProjetoGeral> {
  return apiRequest(() => api.get(`/projetos-gerais/${id}/`));
}

/**
 * Create new ProjetoGeral
 * @param data - ProjetoGeral data
 */
export async function createProjetoGeral(data: Partial<ProjetoGeral>): Promise<ProjetoGeral> {
  return apiRequest(() => api.post('/projetos-gerais/', data));
}

/**
 * Update ProjetoGeral
 * @param id - ProjetoGeral ID
 * @param data - Updated fields
 */
export async function updateProjetoGeral(id: ID, data: Partial<ProjetoGeral>): Promise<ProjetoGeral> {
  return apiRequest(() => api.patch(`/projetos-gerais/${id}/`, data));
}

/**
 * Delete ProjetoGeral (requires Superintendencia)
 * @param id - ProjetoGeral ID
 */
export async function deleteProjetoGeral(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/projetos-gerais/${id}/`));
}

/**
 * Get Projetos linked to a ProjetoGeral
 * @param id - ProjetoGeral ID
 */
export async function getProjetosForProjetoGeral(id: ID): Promise<Projeto[]> {
  return apiRequest(() => api.get(`/projetos-gerais/${id}/projetos/`));
}

// ========== OPTIONS (for dropdowns) ==========

/**
 * Get minimal list of ProjetosGerais for dropdown
 */
export async function getProjetosGeraisOptions(): Promise<ProjetoGeralOption[]> {
  return apiRequest(() => api.get('/projetos-gerais/', { params: { minimal: 'true' } }));
}

/**
 * Get Municipios options for dropdown
 */
export async function getMunicipiosOptions(): Promise<MunicipioOption[]> {
  return apiRequest(() => api.get('/options/municipios/'));
}

/**
 * Get Projetos options for dropdown
 */
export async function getProjetosOptions(): Promise<ProjetoOption[]> {
  return apiRequest(() => api.get('/options/projetos/'));
}

// ========== AÇÕES (Ciclo de Vida de Projetos) ==========

/**
 * Listar ações com filtros
 */
export async function listAcoes(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return apiRequest(() => api.get('/dat/acoes-ciclo/', { params }));
}

export async function getAcao(id: ID): Promise<GenericRecord> {
  return apiRequest(() => api.get(`/dat/acoes-ciclo/${id}/`));
}

export async function createAcao(data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.post('/dat/acoes-ciclo/', data));
}

export async function updateAcao(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/acoes-ciclo/${id}/`, data));
}

export async function deleteAcao(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/dat/acoes-ciclo/${id}/`));
}

export async function getAcoesStats(params: FilterParams = {}): Promise<GenericStats> {
  return apiRequest(() => api.get('/dat/acoes-ciclo/stats/', { params }));
}

// ========== COMPRAS (Controle de Materiais) ==========

/**
 * Listar compras com filtros
 */
export async function listCompras(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return apiRequest(() => api.get('/dat/compras-materiais/', { params }));
}

export async function getCompra(id: ID): Promise<GenericRecord> {
  return apiRequest(() => api.get(`/dat/compras-materiais/${id}/`));
}

export async function createCompra(data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.post('/dat/compras-materiais/', data));
}

export async function updateCompra(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/compras-materiais/${id}/`, data));
}

export async function deleteCompra(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/dat/compras-materiais/${id}/`));
}

export async function getComprasStats(params: FilterParams = {}): Promise<GenericStats> {
  return apiRequest(() => api.get('/dat/compras-materiais/stats/', { params }));
}

// Dashboard de Compras
export interface ComprasDashboardKpis {
  municipios_atendidos: number;
  total_municipios_referencia: number;
  cobertura_percentual: number;
  total_itens: number;
  total_entregue: number;
  total_disponivel: number;
  produtos_diferentes: number;
  colecoes_diferentes: number;
  valor_total: number;
}

export interface ComprasDashboardItem {
  [key: string]: string | number;
}

export interface ComprasDashboardData {
  kpis: ComprasDashboardKpis;
  por_colecao: ComprasDashboardItem[];
  top_produtos: ComprasDashboardItem[];
  top_municipios: ComprasDashboardItem[];
  top_frequencia: ComprasDashboardItem[];
  por_ano: ComprasDashboardItem[];
  por_tipo_compra: ComprasDashboardItem[];
}

export async function getComprasDashboard(params: FilterParams = {}): Promise<ComprasDashboardData> {
  return apiRequest(() => api.get('/dat/compras-materiais/dashboard/', { params }));
}

export interface CompraPendenteItem {
  municipio_id: number;
  municipio: string;
  uf: string;
  projeto_id: number;
  projeto: string;
  total_itens: number;
  total_compras: number;
  ultima_compra: string | null;
}

export interface ComprasPendenciasResponse {
  total_com_compra: number;
  total_com_evento: number;
  total_pendentes: number;
  percentual_pendentes: number;
  pendentes: CompraPendenteItem[];
}

export async function getComprasPendencias(params: FilterParams = {}): Promise<ComprasPendenciasResponse> {
  return apiRequest(() => api.get('/dat/compras-materiais/pendencias/', { params }));
}

// ========== CADASTROS (Workflow FORMAR/AVALIAR) ==========

/**
 * Listar cadastros com filtros
 */
export async function listCadastros(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return apiRequest(() => api.get('/dat/cadastros/', { params }));
}

export async function getCadastro(id: ID): Promise<GenericRecord> {
  return apiRequest(() => api.get(`/dat/cadastros/${id}/`));
}

export async function createCadastro(data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.post('/dat/cadastros/', data));
}

export async function updateCadastro(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/cadastros/${id}/`, data));
}

export async function deleteCadastro(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/dat/cadastros/${id}/`));
}

export async function updateCadastroEtapa(id: ID, etapa: string, status: string): Promise<GenericRecord> {
  return apiRequest(() => api.post(`/dat/cadastros/${id}/etapa/`, { etapa, status }));
}

export async function getCadastrosStats(params: FilterParams = {}): Promise<GenericStats> {
  return apiRequest(() => api.get('/dat/cadastros/stats/', { params }));
}

// ========== FORMAÇÕES (Calendário de Treinamentos) ==========

/**
 * Listar formações com filtros
 */
export async function listFormacoes(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return apiRequest(() => api.get('/dat/formacoes/', { params }));
}

export async function getFormacao(id: ID): Promise<GenericRecord> {
  return apiRequest(() => api.get(`/dat/formacoes/${id}/`));
}

export async function createFormacao(data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.post('/dat/formacoes/', data));
}

export async function updateFormacao(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/formacoes/${id}/`, data));
}

export async function deleteFormacao(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/dat/formacoes/${id}/`));
}

export async function getFormacoesStats(params: FilterParams = {}): Promise<GenericStats> {
  return apiRequest(() => api.get('/dat/formacoes/stats/', { params }));
}

export async function getFormacoesCalendario(params: FilterParams = {}): Promise<GenericRecord[]> {
  return apiRequest(() => api.get('/dat/formacoes/calendario/', { params }));
}

// ========== COORDENADORES ==========

/**
 * Listar coordenadores com filtros
 */
export async function listCoordenadoresDAT(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return apiRequest(() => api.get('/dat/coordenadores/', { params }));
}

export async function getCoordenadorDAT(id: ID): Promise<GenericRecord> {
  return apiRequest(() => api.get(`/dat/coordenadores/${id}/`));
}

export async function createCoordenadorDAT(data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.post('/dat/coordenadores/', data));
}

export async function updateCoordenadorDAT(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/coordenadores/${id}/`, data));
}

export async function deleteCoordenadorDAT(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/dat/coordenadores/${id}/`));
}

export async function getCoordenadorAlocacoes(id: ID): Promise<GenericRecord[]> {
  return apiRequest(() => api.get(`/dat/coordenadores/${id}/alocacoes/`));
}

// ========== PRODUTOS ==========

export async function listProdutosDAT(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return apiRequest(() => api.get('/produtos/', { params }));
}

export async function getProdutoDAT(id: ID): Promise<GenericRecord> {
  return apiRequest(() => api.get(`/produtos/${id}/`));
}

export async function createProdutoDAT(data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.post('/produtos/', data));
}

export async function updateProdutoDAT(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/produtos/${id}/`, data));
}

export async function deleteProdutoDAT(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/produtos/${id}/`));
}

// ========== ÁREAS ==========

export async function listAreasDAT(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return apiRequest(() => api.get('/dat/areas/', { params }));
}

// ========== COORDENADORES OPTIONS ==========

export async function getCoordenadoresOptions(): Promise<GenericRecord[]> {
  return apiRequest(() => api.get('/options/coordenadores/'));
}

export async function getAreasOptions(): Promise<GenericRecord[]> {
  return apiRequest(() => api.get('/options/areas/'));
}

export async function getProdutosOptions(): Promise<GenericRecord[]> {
  return apiRequest(() => api.get('/options/produtos/'));
}

// ========== PLANO FORMAÇÕES ==========

/**
 * List PlanoFormacoes records
 */
export async function listPlanoFormacoes(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return apiRequest(() => api.get('/dat/plano-formacoes/', { params }));
}

/**
 * Get single PlanoFormacoes
 * @param id - PlanoFormacoes ID
 */
export async function getPlanoFormacoes(id: ID): Promise<GenericRecord> {
  return apiRequest(() => api.get(`/dat/plano-formacoes/${id}/`));
}

/**
 * Create new PlanoFormacoes
 * @param data - PlanoFormacoes data
 */
export async function createPlanoFormacoes(data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.post('/dat/plano-formacoes/', data));
}

/**
 * Update PlanoFormacoes
 * @param id - PlanoFormacoes ID
 * @param data - Updated fields
 */
export async function updatePlanoFormacoes(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/plano-formacoes/${id}/`, data));
}

/**
 * Delete PlanoFormacoes (requires Superintendencia)
 * @param id - PlanoFormacoes ID
 */
export async function deletePlanoFormacoes(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/dat/plano-formacoes/${id}/`));
}

/**
 * Get PlanoFormacoes stats
 */
export async function getPlanoFormacoesStats(params: FilterParams = {}): Promise<GenericStats> {
  return apiRequest(() => api.get('/dat/plano-formacoes/stats/', { params }));
}

/**
 * Get PlanoFormacoes calendar data
 */
export async function getPlanoFormacoesCalendario(params: FilterParams = {}): Promise<GenericRecord[]> {
  return apiRequest(() => api.get('/dat/plano-formacoes/calendario/', { params }));
}

/**
 * Get PlanoFormacoes summary by project
 */
export async function getPlanoFormacoesResumoProjeto(params: FilterParams = {}): Promise<GenericRecord[]> {
  return apiRequest(() => api.get('/dat/plano-formacoes/resumo-projeto/', { params }));
}

/**
 * Update a specific formacao inline
 * @param planoId - PlanoFormacoes ID
 * @param numero - Formacao number (1-15)
 * @param data - Updated fields
 */
export async function updateFormacaoInline(planoId: ID, numero: number, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/plano-formacoes/${planoId}/formacao/${numero}/`, data));
}

/**
 * Update a specific acompanhamento inline
 * @param planoId - PlanoFormacoes ID
 * @param tipo - 'primeiro' or 'segundo'
 * @param data - Updated fields
 */
export async function updateAcompanhamentoInline(planoId: ID, tipo: 'primeiro' | 'segundo', data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/plano-formacoes/${planoId}/acompanhamento/${tipo}/`, data));
}

/**
 * Update a specific prova inline
 * @param planoId - PlanoFormacoes ID
 * @param numero - Prova number (1-3)
 * @param data - Updated fields
 */
export async function updateProvaInline(planoId: ID, numero: number, data: Record<string, unknown>): Promise<GenericRecord> {
  return apiRequest(() => api.patch(`/dat/plano-formacoes/${planoId}/prova/${numero}/`, data));
}
