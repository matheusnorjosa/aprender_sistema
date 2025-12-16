/**
 * API Client for DAT Module endpoints
 *
 * Ref: v2/docs/SPEC_DAT_REGISTROS.md
 *
 * Endpoints:
 * - /api/dat/registros/ - DATRegistro CRUD
 * - /api/projetos-gerais/ - ProjetoGeral CRUD
 */

import api from '../api';

/**
 * Helper to handle axios responses and errors
 */
async function apiRequest(requestFn) {
  try {
    const response = await requestFn();
    return response.data;
  } catch (error) {
    let message;
    if (error.response?.status === 403) {
      message = 'Acesso restrito ao setor DAT.';
    } else if (error.response?.status === 404) {
      message = 'Registro nao encontrado.';
    } else {
      message = error.response?.data?.detail || error.message || `Erro HTTP ${error.response?.status}`;
    }
    throw new Error(message);
  }
}

// ========== DAT REGISTROS ==========

/**
 * List DATRegistro records
 * @param {Object} params - Query parameters (municipio, projeto_geral, projeto, uf, usa_avaliar, status_formar, search, ordering, page)
 * @returns {Promise<Object>} Paginated response with results[]
 */
export async function listDATRegistros(params = {}) {
  return apiRequest(() => api.get('/dat/registros/', { params }));
}

/**
 * Get single DATRegistro
 * @param {number} id - DATRegistro ID
 */
export async function getDATRegistro(id) {
  return apiRequest(() => api.get(`/dat/registros/${id}/`));
}

/**
 * Create new DATRegistro
 * @param {Object} data - DATRegistro data
 */
export async function createDATRegistro(data) {
  return apiRequest(() => api.post('/dat/registros/', data));
}

/**
 * Update DATRegistro
 * @param {number} id - DATRegistro ID
 * @param {Object} data - Updated fields
 */
export async function updateDATRegistro(id, data) {
  return apiRequest(() => api.patch(`/dat/registros/${id}/`, data));
}

/**
 * Delete DATRegistro (requires Superintendencia)
 * @param {number} id - DATRegistro ID
 */
export async function deleteDATRegistro(id) {
  return apiRequest(() => api.delete(`/dat/registros/${id}/`));
}

/**
 * Get DATRegistro stats
 * @returns {Promise<Object>} Stats: {total, completos_formar, completos_avaliar, usa_avaliar, por_uf}
 */
export async function getDATRegistroStats() {
  return apiRequest(() => api.get('/dat/registros/stats/'));
}

/**
 * Export DATRegistros to CSV
 * @param {Object} params - Filter parameters
 * @returns {Promise<Blob>} CSV file blob
 */
export async function exportDATRegistros(params = {}) {
  const response = await api.get('/dat/registros/export/', {
    params,
    responseType: 'blob',
  });
  return response.data;
}

// ========== PROJETOS GERAIS ==========

/**
 * List ProjetoGeral records
 * @param {Object} params - Query parameters (usa_avaliar, ativo, tipo_calculo_codigos, search, ordering, page, minimal)
 * @returns {Promise<Object>} Paginated response with results[]
 */
export async function listProjetosGerais(params = {}) {
  return apiRequest(() => api.get('/projetos-gerais/', { params }));
}

/**
 * Get single ProjetoGeral
 * @param {number} id - ProjetoGeral ID
 */
export async function getProjetoGeral(id) {
  return apiRequest(() => api.get(`/projetos-gerais/${id}/`));
}

/**
 * Create new ProjetoGeral
 * @param {Object} data - ProjetoGeral data (nome, usa_avaliar, tipo_calculo_codigos, divisor_aluno, multiplicador_professor)
 */
export async function createProjetoGeral(data) {
  return apiRequest(() => api.post('/projetos-gerais/', data));
}

/**
 * Update ProjetoGeral
 * @param {number} id - ProjetoGeral ID
 * @param {Object} data - Updated fields
 */
