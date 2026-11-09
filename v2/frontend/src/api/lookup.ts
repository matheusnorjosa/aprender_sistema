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
 * Filtros opcionais para lookup de municípios.
 */
export type LookupMunicipiosParams = QueryParams & {
  q?: string;
  com_compra?: boolean | undefined;
  projeto_id?: ID | undefined;
  /**
   * Com `projeto_id`: em vez de filtrar, traz também os municípios sem compra para o projeto, com compra
   * primeiro, e cada item leva `sem_compra` (o evento ali vai para aprovação; pedido do dono, 03/11/2026).
   */
  marcar_sem_compra?: boolean | undefined;
  /** Só esse município (a edição reconfere a marca do par ao trocar o projeto). */
  municipio_id?: ID | undefined;
  /** Com `projeto_id`: o outro projeto do combo (#2036). A marca e o filtro pedem compra para os dois. */
  projeto_2_id?: ID | undefined;
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
 * Filtros opcionais para lookup de projetos.
 */
export type LookupProjetosParams = QueryParams & {
  /** Esconde o projeto "em espera" (sem compra que o libere); o servidor isenta quem é isento. */
  com_compra?: boolean | undefined;
  /** Combo (#2036): só os projetos que podem ir com este (mesma gerência e mesmo fluxo), sem ele. */
  mesmo_grupo_de?: ID | undefined;
};

/**
 * Buscar projetos (autocomplete)
 *
 * @param q - Query string
 * @param params - Filtros do lookup (a assinatura de `q` não muda: o ComboBox chama só com `q`)
 */
export async function lookupProjetos(q: string = '', params: LookupProjetosParams = {}): Promise<LookupItem[]> {
  const url = buildUrl('/lookup/projetos/', { ...params, q });
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
 * @param role - Filtro por papel vigente (opcional; vários separados por vírgula)
 * @param projetoId - Projeto do evento (opcional): só pessoas da gerência dele (PR 9, P9-5)
 */
export async function lookupUsuarios(q: string = '', role: string = '', projetoId?: ID | undefined): Promise<UserLookupItem[]> {
  const url = buildUrl('/lookup/usuarios/', { q, role, projeto_id: projetoId });
  return await fetchAPI(url);
}
