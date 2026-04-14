/**
 * API Client for Admin DAT endpoints
 *
 * GAP-001/002 resolved: Endpoints reactivated/created in Phase 1 Iteration 2
 */

import { fetchAPI, fetchWithErrorMapping, buildUrl, type QueryParams } from './config';
import { syncChannel } from '../services/syncChannel';
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

// Common error mapping for admin endpoints
const ADMIN_ERROR_MAP: Record<number, string> = {
  403: 'Você não tem permissão para realizar esta ação.',
  404: 'Recurso não encontrado.',
};

// ========== USUARIOS ==========

export async function listUsers(params: ListParams = {}): Promise<PaginatedResponse<AdminUser>> {
  return fetchWithErrorMapping(buildUrl('/usuarios-admin/', params as QueryParams), {}, ADMIN_ERROR_MAP);
}

export async function getUser(id: ID): Promise<AdminUser> {
  return fetchWithErrorMapping(`/usuarios-admin/${id}/`, {}, ADMIN_ERROR_MAP);
}

export async function createUser(data: UserPayload): Promise<AdminUser> {
  const result = await fetchWithErrorMapping<AdminUser>(
    '/usuarios-admin/',
    { method: 'POST', body: JSON.stringify(data) },
    ADMIN_ERROR_MAP,
  );
  syncChannel.publish('usuarios', { action: 'created' });
  return result;
}

export async function updateUser(id: ID, data: UserPayload): Promise<AdminUser> {
  const result = await fetchWithErrorMapping<AdminUser>(
    `/usuarios-admin/${id}/`,
    { method: 'PATCH', body: JSON.stringify(data) },
    ADMIN_ERROR_MAP,
  );
  syncChannel.publish('usuarios', { action: 'updated' });
  return result;
}