export async function updateProjetoGeral(id, data) {
  return apiRequest(() => api.patch(`/projetos-gerais/${id}/`, data));
}

/**
 * Delete ProjetoGeral (requires Superintendencia)
 * @param {number} id - ProjetoGeral ID
 */
export async function deleteProjetoGeral(id) {
  return apiRequest(() => api.delete(`/projetos-gerais/${id}/`));
}

/**
 * Get Projetos linked to a ProjetoGeral
 * @param {number} id - ProjetoGeral ID
 * @returns {Promise<Array>} List of linked Projeto objects
 */
export async function getProjetosForProjetoGeral(id) {
  return apiRequest(() => api.get(`/projetos-gerais/${id}/projetos/`));
}

// ========== OPTIONS (for dropdowns) ==========

/**
 * Get minimal list of ProjetosGerais for dropdown
 * @returns {Promise<Array>} [{id, nome, usa_avaliar}]
 */
export async function getProjetosGeraisOptions() {
  return apiRequest(() => api.get('/projetos-gerais/', { params: { minimal: 'true' } }));
}

/**
 * Get Municipios options for dropdown
 * @returns {Promise<Array>} [{id, nome, uf}]
 */
export async function getMunicipiosOptions() {
  return apiRequest(() => api.get('/options/municipios/'));
}

/**
 * Get Projetos options for dropdown
 * @returns {Promise<Array>} [{id, nome, codigo, fluxo}]
 */
export async function getProjetosOptions() {
  return apiRequest(() => api.get('/options/projetos/'));
}

// ========== AÇÕES (Ciclo de Vida de Projetos) ==========

/**
 * Listar ações com filtros
 * @param {Object} params - search, status_carta, status_contato, status_reuniao, status_entrega,
 *                          projeto_id, municipio_id, coordenador_id, uf, page
 */
export async function listAcoes(params = {}) {
  return apiRequest(() => api.get('/dat/acoes/', { params }));
}

export async function getAcao(id) {
  return apiRequest(() => api.get(`/dat/acoes/${id}/`));
}

export async function createAcao(data) {
  return apiRequest(() => api.post('/dat/acoes/', data));
}

export async function updateAcao(id, data) {
  return apiRequest(() => api.patch(`/dat/acoes/${id}/`, data));
}

export async function deleteAcao(id) {
  return apiRequest(() => api.delete(`/dat/acoes/${id}/`));
}

export async function getAcoesStats(params = {}) {
  return apiRequest(() => api.get('/dat/acoes/stats/', { params }));
}

// ========== COMPRAS (Controle de Materiais) ==========

/**
 * Listar compras com filtros
 * @param {Object} params - search, status, projeto_id, municipio_id, produto_id, uf, ano_uso, page
 */
export async function listCompras(params = {}) {
  return apiRequest(() => api.get('/dat/compras/', { params }));
}

export async function getCompra(id) {
  return apiRequest(() => api.get(`/dat/compras/${id}/`));
}

export async function createCompra(data) {
  return apiRequest(() => api.post('/dat/compras/', data));
}

export async function updateCompra(id, data) {
  return apiRequest(() => api.patch(`/dat/compras/${id}/`, data));
}

export async function deleteCompra(id) {
  return apiRequest(() => api.delete(`/dat/compras/${id}/`));
}

export async function getComprasStats(params = {}) {
  return apiRequest(() => api.get('/dat/compras/stats/', { params }));
}

// ========== CADASTROS (Workflow FORMAR/AVALIAR) ==========

/**
 * Listar cadastros com filtros
 * @param {Object} params - search, plataforma, projeto_id, municipio_id, status_etapa, page
 */
export async function listCadastros(params = {}) {
  return apiRequest(() => api.get('/dat/cadastros/', { params }));
}

export async function getCadastro(id) {
  return apiRequest(() => api.get(`/dat/cadastros/${id}/`));
}

