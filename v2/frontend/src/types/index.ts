/**
 * AS v2 Frontend - Shared TypeScript Types
 *
 * Re-exports all types from domain-specific modules.
 * Import from '@/types' or 'src/types' in your components.
 *
 * Example:
 *   import type { Solicitacao, CurrentUser, MunicipioOption } from '@/types';
 */

// Common types
export type {
  PaginatedResponse,
  ApiError,
  LoadingStatus,
  ID,
  ISODateTime,
  ISODate,
  DecimalString,
} from './common';

// User types
export type {
  UserSlim,
  UsuarioOption,
  CurrentUser,
  AuthCheckResponse,
  LoginRequest,
  LoginResponse,
  Group,
} from './usuario';

// Solicitacao types
export type {
  SolicitacaoStatus,
  FluxoType,
  GCalStatus,
  TipoEventoCode,
  ParticipantRole,
  Participation,
  Solicitacao,
  SolicitacaoPayload,
  SolicitacaoFilters,
  AuditLogEntry,
  EventDetail,
  BatchOperationResult,
  PublishResult,
} from './solicitacao';

// Organization types
export type {
  UFCode,
  Municipio,
  MunicipioOption,
  ProjetoFluxo,
  Projeto,
  ProjetoOption,
  TipoEventoOption,
  Gerencia,
  Produto,
  ProdutoOption,
} from './organizacao';

// Availability types
export type {
  BlockType,
  BlockStatus,
  AvailabilityBlock,
  AvailabilityBlockPayload,
  AvailabilityCheckRequest,
  ConflictDetail,
  AvailabilityCheckResponse,
  MonthlyGridResponse,
} from './availability';

// Google Calendar types
export type {
  GoogleConnectionStatus,
  GoogleIntegrationStatus,
  GoogleCalendar,
  GCalDashboardMetrics,
  GCalDashboardEvent,
  PublishBatchRequest,
  PublishBatchResponse,
  OAuthUrlResponse,
  OAuthCallbackResponse,
} from './gcal';
