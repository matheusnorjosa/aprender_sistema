/**
 * API Client for Admin DAT endpoints
 *
 * GAP-001/002 resolved: Endpoints reactivated/created in Phase 1 Iteration 2
 *
 * Issue #135: Uses axios instance with CSRF token handling for all requests
 */

import type { AxiosResponse, AxiosError } from 'axios';
import api from '../api';
import type { ID, PaginatedResponse, Municipio, Projeto, Group } from '../types';

/**
 * Admin user data
 */
export interface AdminUser {
  id: ID;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  cpf?: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  groups: Group[];
  date_joined: string;
  last_login: string | null;
}

/**
 * User create/update payload
 */
export interface UserPayload {
  username?: string;
  email?: string;
  password?: string;
  first_name?: string;
  last_name?: string;
  cpf?: string;
  is_active?: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
}

/**
 * Group assignment payload
 */
export interface AssignGroupsPayload {
  group_ids: ID[];
}

/**
 * Group create/update payload
 */
export interface GroupPayload {
  name: string;
}

/**
 * Municipality create/update payload
 */
export interface MunicipioPayload {
  nome?: string;
  uf?: string;
  ibge_code?: string;
  ativo?: boolean;
}

/**
 * Project create/update payload
 */
export interface ProjetoPayload {
  nome?: string;
  codigo?: string;
  fluxo?: 'SUPER' | 'NAO_SUPER';
  ativo?: boolean;
}

/**
 * Query parameters for list endpoints
 */
export interface ListParams {
  search?: string;
  is_active?: boolean;
  ativo?: boolean;
  uf?: string;
  ordering?: string;
  page?: number;
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
    // Extract error message from axios error
    const axiosError = error as AxiosErrorWithResponse;
    let message: string;
    if (axiosError.response?.status === 403) {
      message = 'Você não tem permissão para realizar esta ação.';
    } else if (axiosError.response?.status === 404) {
      message = 'Recurso não encontrado.';
    } else {
      message = axiosError.response?.data?.detail || axiosError.message || `Erro HTTP ${axiosError.response?.status}`;
    }

    throw new Error(message);
  }
}

// ========== USUARIOS ==========

/**
 * List all users (admin)
 * @param params - Query parameters (search, is_active, ordering, page)
 */
export async function listUsers(params: ListParams = {}): Promise<PaginatedResponse<AdminUser>> {
  return apiRequest(() => api.get('/usuarios-admin/', { params }));
}

/**
 * Get single user
 * @param id - User ID
 */
export async function getUser(id: ID): Promise<AdminUser> {
  return apiRequest(() => api.get(`/usuarios-admin/${id}/`));
}

/**
 * Create new user
 * @param data - User data (username, email, password, first_name, last_name, cpf, etc.)
 */
export async function createUser(data: UserPayload): Promise<AdminUser> {
  return apiRequest(() => api.post('/usuarios-admin/', data));
}

/**
 * Update user
 * @param id - User ID
 * @param data - Updated fields
 */
export async function updateUser(id: ID, data: UserPayload): Promise<AdminUser> {
  return apiRequest(() => api.patch(`/usuarios-admin/${id}/`, data));
}

/**
 * Delete user
 * @param id - User ID
 */
export async function deleteUser(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/usuarios-admin/${id}/`));
}

/**
 * Assign groups to user
 * @param userId - User ID
 * @param data - {group_ids: [1, 2, 3]}
 *
 * GAP-003 (resolved): Endpoint for assigning groups to users.
 * Phase 1 Iteration 3 - DAT/GCal Plan.
 */
export async function assignGroups(userId: ID, data: AssignGroupsPayload): Promise<AdminUser> {
  return apiRequest(() => api.post(`/usuarios-admin/${userId}/assign_groups/`, data));
}

// ========== GRUPOS ==========

/**
 * List all groups
 * @param params - Query parameters (search, ordering, page)
 */
export async function listGroups(params: ListParams = {}): Promise<PaginatedResponse<Group>> {
  return apiRequest(() => api.get('/grupos/', { params }));
}

/**
 * Get single group
 * @param id - Group ID
 */
export async function getGroup(id: ID): Promise<Group> {
  return apiRequest(() => api.get(`/grupos/${id}/`));
}

/**
 * Create new group
 * @param data - Group data (name)
 */
export async function createGroup(data: GroupPayload): Promise<Group> {
  return apiRequest(() => api.post('/grupos/', data));
}

/**
 * Update group
 * @param id - Group ID
 * @param data - Updated fields
 */
export async function updateGroup(id: ID, data: GroupPayload): Promise<Group> {
  return apiRequest(() => api.patch(`/grupos/${id}/`, data));
}

/**
 * Delete group
 * @param id - Group ID
 */
export async function deleteGroup(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/grupos/${id}/`));
}

// ========== MUNICIPIOS ==========

/**
 * List all municipalities
 * @param params - Query parameters (uf, ativo, search, ordering, page)
 */
export async function listMunicipios(params: ListParams = {}): Promise<PaginatedResponse<Municipio>> {
  return apiRequest(() => api.get('/municipios/', { params }));
}

/**
 * Get single municipality
 * @param id - Municipality ID
 */
export async function getMunicipio(id: ID): Promise<Municipio> {
  return apiRequest(() => api.get(`/municipios/${id}/`));
}

/**
 * Create new municipality
 * @param data - Municipality data (nome, uf, ibge_code, ativo)
 */
export async function createMunicipio(data: MunicipioPayload): Promise<Municipio> {
  return apiRequest(() => api.post('/municipios/', data));
}

/**
 * Update municipality
 * @param id - Municipality ID
 * @param data - Updated fields
 */
export async function updateMunicipio(id: ID, data: MunicipioPayload): Promise<Municipio> {
  return apiRequest(() => api.patch(`/municipios/${id}/`, data));
}

/**
 * Delete municipality
 * @param id - Municipality ID
 */
export async function deleteMunicipio(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/municipios/${id}/`));
}

// ========== PROJETOS ==========

/**
 * List all projects
 * @param params - Query parameters (ativo, search, ordering, page)
 */
export async function listProjetos(params: ListParams = {}): Promise<PaginatedResponse<Projeto>> {
  return apiRequest(() => api.get('/projetos/', { params }));
}

/**
 * Get single project
 * @param id - Project ID
 */
export async function getProjeto(id: ID): Promise<Projeto> {
  return apiRequest(() => api.get(`/projetos/${id}/`));
}

/**
 * Create new project
 * @param data - Project data (nome, codigo, fluxo, ativo)
 */
export async function createProjeto(data: ProjetoPayload): Promise<Projeto> {
  return apiRequest(() => api.post('/projetos/', data));
}

/**
 * Update project
 * @param id - Project ID
 * @param data - Updated fields
 */
export async function updateProjeto(id: ID, data: ProjetoPayload): Promise<Projeto> {
  return apiRequest(() => api.patch(`/projetos/${id}/`, data));
}

/**
 * Delete project
 * @param id - Project ID
 */
export async function deleteProjeto(id: ID): Promise<void> {
  return apiRequest(() => api.delete(`/projetos/${id}/`));
}
