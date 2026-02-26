/**
 * API Client - Google Calendar Dashboard
 *
 * Endpoints consumidos pelo frontend e implementados no backend.
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
  errors: Array<{ id: ID; detail?: string; error?: string }>;
  skipped?: number;
  dry_run?: boolean;
  apply_blocked?: boolean;
  task_ids?: string[];
}

/**
 * Batch IDs request
 */
export interface BatchIdsRequest {
  ids: ID[];
  dry_run?: boolean;
  apply_blocked?: boolean;
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
  const url = buildUrl('/gcal/list/', filters as QueryParams);
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
 * Reaplica eventos já publicados sem resetar hash.
 *
 * @param body - { ids: [...], dry_run?: bool, apply_blocked?: bool }
 */
export async function reapplyBatch(body: BatchIdsRequest): Promise<BatchOperationResponse> {
  return await fetchAPI('/gcal/dashboard/batch/reapply/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Força resync (reseta hash + marca pending + republica em lote).
 *
 * @param body - { ids: [...], dry_run?: bool, apply_blocked?: bool }
 */
export async function resyncBatch(body: BatchIdsRequest): Promise<BatchOperationResponse> {
  return await fetchAPI('/gcal/dashboard/batch/resync/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
