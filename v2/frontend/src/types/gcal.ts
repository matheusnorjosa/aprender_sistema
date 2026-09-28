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
 * Por que o usuário ainda não pode publicar no Google Agenda (#1656).
 *
 * - `no_setor_scope`: não é global nem tem setor vigente (nada que publicar).
 * - `google_not_connected`: falta conectar a própria conta Google.
 * - `google_calendar_not_configured`: o calendário da organização não foi configurado.
 */
export type PublishBlockReason = 'no_setor_scope' | 'google_not_connected' | 'google_calendar_not_configured';

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
  /** `true` quando o usuário já pode publicar (#1656). Ausente em payloads antigos. */
  publish_ready: boolean;
  publish_block_reason: PublishBlockReason | null;
  /**
   * `true` quando o SISTEMA removeu a conexão porque o Google revogou o acesso
   * (`invalid_grant`) e a pessoa não reconectou (#2039). Ausente em payloads antigos.
   */
  reconnect_required?: boolean;
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
  publishReady: boolean;
  publishBlockReason: PublishBlockReason | null;
  /** O sistema desconectou a conta (Google revogou o acesso); pedir para conectar de novo. */
  reconnectRequired: boolean;
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
