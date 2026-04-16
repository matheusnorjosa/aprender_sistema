/**
 * API Client - Lookup (Autocomplete) e Validação
 *
 * Endpoints para autocomplete de municípios, projetos, tipos de evento, usuários
 * e validação de solicitações.
 */

import { fetchAPI, buildUrl, type QueryParams } from './config';
import type { ID } from '../types';

/**
 * Generic lookup result item
 */
export interface LookupItem {
  id: ID;
  label: string;
  kind: string;
  [key: string]: unknown;
}

/**
 * User lookup result (SEC-ENUM-01: email removed)
 */
export type UserLookupItem = LookupItem;

/**
 * Validation payload for solicitacao
 */
export interface ValidateSolicPayload {
  municipio?: string | { id: ID };
  projeto?: string | { id: ID };
  tipo_evento?: string | { id: ID };
  date?: string;
  start?: string;
  end?: string;
  participants?: {
    coordenador?: ID;
    formadores?: ID[];
    coord_acompanha?: ID[];
  };
}

/**
 * Validation result
 */
export interface ValidateSolicResult {
  ok: boolean;
  errors: Array<{ field: string; message: string }>;
  canonical: Record<string, unknown>;
}

/**
 * Filtros opcionais para lookup de municípios.
 */
export type LookupMunicipiosParams = QueryParams & {
  q?: string;
  com_compra?: boolean;
  projeto_id?: ID;
};

/**
 * Filtros opcionais para lookup de projetos.
 */
export type LookupProjetosParams = QueryParams & {
  q?: string;
  com_compra?: boolean;
  municipio_id?: ID;
};

/**
 * Buscar municípios (autocomplete)
 *
 * @param q - Query string
 */
export async function lookupMunicipios(q: string = ''): Promise<LookupItem[]> {
  const url = buildUrl('/lookup/municipios/', { q });
  return await fetchAPI(url);
}

/**
 * Buscar municípios (autocomplete) com filtros de elegibilidade.
 *
 * @param params - Filtros do lookup
 */
export async function lookupMunicipiosWithFilters(params: LookupMunicipiosParams = {}): Promise<LookupItem[]> {
  const url = buildUrl('/lookup/municipios/', params);
  return await fetchAPI(url);
}

/**
 * Buscar projetos (autocomplete)
 *
 * @param q - Query string
 */
export async function lookupProjetos(q: string = ''): Promise<LookupItem[]> {
  const url = buildUrl('/lookup/projetos/', { q });
  return await fetchAPI(url);
}

/**
 * Buscar projetos (autocomplete) com filtros de elegibilidade.
 *
 * @param params - Filtros do lookup
 */
export async function lookupProjetosWithFilters(params: LookupProjetosParams = {}): Promise<LookupItem[]> {
  const url = buildUrl('/lookup/projetos/', params);
  return await fetchAPI(url);
}

/**
 * Buscar tipos de evento (autocomplete)
 *
 * @param q - Query string
 */
export async function lookupTiposEvento(q: string = ''): Promise<LookupItem[]> {
  const url = buildUrl('/lookup/tipos-evento/', { q });
  return await fetchAPI(url);
}

/**
 * Buscar usuários (autocomplete)
 *
 * @param q - Query string
 * @param role - Filtro por role/grupo (opcional)
 */
export async function lookupUsuarios(q: string = '', role: string = ''): Promise<UserLookupItem[]> {
  const url = buildUrl('/lookup/usuarios/', { q, role });
  return await fetchAPI(url);
}

/**
 * Validar dados de solicitação antes do submit
 */
export async function validateSolic(payload: ValidateSolicPayload): Promise<ValidateSolicResult> {
  return await fetchAPI('/solicitacoes/validate/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
