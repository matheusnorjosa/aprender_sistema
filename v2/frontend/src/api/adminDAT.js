/**
 * API Client for Admin DAT endpoints
 *
 * GAP-001/002 resolved: Endpoints reactivated/created in Phase 1 Iteration 2
 */

const API_BASE = '/api';

/**
 * Fetch with credentials and error handling
 */
async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));

    // Status-specific error handling
    let message;
    if (response.status === 403) {
      message = 'Você não tem permissão para realizar esta ação.';
    } else if (response.status === 404) {
      message = 'Recurso não encontrado.';
    } else {
      message = error.detail || `Erro HTTP ${response.status}`;
    }

    throw new Error(message);
  }

  return response.json();
}

// ========== USUARIOS ==========

/**
 * List all users (admin)
 * @param {Object} params - Query parameters (search, is_active, ordering, page)
 * @returns {Promise<Object>} Paginated response with results[]
 */
export async function listUsers(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`${API_BASE}/usuarios-admin/?${query}`);
}

/**
 * Get single user
 * @param {number} id - User ID
 */
export async function getUser(id) {
  return apiFetch(`${API_BASE}/usuarios-admin/${id}/`);
}

/**
 * Create new user
 * @param {Object} data - User data (username, email, password, first_name, last_name, cpf, etc.)
 */
export async function createUser(data) {
  return apiFetch(`${API_BASE}/usuarios-admin/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update user
 * @param {number} id - User ID
 * @param {Object} data - Updated fields
 */
export async function updateUser(id, data) {
  return apiFetch(`${API_BASE}/usuarios-admin/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete user
 * @param {number} id - User ID
 */
export async function deleteUser(id) {
  return apiFetch(`${API_BASE}/usuarios-admin/${id}/`, {
    method: 'DELETE',
  });
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
  return apiFetch(`${API_BASE}/usuarios-admin/${userId}/assign_groups/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ========== GRUPOS ==========

/**
 * List all groups
 * @param {Object} params - Query parameters (search, ordering, page)
 */
export async function listGroups(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`${API_BASE}/grupos/?${query}`);
}

/**
 * Get single group
 * @param {number} id - Group ID
 */
export async function getGroup(id) {
  return apiFetch(`${API_BASE}/grupos/${id}/`);
}

/**
 * Create new group
 * @param {Object} data - Group data (name)
 */
export async function createGroup(data) {
  return apiFetch(`${API_BASE}/grupos/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update group
 * @param {number} id - Group ID
 * @param {Object} data - Updated fields
 */
export async function updateGroup(id, data) {
  return apiFetch(`${API_BASE}/grupos/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete group
 * @param {number} id - Group ID
 */
export async function deleteGroup(id) {
  return apiFetch(`${API_BASE}/grupos/${id}/`, {
    method: 'DELETE',
  });
}

// ========== MUNICIPIOS ==========

/**
 * List all municipalities
 * @param {Object} params - Query parameters (uf, ativo, search, ordering, page)
 */
export async function listMunicipios(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`${API_BASE}/municipios/?${query}`);
}

/**
 * Get single municipality
 * @param {number} id - Municipality ID
 */
export async function getMunicipio(id) {
  return apiFetch(`${API_BASE}/municipios/${id}/`);
}

/**
 * Create new municipality
 * @param {Object} data - Municipality data (nome, uf, ibge_code, ativo)
 */
export async function createMunicipio(data) {
  return apiFetch(`${API_BASE}/municipios/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update municipality
 * @param {number} id - Municipality ID
 * @param {Object} data - Updated fields
 */
export async function updateMunicipio(id, data) {
  return apiFetch(`${API_BASE}/municipios/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete municipality
 * @param {number} id - Municipality ID
 */
export async function deleteMunicipio(id) {
  return apiFetch(`${API_BASE}/municipios/${id}/`, {
    method: 'DELETE',
  });
}

// ========== PROJETOS ==========

/**
 * List all projects
 * @param {Object} params - Query parameters (ativo, search, ordering, page)
 */
export async function listProjetos(params = {}) {
  const query = new URLSearchParams(params).toString();
  return apiFetch(`${API_BASE}/projetos/?${query}`);
}

/**
 * Get single project
 * @param {number} id - Project ID
 */
export async function getProjeto(id) {
  return apiFetch(`${API_BASE}/projetos/${id}/`);
}

/**
 * Create new project
 * @param {Object} data - Project data (nome, codigo, fluxo, ativo)
 */
export async function createProjeto(data) {
  return apiFetch(`${API_BASE}/projetos/`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

/**
 * Update project
 * @param {number} id - Project ID
 * @param {Object} data - Updated fields
 */
export async function updateProjeto(id, data) {
  return apiFetch(`${API_BASE}/projetos/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Delete project
 * @param {number} id - Project ID
 */
export async function deleteProjeto(id) {
  return apiFetch(`${API_BASE}/projetos/${id}/`, {
    method: 'DELETE',
  });
}
