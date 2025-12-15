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
