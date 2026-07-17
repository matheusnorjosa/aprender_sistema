/**
 * API Client - Availability Blocks
 *
 * Consome endpoints do backend AS v2 para gerenciar bloqueios de disponibilidade.
 */

import { fetchAPI, buildUrl, type QueryParams } from './config';
import { syncChannel } from '../services/syncChannel';
import type {
  ID,
  CurrentUser,
  AvailabilityBlock,
  AvailabilityBlockPayload,
  AvailabilityCheckResponse,
  AvailabilityCheckManyRequest,
  AvailabilityCheckManyResponse,
  MonthlyGridResponse,
  Gerencia,
} from '../types';
import { assertCurrentUserPayload } from '../types';

/**
 * Block filter parameters
 */
export interface BlockFilters {
  owner?: string;
  [key: string]: string | undefined;
}

/**
 * Availability check parameters
 */
export interface AvailabilityCheckParams {
  usuario_id: ID;
  inicio: string;
  fim: string;
  municipio_id?: ID;
}

/**
 * Monthly availability parameters
 */
export interface MonthlyAvailabilityParams {
  year: number;
  month: number;
  role?: 'FORMADOR' | 'COORDENADOR';
  sector?: string;
  q?: string;
  gerencia_id?: number | null;
}

/**
 * Feature flags response
 */
export interface FeatureFlags {
  apply_blocked: boolean;
  GCAL_CLIENT: boolean;
  PREVIEW_ONLY: boolean;
  [key: string]: unknown;
}

/**
 * Busca informações do usuário atual.
 */
export async function getMe(): Promise<CurrentUser> {
  const payload = await fetchAPI<unknown>('/me/');
  return assertCurrentUserPayload(payload);
}

/**
 * Lista bloqueios de disponibilidade.
 *
 * @param params - Parâmetros de filtro
 */
export async function getBlocks(params: BlockFilters = { owner: 'me' }): Promise<AvailabilityBlock[]> {
  const url = buildUrl('/availability-blocks/', params);
  const data = await fetchAPI<{ results?: AvailabilityBlock[] } | AvailabilityBlock[]>(url);

  // DRF retorna { results: [...], count: N } quando paginado
  return (data as { results: AvailabilityBlock[] }).results || (data as AvailabilityBlock[]);
}

/**
 * Cria novo bloqueio de disponibilidade.
 *
 * @param data - Dados do bloqueio
 */
export async function createBlock(data: AvailabilityBlockPayload): Promise<AvailabilityBlock> {
  const result = await fetchAPI<AvailabilityBlock>('/availability-blocks/', {
    method: 'POST',
    body: JSON.stringify(data),
  });
  syncChannel.publish('availability', { action: 'block_created' });
  return result;
}

/**
 * Remove bloqueio de disponibilidade.
 *
 * @param id - ID do bloqueio
 */
export async function deleteBlock(id: ID): Promise<void> {
  await fetchAPI(`/availability-blocks/${id}/`, {
    method: 'DELETE',
  });
  syncChannel.publish('availability', { action: 'block_deleted' });
}

/**
 * Checa disponibilidade de um usuário (consultivo).
 *
 * @param params - Parâmetros da checagem
 */
export async function checkAvailability(params: AvailabilityCheckParams): Promise<AvailabilityCheckResponse> {
  const url = buildUrl('/availability/check/', params as unknown as QueryParams);
  return await fetchAPI(url);
}

/**
 * Checa disponibilidade de vários usuários de uma vez (#1452).
 *
 * Usado pelo wizard de nova solicitação para avisar cedo quando um participante
 * (formador/coordenador) já está alocado. Uma chamada em vez de N, para não estourar
 * o throttle `availability_check`. Aceita `signal` para cancelar respostas obsoletas.
 *
 * @param params - usuarios_ids + intervalo + município
 * @param options - opções do fetch (ex.: `signal` de um AbortController)
 */
export async function checkAvailabilityMany(
  params: AvailabilityCheckManyRequest,
  options: { signal?: AbortSignal } = {}
): Promise<AvailabilityCheckManyResponse> {
  return await fetchAPI('/availability/check-many/', {
    ...options,
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * Busca grade mensal de disponibilidade.
 *
 * @param params - Parâmetros da consulta
 */
export async function getMonthlyAvailability(params: MonthlyAvailabilityParams): Promise<MonthlyGridResponse> {
  const url = buildUrl('/availability/monthly/', params as unknown as QueryParams);
  return await fetchAPI(url);
}

/**
 * Busca grade mensal de disponibilidade (versão genérica).
 *
 * @param params - Parâmetros da consulta
 */
export async function getMonthly(params: QueryParams): Promise<MonthlyGridResponse> {
  const url = buildUrl('/availability/monthly/', params);
  return await fetchAPI(url);
}

/**
 * Busca feature flags do sistema.
 */
export async function getFeatures(): Promise<FeatureFlags> {
  return await fetchAPI('/features/');
}

/**
 * Busca lista de gerências disponíveis.
 */
export async function getGerencias(): Promise<Gerencia[]> {
  const data = await fetchAPI<{ results?: Gerencia[] } | Gerencia[]>('/gerencias/');
  // DRF retorna { results: [...], count: N } quando paginado
  return (data as { results: Gerencia[] }).results || (data as Gerencia[]);
}
