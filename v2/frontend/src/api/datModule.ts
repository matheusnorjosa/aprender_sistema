/**
 * API Client for DAT Module endpoints
 *
 * Ref: v2/docs/SPEC_DAT_REGISTROS.md
 *
 * Migrated from axios to fetchAPI (Epic #1039)
 */

import { fetchAPI, fetchBlob, fetchWithErrorMapping, buildUrl, type QueryParams } from './config';
import type { ID, PaginatedResponse, MunicipioOption, ProjetoOption, Projeto } from '../types';

// ========== TYPE DEFINITIONS ==========

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

export interface DATRegistroStats {
  total: number;
  completos_formar: number;
  completos_avaliar: number;
  usa_avaliar: number;
  por_uf: Record<string, number>;
}

export interface ProjetoGeral {
  id: ID;
  nome: string;
  usa_avaliar: boolean;
  tipo_calculo_codigos: string;
  divisor_aluno?: number;
  multiplicador_professor?: number;
  ativo: boolean;
}

export interface ProjetoGeralOption {
  id: ID;
  nome: string;
  usa_avaliar: boolean;
}

export interface GenericRecord {
  id: ID;
  [key: string]: unknown;
}

export interface GenericStats {
  [key: string]: number | Record<string, number>;
}

export interface FilterParams {
  search?: string;
  page?: number;
  ordering?: string;
  [key: string]: string | number | boolean | undefined;
}

// Common error mapping for DAT endpoints
const DAT_ERROR_MAP: Record<number, string> = {
  403: 'Acesso restrito ao setor DAT.',
  404: 'Registro nao encontrado.',
};

// ========== DAT REGISTROS ==========

export async function listDATRegistros(params: FilterParams = {}): Promise<PaginatedResponse<DATRegistro>> {
  return fetchWithErrorMapping(buildUrl('/dat/registros/', params as QueryParams), {}, DAT_ERROR_MAP);
}

export async function getDATRegistro(id: ID): Promise<DATRegistro> {
  return fetchWithErrorMapping(`/dat/registros/${id}/`, {}, DAT_ERROR_MAP);
}

export async function createDATRegistro(data: Partial<DATRegistro>): Promise<DATRegistro> {
  return fetchWithErrorMapping('/dat/registros/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateDATRegistro(id: ID, data: Partial<DATRegistro>): Promise<DATRegistro> {
  return fetchWithErrorMapping(`/dat/registros/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function deleteDATRegistro(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/dat/registros/${id}/`, { method: 'DELETE' }, DAT_ERROR_MAP);
}

export async function getDATRegistroStats(): Promise<DATRegistroStats> {
  return fetchAPI('/dat/registros/stats/');
}

export async function exportDATRegistros(params: FilterParams = {}): Promise<Blob> {
  return fetchBlob(buildUrl('/dat/registros/export/', params as QueryParams));
}

// ========== PROJETOS GERAIS ==========

export async function listProjetosGerais(params: FilterParams = {}): Promise<PaginatedResponse<ProjetoGeral>> {
  return fetchWithErrorMapping(buildUrl('/projetos-gerais/', params as QueryParams), {}, DAT_ERROR_MAP);
}

export async function getProjetoGeral(id: ID): Promise<ProjetoGeral> {
  return fetchWithErrorMapping(`/projetos-gerais/${id}/`, {}, DAT_ERROR_MAP);
}

export async function createProjetoGeral(data: Partial<ProjetoGeral>): Promise<ProjetoGeral> {
  return fetchWithErrorMapping('/projetos-gerais/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateProjetoGeral(id: ID, data: Partial<ProjetoGeral>): Promise<ProjetoGeral> {
  return fetchWithErrorMapping(`/projetos-gerais/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function deleteProjetoGeral(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/projetos-gerais/${id}/`, { method: 'DELETE' }, DAT_ERROR_MAP);
}

export async function getProjetosForProjetoGeral(id: ID): Promise<Projeto[]> {
  return fetchAPI(`/projetos-gerais/${id}/projetos/`);
}

// ========== OPTIONS (for dropdowns) ==========

export async function getProjetosGeraisOptions(): Promise<ProjetoGeralOption[]> {
  return fetchAPI(buildUrl('/projetos-gerais/', { minimal: 'true' }));
}

export async function getMunicipiosOptions(): Promise<MunicipioOption[]> {
  return fetchAPI('/options/municipios/');
}

export async function getProjetosOptions(): Promise<ProjetoOption[]> {
  return fetchAPI('/options/projetos/');
}

// ========== AÇÕES (Ciclo de Vida de Projetos) ==========

export async function listAcoes(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return fetchWithErrorMapping(buildUrl('/dat/acoes-ciclo/', params as QueryParams), {}, DAT_ERROR_MAP);
}

export async function getAcao(id: ID): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/acoes-ciclo/${id}/`, {}, DAT_ERROR_MAP);
}

export async function createAcao(data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping('/dat/acoes-ciclo/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateAcao(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/acoes-ciclo/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function deleteAcao(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/dat/acoes-ciclo/${id}/`, { method: 'DELETE' }, DAT_ERROR_MAP);
}

