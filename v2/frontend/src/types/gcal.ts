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
 * Google integration status response
 */
export interface GoogleIntegrationStatus {
  connected: boolean;
  email: string | null;
  calendars: GoogleCalendar[];
  expires_at: ISODateTime | null;
  needs_refresh: boolean;
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
