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
  cpf_masked?: string;
  telefone?: string;
  cargo?: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  groups: string[];
  group_ids_display?: ID[];
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
  telefone?: string;
  cargo?: string;
  is_active?: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  group_ids?: ID[];
}

/**
 * Group assignment payload
 */
export interface AssignGroupsPayload {
  group_ids: ID[];
}

/**
 * Group member sync payload
 */
export interface SyncGroupMembersPayload {
  user_ids: ID[];
}

/**
 * Group member sync response
 */
export interface SyncGroupMembersResponse {
  group_id: ID;
  members_count: number;
  member_ids: ID[];
  added: number;
  removed: number;
}

/**
 * Group create/update payload
 */
export interface GroupPayload {
  name: string;
  group_type_input?: 'setor' | 'funcao' | null;
  permissao_funcional_ids?: ID[];
}

/**
 * Functional permission representation
 */
export interface PermissaoFuncional {
  id: ID;
  codename: string;
  label: string;
  description: string;
  category: string;
  is_system: boolean;
  groups?: Array<{ id: ID; name: string }>;
}

/**
 * RBAC meta payload
 */
export interface RBACMetaPayload {
  setor_groups: string[];
  funcao_groups: string[];
  categories: string[];
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
 * Municipio autocomplete item used by Admin DAT assisted form
 */
export interface MunicipioAutocompleteItem {
  nome: string;
  uf: string;
  ibge_code: string | null;
  source: 'referencia' | 'cadastro';
  confidence: 'high' | 'low';
}

/**
 * Municipio autocomplete query params
 */
export interface MunicipioAutocompleteParams {
  q: string;
  uf?: string;
  limit?: number;
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
  page_size?: number;
}

/**
 * Axios error with response
 */
interface AxiosErrorWithResponse extends AxiosError {
  response?: AxiosResponse<{
    detail?: string;
    errors?: Record<string, string[] | string>;
  }>;
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
      const backendErrors = axiosError.response?.data?.errors;
      const firstBackendError = backendErrors
        ? Object.values(backendErrors).flatMap((value) => (Array.isArray(value) ? value : [value]))[0]
        : null;
      message = String(
        firstBackendError
        || axiosError.response?.data?.detail
        || axiosError.message
        || `Erro HTTP ${axiosError.response?.status}`
      );
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
export async function updateGroup(
  id: ID,
  data: GroupPayload,
  options: { confirmReserved?: boolean } = {}
): Promise<Group> {
  const params = options.confirmReserved ? { confirm_reserved: true } : undefined;
  return apiRequest(() => api.patch(`/grupos/${id}/`, data, { params }));
}

/**
 * Delete group
 * @param id - Group ID
 */
export async function deleteGroup(id: ID, options: { confirmReserved?: boolean } = {}): Promise<void> {
  const params = options.confirmReserved ? { confirm_reserved: true } : undefined;
  return apiRequest(() => api.delete(`/grupos/${id}/`, { params }));
}

/**
 * Sync group members in one request
 * @param groupId - Group ID
 * @param data - {user_ids: [...]}
 */
export async function syncGroupMembers(
  groupId: ID,
  data: SyncGroupMembersPayload
): Promise<SyncGroupMembersResponse> {
  return apiRequest(() => api.post(`/grupos/${groupId}/sync-members/`, data));
}

/**
 * List functional permissions
 */
export async function listPermissoesFuncionais(
  params: { category?: string; search?: string; ordering?: string; page_size?: number } = {}
): Promise<PaginatedResponse<PermissaoFuncional>> {
  return apiRequest(() => api.get('/permissoes-funcionais/', { params }));
}

/**
 * RBAC metadata for admin UI
 */
export async function getRBACMeta(): Promise<RBACMetaPayload> {
  return apiRequest(() => api.get('/rbac/meta/'));
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

/**
 * Assisted municipio lookup for Admin DAT forms (UF + name + IBGE hints)
 * @param params - q (required), optional uf and limit
 */
export async function autocompleteMunicipiosAdmin(
  params: MunicipioAutocompleteParams
): Promise<MunicipioAutocompleteItem[]> {
  const response = await apiRequest<{ results: MunicipioAutocompleteItem[] }>(() =>
    api.get('/municipios/autocomplete/', { params })
  );
  return response.results || [];
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
