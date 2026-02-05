/**
 * TypeScript Type Definitions - Playwright E2E Tests
 *
 * Interfaces para entidades do Aprender Sistema v2.
 * Fase 2 - Plano DAT/GCal 2025-10-29
 */

/**
 * Usuario (Django Auth User customizado)
 */
export interface Usuario {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  cpf: string;
  telefone?: string;
  cargo?: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  groups: string[] | number[];
  date_joined: string;
  last_login?: string;
}

/**
 * Municipio
 */
export interface Municipio {
  id: number;
  nome: string;
  uf: string;
  ibge_code: string;
  ativo: boolean;
}

/**
 * Projeto
 */
export interface Projeto {
  id: number;
  nome: string;
  codigo: string;
  fluxo: 'SUPER' | 'NAO_SUPER';
  ativo: boolean;
  descricao?: string;
}

/**
 * Solicitacao (principal entidade do teste E2E)
 */
export interface Solicitacao {
  id: number;
  titulo: string;
  descricao?: string;
  inicio: string; // ISO datetime
  fim: string; // ISO datetime
  status: 'pendente' | 'aprovado' | 'reprovado' | 'publicado';
  is_online: boolean;
  projeto: number; // FK
  municipio: number; // FK
  solicitante: number; // FK
  formadores: number[]; // M2M

  // Campos Google Calendar
  external_event_id?: string | null;
  gcal_status?: string | null;
  gcal_event_id?: string | null;
  gcal_payload_hash?: string | null;
  meet_link?: string | null;

  // Timestamps
  created_at: string;
  updated_at: string;
}

/**
 * Aprovacao
 */
export interface Aprovacao {
  id: number;
  solicitacao: number; // FK
  aprovador: number; // FK
  decisao: 'aprovado' | 'reprovado';
  justificativa?: string;
  timestamp: string;
}

/**
 * AuditLog
 */
export interface AuditLog {
  id: number;
  usuario: number; // FK
  action: string; // CREATE, APPROVE, PUBLISH, etc.
  model_name: string; // Solicitacao, Usuario, etc.
  object_id: number;
  details: Record<string, any>;
  timestamp: string;
  ip_address?: string;
  user_agent?: string;
}

/**
 * DRF Paginated Response
 */
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/**
 * Google Calendar Event (simplified)
 */
export interface GCalEvent {
  id?: string;
  summary: string;
  description?: string;
  start: {
    dateTime: string;
    timeZone: string;
  };
  end: {
    dateTime: string;
    timeZone: string;
  };
  attendees?: Array<{
    email: string;
    displayName?: string;
  }>;
  conferenceData?: {
    conferenceSolution: {
      key: {
        type: string;
      };
    };
    conferenceId: string;
    entryPoints: Array<{
      entryPointType: string;
      uri: string;
    }>;
  };
}

/**
 * API Response types
 */
export interface APIResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

/**
 * Test Context (compartilhado entre test cases)
 */
export interface TestContext {
  solicitacaoId?: number;
  solicitacao?: Solicitacao;
  usuarios?: {
    coordenador?: Usuario;
    super?: Usuario;
    controle?: Usuario;
    formador?: Usuario;
  };
}