export async function createCadastro(data) {
  return apiRequest(() => api.post('/dat/cadastros/', data));
}

export async function updateCadastro(id, data) {
  return apiRequest(() => api.patch(`/dat/cadastros/${id}/`, data));
}

export async function deleteCadastro(id) {
  return apiRequest(() => api.delete(`/dat/cadastros/${id}/`));
}

export async function updateCadastroEtapa(id, etapa, status) {
  return apiRequest(() => api.patch(`/dat/cadastros/${id}/etapa/`, { etapa, status }));
}

export async function getCadastrosStats(params = {}) {
  return apiRequest(() => api.get('/dat/cadastros/stats/', { params }));
}

// ========== FORMAÇÕES (Calendário de Treinamentos) ==========

/**
 * Listar formações com filtros
 * @param {Object} params - search, status, projeto_id, municipio_id, coordenador_id,
 *                          formador_id, data_inicio, data_fim, modalidade, page
 */
export async function listFormacoes(params = {}) {
  return apiRequest(() => api.get('/dat/formacoes/', { params }));
}

export async function getFormacao(id) {
  return apiRequest(() => api.get(`/dat/formacoes/${id}/`));
}

export async function createFormacao(data) {
  return apiRequest(() => api.post('/dat/formacoes/', data));
}

export async function updateFormacao(id, data) {
  return apiRequest(() => api.patch(`/dat/formacoes/${id}/`, data));
}

export async function deleteFormacao(id) {
  return apiRequest(() => api.delete(`/dat/formacoes/${id}/`));
}

export async function getFormacoesStats(params = {}) {
  return apiRequest(() => api.get('/dat/formacoes/stats/', { params }));
}

export async function getFormacoesCalendario(params = {}) {
  return apiRequest(() => api.get('/dat/formacoes/calendario/', { params }));
}

// ========== COORDENADORES ==========

/**
 * Listar coordenadores com filtros
 * @param {Object} params - search, area, ativo, page
 */
export async function listCoordenadoresDAT(params = {}) {
  return apiRequest(() => api.get('/dat/coordenadores/', { params }));
}

export async function getCoordenadorDAT(id) {
  return apiRequest(() => api.get(`/dat/coordenadores/${id}/`));
}

export async function createCoordenadorDAT(data) {
  return apiRequest(() => api.post('/dat/coordenadores/', data));
}

export async function updateCoordenadorDAT(id, data) {
  return apiRequest(() => api.patch(`/dat/coordenadores/${id}/`, data));
}

export async function deleteCoordenadorDAT(id) {
  return apiRequest(() => api.delete(`/dat/coordenadores/${id}/`));
}

export async function getCoordenadorAlocacoes(id) {
  return apiRequest(() => api.get(`/dat/coordenadores/${id}/alocacoes/`));
}

// ========== PRODUTOS ==========

export async function listProdutosDAT(params = {}) {
  return apiRequest(() => api.get('/dat/produtos/', { params }));
}

export async function getProdutoDAT(id) {
  return apiRequest(() => api.get(`/dat/produtos/${id}/`));
}

export async function createProdutoDAT(data) {
  return apiRequest(() => api.post('/dat/produtos/', data));
}

export async function updateProdutoDAT(id, data) {
  return apiRequest(() => api.patch(`/dat/produtos/${id}/`, data));
}

export async function deleteProdutoDAT(id) {
  return apiRequest(() => api.delete(`/dat/produtos/${id}/`));
}

// ========== ÁREAS ==========

export async function listAreasDAT(params = {}) {
  return apiRequest(() => api.get('/dat/areas/', { params }));
}

// ========== COORDENADORES OPTIONS ==========

export async function getCoordenadoresOptions() {
  return apiRequest(() => api.get('/options/coordenadores/'));
}

export async function getAreasOptions() {
  return apiRequest(() => api.get('/options/areas/'));
}

export async function getProdutosOptions() {
  return apiRequest(() => api.get('/options/produtos/'));
}
