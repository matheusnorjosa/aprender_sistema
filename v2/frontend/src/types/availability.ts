/**
 * Availability-related TypeScript types for AS v2 Frontend
 *
 * Business rules: RD-01 to RD-08 (Availability Rules)
 */

import type { ID, ISODateTime } from './common';

/**
 * Availability block type
 * T = Total block (full day unavailable)
 * P = Partial block (time range unavailable)
 */
export type BlockType = 'T' | 'P';

/**
 * Availability block status
 */
export type BlockStatus = 'pendente' | 'aprovado' | 'reprovado';

/**
 * Availability block representation
 */
export interface AvailabilityBlock {
  id: ID;
  usuario: ID;
  usuario_username?: string;
  usuario_nome?: string;
  tipo: BlockType;
  inicio: ISODateTime;
  fim: ISODateTime;
  motivo: string | null;
  status: BlockStatus;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

/**
 * Availability block create payload
 */
export interface AvailabilityBlockPayload {
  tipo: BlockType;
  inicio: string;
  fim: string;
  motivo?: string;
}

/**
 * Availability check request
 */
export interface AvailabilityCheckRequest {
  usuario_id: ID;
  inicio: string;
  fim: string;
  municipio_id?: ID;
}

/**
 * Conflict detail in availability check response
 */
export interface ConflictDetail {
  code: 'X' | 'T' | 'P' | 'D' | 'M';
  title: string;
  detail: string;
  ref_id?: ID | null;
}

/**
 * Availability check response
 */
export interface AvailabilityCheckResponse {
  ok: boolean;
  conflicts: ConflictDetail[];
}

/**
 * Availability check-many request (#1452) — checa vários usuários de uma vez.
 */
export interface AvailabilityCheckManyRequest {
  usuarios_ids: ID[];
  inicio: string;
  fim: string;
  municipio_id?: ID;
}

/**
 * Resultado por usuário no check-many.
 */
export interface AvailabilityCheckManyResult {
  usuario_id: ID;
  ok: boolean;
  conflicts: ConflictDetail[];
}

/**
 * Availability check-many response.
 */
export interface AvailabilityCheckManyResponse {
  ok: boolean;
  results: AvailabilityCheckManyResult[];
}

/**
 * Participante bloqueado no payload de erro 400 `availability_conflict` do backend
 * (`solicitacao_availability.py:raise_if_blocked`).
 */
export interface BlockedParticipant {
  usuario_id: ID;
  usuario_nome: string;
  conflicts: ConflictDetail[];
}

/**
 * Shape do erro 400 `availability_conflict` retornado no submit (#1452).
 */
export interface AvailabilityConflictErrorPayload {
  detail: string;
  code: 'availability_conflict';
  errors: {
    conflicts: ConflictDetail[];
    blocked_participants: BlockedParticipant[];
    skipped_guests: unknown[];
  };
}

/**
 * Monthly availability grid response
 */
export type AvailabilityCode = 'E' | '2' | 'P' | 'T' | 'X' | 'D' | 'D1' | '';

export interface MonthlyGridPerson {
  id: ID;
  name: string;
  email?: string;
  ch_month?: number;
  ch_year?: number;
  position_month?: number;
}

export interface MonthlyGridResponse {
  days: number[];
  legend: Record<string, string>;
  people: MonthlyGridPerson[];
  cells: AvailabilityCode[][];
  details_index: Record<string, unknown>;
}
