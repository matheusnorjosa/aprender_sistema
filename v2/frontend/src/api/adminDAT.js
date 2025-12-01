/**
 * API Client for Admin DAT endpoints
 *
 * GAP-001/002 resolved: Endpoints reactivated/created in Phase 1 Iteration 2
 *
 * Issue #135: Uses axios instance with CSRF token handling for all requests
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
    // Extract error message from axios error
    let message;
    if (error.response?.status === 403) {
      message = 'Você não tem permissão para realizar esta ação.';
    } else if (error.response?.status === 404) {
      message = 'Recurso não encontrado.';
    } else {
      message = error.response?.data?.detail || error.message || `Erro HTTP ${error.response?.status}`;
    }

    throw new Error(message);
  }
}

// ========== USUARIOS ==========

/**
 * List all users (admin)
 * @param {Object} params - Query parameters (search, is_active, ordering, page)
 * @returns {Promise<Object>} Paginated response with results[]
 */
export async function listUsers(params = {}) {
  return apiRequest(() => api.get('/usuarios-admin/', { params }));
}

/**
 * Get single user
 * @param {number} id - User ID
 */
export async function getUser(id) {
  return apiRequest(() => api.get(`/usuarios-admin/${id}/`));
}

/**
 * Create new user
 * @param {Object} data - User data (username, email, password, first_name, last_name, cpf, etc.)
 */
export async function createUser(data) {
  return apiRequest(() => api.post('/usuarios-admin/', data));
}

/**
 * Update user
 * @param {number} id - User ID
 * @param {Object} data - Updated fields
 */
export async function updateUser(id, data) {
  return apiRequest(() => api.patch(`/usuarios-admin/${id}/`, data));
}

/**
 * Delete user
 * @param {number} id - User ID
 */
export async function deleteUser(id) {
  return apiRequest(() => api.delete(`/usuarios-admin/${id}/`));
}

/**
 * Assign groups to user
 * @param {number} userId - User ID
 * @param {Object} data - {group_ids: [1, 2, 3]}
 * @returns {Promise<Object>} Updated user with groups
 *
 * GAP-003 (resolved): Endpoint for assigning groups to users.
 * Phase 1 Iteration 3 - DAT/GCal Plan.
 */
export async function assignGroups(userId, data) {
  return apiRequest(() => api.post(`/usuarios-admin/${userId}/assign_groups/`, data));
}

// ========== GRUPOS ==========

/**
 * List all groups
 * @param {Object} params - Query parameters (search, ordering, page)
 */
export async function listGroups(params = {}) {
  return apiRequest(() => api.get('/grupos/', { params }));
}

/**
 * Get single group
 * @param {number} id - Group ID
 */
export async function getGroup(id) {
  return apiRequest(() => api.get(`/grupos/${id}/`));
}

/**
 * Create new group
 * @param {Object} data - Group data (name)
 */
export async function createGroup(data) {
  return apiRequest(() => api.post('/grupos/', data));
}

/**
 * Update group
 * @param {number} id - Group ID
 * @param {Object} data - Updated fields
 */
export async function updateGroup(id, data) {
  return apiRequest(() => api.patch(`/grupos/${id}/`, data));
}

/**
 * Delete group
 * @param {number} id - Group ID
 */
export async function deleteGroup(id) {
  return apiRequest(() => api.delete(`/grupos/${id}/`));
}

// ========== MUNICIPIOS ==========

/**
 * List all municipalities
 * @param {Object} params - Query parameters (uf, ativo, search, ordering, page)
 */
export async function listMunicipios(params = {}) {
  return apiRequest(() => api.get('/municipios/', { params }));
}

/**
 * Get single municipality
 * @param {number} id - Municipality ID
 */
export async function getMunicipio(id) {
  return apiRequest(() => api.get(`/municipios/${id}/`));
}

/**
 * Create new municipality
 * @param {Object} data - Municipality data (nome, uf, ibge_code, ativo)
 */
export async function createMunicipio(data) {
  return apiRequest(() => api.post('/municipios/', data));
}

/**
 * Update municipality
 * @param {number} id - Municipality ID
 * @param {Object} data - Updated fields
 */
export async function updateMunicipio(id, data) {
  return apiRequest(() => api.patch(`/municipios/${id}/`, data));
}

/**
 * Delete municipality
 * @param {number} id - Municipality ID
 */
export async function deleteMunicipio(id) {
  return apiRequest(() => api.delete(`/municipios/${id}/`));
}

// ========== PROJETOS ==========

/**
 * List all projects
 * @param {Object} params - Query parameters (ativo, search, ordering, page)
 */
export async function listProjetos(params = {}) {
  return apiRequest(() => api.get('/projetos/', { params }));
}

/**
 * Get single project
 * @param {number} id - Project ID
 */
export async function getProjeto(id) {
  return apiRequest(() => api.get(`/projetos/${id}/`));
}

/**
 * Create new project
 * @param {Object} data - Project data (nome, codigo, fluxo, ativo)
 */
export async function createProjeto(data) {
  return apiRequest(() => api.post('/projetos/', data));
}

/**
 * Update project
 * @param {number} id - Project ID
 * @param {Object} data - Updated fields
 */
export async function updateProjeto(id, data) {
  return apiRequest(() => api.patch(`/projetos/${id}/`, data));
}

/**
 * Delete project
 * @param {number} id - Project ID
 */
export async function deleteProjeto(id) {
  return apiRequest(() => api.delete(`/projetos/${id}/`));
}