export async function getAcoesStats(params: FilterParams = {}): Promise<GenericStats> {
  return fetchAPI(buildUrl('/dat/acoes-ciclo/stats/', params as QueryParams));
}

// ========== COMPRAS (Controle de Materiais) ==========

export async function listCompras(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return fetchWithErrorMapping(buildUrl('/dat/compras-materiais/', params as QueryParams), {}, DAT_ERROR_MAP);
}

export async function getCompra(id: ID): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/compras-materiais/${id}/`, {}, DAT_ERROR_MAP);
}

export async function createCompra(data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping('/dat/compras-materiais/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateCompra(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/compras-materiais/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function deleteCompra(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/dat/compras-materiais/${id}/`, { method: 'DELETE' }, DAT_ERROR_MAP);
}

export async function getComprasStats(params: FilterParams = {}): Promise<GenericStats> {
  return fetchAPI(buildUrl('/dat/compras-materiais/stats/', params as QueryParams));
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
  return fetchAPI(buildUrl('/dat/compras-materiais/dashboard/', params as QueryParams));
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
  return fetchAPI(buildUrl('/dat/compras-materiais/pendencias/', params as QueryParams));
}

// ========== CADASTROS (Workflow FORMAR/AVALIAR) ==========

export async function listCadastros(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return fetchWithErrorMapping(buildUrl('/dat/cadastros/', params as QueryParams), {}, DAT_ERROR_MAP);
}

export async function getCadastro(id: ID): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/cadastros/${id}/`, {}, DAT_ERROR_MAP);
}

export async function createCadastro(data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping('/dat/cadastros/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateCadastro(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/cadastros/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function deleteCadastro(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/dat/cadastros/${id}/`, { method: 'DELETE' }, DAT_ERROR_MAP);
}

export async function updateCadastroEtapa(id: ID, etapa: string, status: string): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/cadastros/${id}/etapa/`, {
    method: 'POST',
    body: JSON.stringify({ etapa, status }),
  }, DAT_ERROR_MAP);
}

export async function getCadastrosStats(params: FilterParams = {}): Promise<GenericStats> {
  return fetchAPI(buildUrl('/dat/cadastros/stats/', params as QueryParams));
}

// ========== FORMAÇÕES (Calendário de Treinamentos) ==========

export async function listFormacoes(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return fetchWithErrorMapping(buildUrl('/dat/formacoes/', params as QueryParams), {}, DAT_ERROR_MAP);
}

export async function getFormacao(id: ID): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/formacoes/${id}/`, {}, DAT_ERROR_MAP);
}

