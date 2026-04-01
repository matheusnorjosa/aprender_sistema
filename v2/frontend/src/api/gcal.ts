/**
 * API Client - Google Calendar Dashboard
 *
 * Endpoints consumidos pelo frontend e implementados no backend.
 */

import { fetchAPI, buildUrl, type QueryParams } from './config';
import { API_BASE } from './config';
import { syncChannel } from '../services/syncChannel';
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
 * GCal dashboard window filter params.
 */
export interface GCalDashboardWindowFilters {
  start?: string;
  end?: string;
}

/**
 * GCal dashboard metrics response.
 */
export interface GCalDashboardMetricsResponse {
  counts: GCalStatusCounts;
  recent_errors: Array<{
    id: number;
    summary: string;
    gcal_last_error: string;
    updated_at: string | null;
  }>;
  window?: {
    start?: string | null;
    end?: string | null;
  };
}

/**
 * Event row in /api/gcal/dashboard/events/.
 */
export interface GCalDashboardEventRecord {
  id: number;
  summary: string;
  gcal_status: 'NONE' | 'PENDING' | 'PUBLISHED' | 'ERROR';
  gcal_last_sync_at: string | null;
  gcal_last_error: string | null;
}

/**
 * Params for dashboard events listing.
 */
export interface GCalDashboardEventsParams extends GCalDashboardWindowFilters {
  page?: number;
  page_size?: number;
  status?: string;
}

/**
 * Success rate response.
 */
export interface GCalSuccessRateResponse {
  published: number;
  error: number;
  pending: number;
  none: number;
  rate: number;
  window?: {
    start?: string | null;
    end?: string | null;
  };
}

/**
 * Top insights item.
 */
export interface GCalTopInsightItem {
  name: string;
  count: number;
  published: number;
  error: number;
  rate: number;
}

/**
 * Top insights response.
 */
export interface GCalTopInsightsResponse {
  items: GCalTopInsightItem[];
  window?: {
    start?: string | null;
    end?: string | null;
  };
  metric: 'municipios' | 'projetos' | string;
  limit: number;
}

/**
 * Params for top insights endpoint.
 */
export interface GCalTopInsightsParams extends GCalDashboardWindowFilters {
  metric: 'municipios' | 'projetos' | string;
  limit?: number;
}

/**
 * Timeline item for event detail.
 */
export interface GCalEventTimelineItem {
  action: string;
  usuario_nome: string;
  created_at: string;
  details?: Record<string, unknown>;
}

/**
 * Event detail response.
 */
export interface GCalDashboardEventDetail {
  id: number;
  municipio_nome: string | null;
  projeto_nome: string | null;
  tipo_evento_nome: string | null;
  inicio: string | null;
  fim: string | null;
  usuario_username: string | null;
  coordenador_username: string | null;
  fluxo: string;
  gcal_status: 'NONE' | 'PENDING' | 'PUBLISHED' | 'ERROR';
  external_event_id: string | null;
  gcal_last_sync_at: string | null;
  meet_link: string | null;
  gcal_payload_hash: string | null;
  gcal_last_error: string | null;
  updated_at: string | null;
  participations: Array<{
    email: string;
    role: string;
    ch_horas?: number;
    observacao?: string;
  }>;
  timeline: GCalEventTimelineItem[];
}

/**
 * Alerts summary response.
 */
export interface GCalAlertsSummaryResponse {
  errors: number;
  pending: number;
  published: number;
  none: number;
  window?: {
    start?: string | null;
    end?: string | null;
  };
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
  const result = await fetchAPI<BatchOperationResponse>('/gcal/dashboard/batch/reapply/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  syncChannel.publish('preagenda', { action: 'batch_reapplied' });
  return result;
}

/**
 * Força resync (reseta hash + marca pending + republica em lote).
 *
 * @param body - { ids: [...], dry_run?: bool, apply_blocked?: bool }
 */
export async function resyncBatch(body: BatchIdsRequest): Promise<BatchOperationResponse> {
  const result = await fetchAPI<BatchOperationResponse>('/gcal/dashboard/batch/resync/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  syncChannel.publish('preagenda', { action: 'batch_resynced' });
  return result;
}

/**
 * Loads dashboard metrics cards and recent errors.
 */
export async function getDashboardMetrics(
  params: GCalDashboardWindowFilters = {}
): Promise<GCalDashboardMetricsResponse> {
  const url = buildUrl('/gcal/dashboard/metrics/', params as QueryParams);
  return await fetchAPI(url);
}

/**
 * Loads dashboard events table.
 */
export async function listDashboardEvents(
  params: GCalDashboardEventsParams = {}
): Promise<PaginatedResponse<GCalDashboardEventRecord>> {
  const url = buildUrl('/gcal/dashboard/events/', params as QueryParams);
  return await fetchAPI(url);
}

/**
 * Loads success-rate insight card.
 */
export async function getDashboardSuccessRate(
  params: GCalDashboardWindowFilters = {}
): Promise<GCalSuccessRateResponse> {
  const url = buildUrl('/gcal/dashboard/insights/success-rate/', params as QueryParams);
  return await fetchAPI(url);
}

/**
 * Loads top insights table.
 */
export async function getDashboardTopInsights(
  params: GCalTopInsightsParams
): Promise<GCalTopInsightsResponse> {
  const queryParams: QueryParams = { ...params };
  const url = buildUrl('/gcal/dashboard/insights/top/', queryParams);
  return await fetchAPI(url);
}

/**
 * Loads full event detail drawer payload.
 */
export async function getDashboardEventDetail(eventId: number): Promise<GCalDashboardEventDetail> {
  return await fetchAPI(`/gcal/dashboard/events/${eventId}/detail/`);
}

/**
 * Loads alerts summary used for menu badge/toast.
 */
export async function getAlertsSummary(): Promise<GCalAlertsSummaryResponse> {
  return await fetchAPI('/gcal/dashboard/alerts/summary/');
}

/**
 * Builds export URL for dashboard events with active filters.
 */
export function buildDashboardEventsExportUrl(params: {
  export_format: 'csv' | 'json';
  start?: string;
  end?: string;
  status?: string;
}): string {
  const relativePath = buildUrl('/gcal/dashboard/events/export/', params as QueryParams);
  return `${API_BASE}${relativePath}`;
}
