/**
 * Availability-related TypeScript types for AS v2 Frontend
 *
 * Business rules: RD-01 to RD-08 (Availability Rules)
 */

import type { ID, ISODateTime, ISODate } from './common';

/**
 * Availability block type
 * T = Total block (full day unavailable)
 * P = Partial block (time range unavailable)
 * D = Deslocamento (travel time buffer)
 * M = Maximum hours reached
 */
export type BlockType = 'T' | 'P' | 'D' | 'M';

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
  data: ISODate;
  hora_inicio: string | null;
  hora_fim: string | null;
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
  data: string;
  hora_inicio?: string;
  hora_fim?: string;
  motivo?: string;
}

/**
 * Availability check request
 */
export interface AvailabilityCheckRequest {
  formador_id: ID;
  data: string;
  hora_inicio: string;
  hora_fim: string;
  municipio_id?: ID;
}

/**
 * Conflict detail in availability check response
 */
export interface ConflictDetail {
  tipo: BlockType | 'CONFLITO';
  descricao: string;
  evento?: string;
  horario?: string;
}

/**
 * Availability check response
 */
export interface AvailabilityCheckResponse {
  disponivel: boolean;
  conflitos: ConflictDetail[];
  mensagem?: string;
}

/**
 * Monthly grid cell data
 */
export interface MonthlyGridCell {
  data: ISODate;
  bloqueios: AvailabilityBlock[];
  eventos: Array<{
    id: ID;
    titulo: string;
    inicio: string;
    fim: string;
    status: string;
  }>;
  horas_usadas: number;
  horas_limite: number;
}

/**
 * Monthly grid response
 */
export interface MonthlyGridResponse {
  formador: {
    id: ID;
    nome: string;
    username: string;
  };
  mes: string;
  ano: number;
  dias: MonthlyGridCell[];
}