export async function createFormacao(data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping('/dat/formacoes/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateFormacao(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/formacoes/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function deleteFormacao(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/dat/formacoes/${id}/`, { method: 'DELETE' }, DAT_ERROR_MAP);
}

export async function getFormacoesStats(params: FilterParams = {}): Promise<GenericStats> {
  return fetchAPI(buildUrl('/dat/formacoes/stats/', params as QueryParams));
}

export async function getFormacoesCalendario(params: FilterParams = {}): Promise<GenericRecord[]> {
  return fetchAPI(buildUrl('/dat/formacoes/calendario/', params as QueryParams));
}

// ========== COORDENADORES ==========

export async function listCoordenadoresDAT(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return fetchWithErrorMapping(buildUrl('/dat/coordenadores/', params as QueryParams), {}, DAT_ERROR_MAP);
}

export async function getCoordenadorDAT(id: ID): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/coordenadores/${id}/`, {}, DAT_ERROR_MAP);
}

export async function createCoordenadorDAT(data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping('/dat/coordenadores/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateCoordenadorDAT(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/coordenadores/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function deleteCoordenadorDAT(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/dat/coordenadores/${id}/`, { method: 'DELETE' }, DAT_ERROR_MAP);
}

export async function getCoordenadorAlocacoes(id: ID): Promise<GenericRecord[]> {
  return fetchAPI(`/dat/coordenadores/${id}/alocacoes/`);
}

// ========== PRODUTOS ==========

export async function listProdutosDAT(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return fetchAPI(buildUrl('/produtos/', params as QueryParams));
}

export async function getProdutoDAT(id: ID): Promise<GenericRecord> {
  return fetchAPI(`/produtos/${id}/`);
}

export async function createProdutoDAT(data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchAPI('/produtos/', { method: 'POST', body: JSON.stringify(data) });
}

export async function updateProdutoDAT(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchAPI(`/produtos/${id}/`, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function deleteProdutoDAT(id: ID): Promise<void> {
  await fetchAPI(`/produtos/${id}/`, { method: 'DELETE' });
}

// ========== ÁREAS ==========

export async function listAreasDAT(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return fetchAPI(buildUrl('/dat/areas/', params as QueryParams));
}

// ========== COORDENADORES OPTIONS ==========

export async function getCoordenadoresOptions(): Promise<GenericRecord[]> {
  return fetchAPI('/options/coordenadores/');
}

export async function getAreasOptions(): Promise<GenericRecord[]> {
  return fetchAPI('/options/areas/');
}

export async function getProdutosOptions(): Promise<GenericRecord[]> {
  return fetchAPI('/options/produtos/');
}

// ========== PLANO FORMAÇÕES ==========

export async function listPlanoFormacoes(params: FilterParams = {}): Promise<PaginatedResponse<GenericRecord>> {
  return fetchWithErrorMapping(buildUrl('/dat/plano-formacoes/', params as QueryParams), {}, DAT_ERROR_MAP);
}

export async function getPlanoFormacoes(id: ID): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/plano-formacoes/${id}/`, {}, DAT_ERROR_MAP);
}

export async function createPlanoFormacoes(data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping('/dat/plano-formacoes/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updatePlanoFormacoes(id: ID, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/plano-formacoes/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function deletePlanoFormacoes(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/dat/plano-formacoes/${id}/`, { method: 'DELETE' }, DAT_ERROR_MAP);
}

export async function getPlanoFormacoesStats(params: FilterParams = {}): Promise<GenericStats> {
  return fetchAPI(buildUrl('/dat/plano-formacoes/stats/', params as QueryParams));
}

export async function getPlanoFormacoesCalendario(params: FilterParams = {}): Promise<GenericRecord[]> {
  return fetchAPI(buildUrl('/dat/plano-formacoes/calendario/', params as QueryParams));
}

export async function getPlanoFormacoesResumoProjeto(params: FilterParams = {}): Promise<GenericRecord[]> {
  return fetchAPI(buildUrl('/dat/plano-formacoes/resumo-projeto/', params as QueryParams));
}

export async function updateFormacaoInline(planoId: ID, numero: number, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/plano-formacoes/${planoId}/formacao/${numero}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateAcompanhamentoInline(planoId: ID, tipo: 'primeiro' | 'segundo', data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/plano-formacoes/${planoId}/acompanhamento/${tipo}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}

export async function updateProvaInline(planoId: ID, numero: number, data: Record<string, unknown>): Promise<GenericRecord> {
  return fetchWithErrorMapping(`/dat/plano-formacoes/${planoId}/prova/${numero}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, DAT_ERROR_MAP);
}
