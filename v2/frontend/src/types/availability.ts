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
