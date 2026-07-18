/**
 * Google Calendar integration TypeScript types for AS v2 Frontend
 *
 * RF05: Google Calendar integration
 * RF06: Google Meet links
 */

import type { ID, ISODateTime } from './common';

/**
 * Google OAuth connection status
 */
export type GoogleConnectionStatus = 'connected' | 'disconnected' | 'expired';

/**
 * Google integration status — payload RAW do backend (snake_case).
 *
 * SSOT do contrato: `apps/core/views_oauth.py` `google_oauth_status`
 * (ramos conectado e desconectado). O frontend NUNCA deve consumir este
 * shape diretamente — normalize via `normalizeGoogleStatus` antes de usar.
 */
export interface GoogleIntegrationStatusRaw {
  connected: boolean;
  google_email: string | null;
  token_expiry: ISODateTime | null;
  expires_in_days: number | null;
  is_expired: boolean;
  default_calendar_id: string | null;
}

/**
 * Google integration status — tipo de DOMÍNIO (camelCase), SSOT do frontend.
 *
 * Produzido por `normalizeGoogleStatus(raw)` a partir do payload snake_case.
 * Consumido pelo hook `useGoogleIntegration` e por `GoogleIntegrationCard`.
 */
export interface GoogleIntegrationStatus {
  connected: boolean;
  googleEmail: string | null;
  tokenExpiry: ISODateTime | null;
  expiresInDays: number | null;
  isExpired: boolean;
  defaultCalendarId: string | null;
}

/**
 * Google Calendar representation
 */
export interface GoogleCalendar {
  id: string;
  summary: string;
  primary: boolean;
  accessRole: 'owner' | 'writer' | 'reader';
}

/**
 * GCal dashboard metrics
 */
export interface GCalDashboardMetrics {
  total_events: number;
  published_events: number;
  pending_events: number;
  error_events: number;
  cancelled_events: number;
  sync_rate: number;
}

/**
 * GCal dashboard event row
 */
export interface GCalDashboardEvent {
  id: ID;
  municipio_nome: string;
  projeto_nome: string;
  tipo_evento_nome: string;
  inicio: ISODateTime;
  fim: ISODateTime;
  status: string;
  gcal_status: string;
  external_event_id: string | null;
  meet_link: string | null;
  gcal_last_sync_at: ISODateTime | null;
  gcal_last_error: string | null;
}

/**
 * GCal publish batch request
 */
export interface PublishBatchRequest {
  ids: ID[];
  dry_run?: boolean;
}

/**
 * GCal publish batch response
 */
export interface PublishBatchResponse {
  queued: number;
  skipped: number;
  errors: Array<{ id: ID; error: string }>;
  task_ids: string[];
}

/**
 * GCal OAuth URL response
 */
export interface OAuthUrlResponse {
  auth_url: string;
}

/**
 * GCal OAuth callback response
 */
export interface OAuthCallbackResponse {
  success: boolean;
  email?: string;
  error?: string;
}
