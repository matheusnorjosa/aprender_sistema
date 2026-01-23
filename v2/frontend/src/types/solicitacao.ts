/**
 * Solicitacao-related TypeScript types for AS v2 Frontend
 *
 * Maps to backend serializers:
 * - SolicitacaoSerializer
 * - ParticipationNestedSerializer
 * - EventDetailSerializer
 *
 * Business rules: PA-01 to PA-07 (Approval Policy)
 */

import type { ID, ISODateTime } from './common';
import type { UserSlim } from './usuario';

/**
 * Solicitacao status (Portuguese)
 */
export type SolicitacaoStatus = 'pendente' | 'aprovado' | 'reprovado';

/**
 * Project workflow type
 */
export type FluxoType = 'SUPER' | 'NAO_SUPER';

/**
 * Google Calendar sync status
 */
export type GCalStatus = 'NOT_SYNCED' | 'PENDING' | 'PUBLISHED' | 'ERROR' | 'CANCELLED';

/**
 * Event type (from TipoEvento)
 */
export type TipoEventoCode = 'FORMACAO' | 'ACOMPANHAMENTO' | 'REUNIAO' | 'OUTRO';

/**
 * Participant role in an event
 */
export type ParticipantRole = 'FORMADOR' | 'COORDENADOR' | 'PARTICIPANTE' | 'CONVIDADO';

/**
 * Participation nested representation
 */
export interface Participation {
  usuario: UserSlim | null;
  guest_email: string | null;
  email: string | null;
  role: ParticipantRole;
  ch_horas: number | null;
  observacao: string | null;
}

/**
 * Solicitacao (event request) - full representation
 */
export interface Solicitacao {
  id: ID;
  usuario: ID;
  usuario_username: string | null;
  municipio: ID | null;
  municipio_nome: string | null;
  projeto: ID | null;
  projeto_nome: string | null;
  tipo_evento: ID | null;
  tipo_evento_nome: string | null;
  tipo: string | null;
  encontro: string | null;
  segmento: string | null;
  coordenador_acompanha: boolean;
  coordenador: ID | null;
  coordenador_username: string | null;
  coordenador_nome: string | null;
  inicio: ISODateTime;
  fim: ISODateTime;
  status: SolicitacaoStatus;
  observacoes: string | null;
  local: string | null;
  is_online: boolean;
  external_event_id: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  participations: Participation[];
  fluxo: FluxoType;
  gcal_status: GCalStatus;
  gcal_last_sync_at: ISODateTime | null;
  gcal_last_error: string | null;
  meet_link: string | null;
}

/**
 * Solicitacao create/update payload
 */
export interface SolicitacaoPayload {
  municipio?: ID;
  projeto?: ID;
  tipo_evento?: ID;
  tipo?: string;
  encontro?: string;
  segmento?: string;
  coordenador_acompanha?: boolean;
  coordenador?: ID;
  inicio?: string;
  fim?: string;
  observacoes?: string;
  local?: string;
  is_online?: boolean;
}

/**
 * Solicitacao list filters
 */
export interface SolicitacaoFilters {
  status?: SolicitacaoStatus | 'pending' | 'approved' | 'rejected';
  mine?: string;
  flow?: FluxoType;
  q?: string;
  sector?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  search?: string;
}

/**
 * Audit log entry for timeline
 */
export interface AuditLogEntry {
  id: ID;
  action: string;
  usuario_nome: string;
  details: Record<string, unknown>;
  created_at: ISODateTime;
}

/**
 * Event detail with timeline (for GCal dashboard)
 */
export interface EventDetail extends Omit<Solicitacao, 'usuario' | 'municipio' | 'projeto' | 'tipo_evento' | 'coordenador' | 'tipo' | 'encontro' | 'segmento' | 'coordenador_acompanha' | 'observacoes' | 'local' | 'is_online' | 'status' | 'created_at'> {
  timeline: AuditLogEntry[];
}

/**
 * Batch operation result
 */
export interface BatchOperationResult {
  approved?: number;
  rejected?: number;
  errors: Array<{ id: ID; error: string }>;
}

/**
 * GCal publish result
 */
export interface PublishResult {
  detail: string;
  task_id?: string;
  solicitacao_id: ID;
}