export async function deleteUser(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/usuarios-admin/${id}/`, { method: 'DELETE' }, ADMIN_ERROR_MAP);
  syncChannel.publish('usuarios', { action: 'deleted' });
}

export async function assignGroups(userId: ID, data: AssignGroupsPayload): Promise<AdminUser> {
  const result = await fetchWithErrorMapping<AdminUser>(
    `/usuarios-admin/${userId}/assign_groups/`,
    { method: 'POST', body: JSON.stringify(data) },
    ADMIN_ERROR_MAP,
  );
  syncChannel.publish('usuarios', { action: 'groups_assigned' });
  return result;
}

// ========== GRUPOS ==========

export async function listGroups(params: ListParams = {}): Promise<PaginatedResponse<Group>> {
  return fetchWithErrorMapping(buildUrl('/grupos/', params as QueryParams), {}, ADMIN_ERROR_MAP);
}

export async function getGroup(id: ID): Promise<Group> {
  return fetchWithErrorMapping(`/grupos/${id}/`, {}, ADMIN_ERROR_MAP);
}

export async function createGroup(data: GroupPayload): Promise<Group> {
  const result = await fetchWithErrorMapping<Group>(
    '/grupos/',
    { method: 'POST', body: JSON.stringify(data) },
    ADMIN_ERROR_MAP,
  );
  syncChannel.publish('grupos', { action: 'created' });
  return result;
}

export async function updateGroup(
  id: ID,
  data: GroupPayload,
  options: { confirmReserved?: boolean } = {},
): Promise<Group> {
  const url = options.confirmReserved ? `/grupos/${id}/?confirm_reserved=true` : `/grupos/${id}/`;
  const result = await fetchWithErrorMapping<Group>(
    url,
    { method: 'PATCH', body: JSON.stringify(data) },
    ADMIN_ERROR_MAP,
  );
  syncChannel.publish('grupos', { action: 'updated' });
  return result;
}

export async function deleteGroup(id: ID, options: { confirmReserved?: boolean } = {}): Promise<void> {
  const url = options.confirmReserved ? `/grupos/${id}/?confirm_reserved=true` : `/grupos/${id}/`;
  await fetchWithErrorMapping(url, { method: 'DELETE' }, ADMIN_ERROR_MAP);
  syncChannel.publish('grupos', { action: 'deleted' });
}

export async function syncGroupMembers(
  groupId: ID,
  data: SyncGroupMembersPayload,
): Promise<SyncGroupMembersResponse> {
  return fetchWithErrorMapping(`/grupos/${groupId}/sync-members/`, {
    method: 'POST',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function listPermissoesFuncionais(
  params: { category?: string; search?: string; ordering?: string; page_size?: number } = {},
): Promise<PaginatedResponse<PermissaoFuncional>> {
  return fetchAPI(buildUrl('/permissoes-funcionais/', params as QueryParams));
}

export async function getRBACMeta(): Promise<RBACMetaPayload> {
  return fetchAPI('/rbac/meta/');
}

// ========== MUNICIPIOS ==========

export async function listMunicipios(params: ListParams = {}): Promise<PaginatedResponse<Municipio>> {
  return fetchWithErrorMapping(buildUrl('/municipios/', params as QueryParams), {}, ADMIN_ERROR_MAP);
}

export async function getMunicipio(id: ID): Promise<Municipio> {
  return fetchWithErrorMapping(`/municipios/${id}/`, {}, ADMIN_ERROR_MAP);
}

export async function createMunicipio(data: MunicipioPayload): Promise<Municipio> {
  return fetchWithErrorMapping('/municipios/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function updateMunicipio(id: ID, data: MunicipioPayload): Promise<Municipio> {
  return fetchWithErrorMapping(`/municipios/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function deleteMunicipio(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/municipios/${id}/`, { method: 'DELETE' }, ADMIN_ERROR_MAP);
}

export async function autocompleteMunicipiosAdmin(
  params: MunicipioAutocompleteParams,
): Promise<MunicipioAutocompleteItem[]> {
  const response = await fetchAPI<{ results: MunicipioAutocompleteItem[] }>(
    buildUrl('/municipios/autocomplete/', params as unknown as QueryParams),
  );
  return response.results || [];
}

// ========== PROJETOS ==========

export async function listProjetos(params: ListParams = {}): Promise<PaginatedResponse<Projeto>> {
  return fetchWithErrorMapping(buildUrl('/projetos/', params as QueryParams), {}, ADMIN_ERROR_MAP);
}

export async function getProjeto(id: ID): Promise<Projeto> {
  return fetchWithErrorMapping(`/projetos/${id}/`, {}, ADMIN_ERROR_MAP);
}

export async function createProjeto(data: ProjetoPayload): Promise<Projeto> {
  return fetchWithErrorMapping('/projetos/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function updateProjeto(id: ID, data: ProjetoPayload): Promise<Projeto> {
  return fetchWithErrorMapping(`/projetos/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function deleteProjeto(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/projetos/${id}/`, { method: 'DELETE' }, ADMIN_ERROR_MAP);
}

// ========== GERENCIAS ==========

export interface GerenciaRecord {
  id: ID;
  nome: string;
  nome_setor: string;
  gerente: ID | null;
  gerente_nome: string;
  ativo: boolean;
  descricao: string;
  projetos_count: number;
  created_at: string;
  updated_at: string;
}

export interface GerenciaPayload {
  nome?: string;
  nome_setor?: string;
  gerente?: ID | null;
  ativo?: boolean;
  descricao?: string;
}

export async function listGerencias(params: ListParams = {}): Promise<PaginatedResponse<GerenciaRecord>> {
  return fetchWithErrorMapping(buildUrl('/gerencias/', params as QueryParams), {}, ADMIN_ERROR_MAP);
}

export async function createGerencia(data: GerenciaPayload): Promise<GerenciaRecord> {
  return fetchWithErrorMapping('/gerencias/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function updateGerencia(id: ID, data: GerenciaPayload): Promise<GerenciaRecord> {
  return fetchWithErrorMapping(`/gerencias/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function deleteGerencia(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/gerencias/${id}/`, { method: 'DELETE' }, ADMIN_ERROR_MAP);
}

// ========== PRODUTOS ==========

export interface ProdutoRecord {
  id: ID;
  codigo: string;
  nome: string;
  descricao: string;
  projeto: ID;
  projeto_nome: string;
  ativo: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProdutoPayload {
  codigo?: string;
  nome?: string;
  descricao?: string;
  projeto?: ID;
  ativo?: boolean;
}

export async function listProdutos(params: ListParams = {}): Promise<PaginatedResponse<ProdutoRecord>> {
  return fetchWithErrorMapping(buildUrl('/produtos/', params as QueryParams), {}, ADMIN_ERROR_MAP);
}

export async function createProduto(data: ProdutoPayload): Promise<ProdutoRecord> {
  return fetchWithErrorMapping('/produtos/', {
    method: 'POST',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function updateProduto(id: ID, data: ProdutoPayload): Promise<ProdutoRecord> {
  return fetchWithErrorMapping(`/produtos/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, ADMIN_ERROR_MAP);
}

export async function deleteProduto(id: ID): Promise<void> {
  await fetchWithErrorMapping(`/produtos/${id}/`, { method: 'DELETE' }, ADMIN_ERROR_MAP);
}
