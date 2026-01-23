/**
 * API Client - Google Calendar Dashboard
 *
 * Endpoints para painel de publicação GCal.
 */

import { fetchAPI, buildUrl, type QueryParams } from './config';
import type { ID, PaginatedResponse, GCalDashboardEvent } from '../types';

/**
 * GCal status summary counts
 */
export interface GCalStatusCounts {
  NONE: number;
  PENDING: number;
  PUBLISHED: number;
  ERROR: number;
}

/**
 * GCal status summary response
 */
export interface GCalStatusSummary {
  counts: GCalStatusCounts;
  total: number;
}

/**
 * GCal filters for dashboard
 */
export interface GCalFilters {
  date_from?: string;
  date_to?: string;
  sector?: string;
  gcal_status?: string;
  q?: string;
  status?: string;
}

/**
 * Batch publish request
 */
export interface BatchPublishRequest {
  solicitacao_ids: ID[];
  dry_run?: boolean;
  apply_blocked?: boolean;
}

/**
 * Batch operation response
 */
export interface BatchOperationResponse {
  queued: number;
  skipped: number;
  errors: Array<{ id: ID; error: string }>;
  task_ids?: string[];
}

/**
 * Batch IDs request
 */
export interface BatchIdsRequest {
  solicitacao_ids: ID[];
}

/**
 * Busca resumo de status do GCal (contadores).
 *
 * @param filters - Filtros opcionais (date_from, date_to, sector, q, status)
 */
export async function getStatusSummary(filters: GCalFilters = {}): Promise<GCalStatusSummary> {
  const url = buildUrl('/gcal/status-summary/', filters as QueryParams);
  return await fetchAPI(url);
}

/**
 * Lista solicitações aprovadas com status GCal.
 *
 * @param filters - Filtros (date_from, date_to, sector, gcal_status, q)
 */
export async function listApprovedWithGCalStatus(filters: GCalFilters = {}): Promise<PaginatedResponse<GCalDashboardEvent>> {
  const url = buildUrl('/gcal/approved/', filters as QueryParams);
  return await fetchAPI(url);
}

/**
 * Publica múltiplas solicitações em lote no Google Calendar.
 *
 * @param body - { solicitacao_ids: [...], dry_run: bool, apply_blocked: bool }
 */
export async function publishBatch(body: BatchPublishRequest): Promise<BatchOperationResponse> {
  return await fetchAPI('/gcal/publish-batch/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Remove múltiplas solicitações do Google Calendar (unpublish).
 *
 * @param body - { solicitacao_ids: [...] }
 */
export async function unpublishBatch(body: BatchIdsRequest): Promise<BatchOperationResponse> {
  return await fetchAPI('/gcal/unpublish-batch/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Sincroniza solicitações bloqueadas (marca como PENDING no GCal).
 *
 * @param body - { solicitacao_ids: [...] }
 */
export async function syncBlocked(body: BatchIdsRequest): Promise<BatchOperationResponse> {
  return await fetchAPI('/gcal/sync-blocked/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
