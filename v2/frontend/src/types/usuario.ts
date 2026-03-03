/**
 * User-related TypeScript types for AS v2 Frontend
 *
 * Maps to backend serializers:
 * - UserSlimSerializer
 * - UsuarioOptionSerializer
 * - UsuarioAdminSerializer
 */

import type { ID } from './common';

/**
 * Slim user representation (UserSlimSerializer)
 * Used in nested serializers
 */
export interface UserSlim {
  id: ID;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
}

/**
 * User option for dropdowns (UsuarioOptionSerializer)
 */
export interface UsuarioOption {
  id: ID;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
}

/**
 * Full user data from /api/me/ endpoint
 */
export interface CurrentUser {
  id: ID;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  name: string;
  groups: string[];
  setores: string[];
  funcoes: string[];
  is_superuser: boolean;
  is_superintendencia: boolean;
  can_approve_super: boolean;
}

/**
 * Runtime guard for /api/me/ payload.
 * Keeps frontend authentication bootstrap aligned with backend contract.
 */
export function isCurrentUserPayload(value: unknown): value is CurrentUser {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const payload = value as Record<string, unknown>;
  const isStringArray = (field: unknown): field is string[] =>
    Array.isArray(field) && field.every((item) => typeof item === 'string');

  return (
    typeof payload.id === 'number'
    && typeof payload.username === 'string'
    && typeof payload.email === 'string'
    && typeof payload.first_name === 'string'
    && typeof payload.last_name === 'string'
    && typeof payload.name === 'string'
    && isStringArray(payload.groups)
    && isStringArray(payload.setores)
    && isStringArray(payload.funcoes)
    && typeof payload.is_superuser === 'boolean'
    && typeof payload.is_superintendencia === 'boolean'
    && typeof payload.can_approve_super === 'boolean'
  );
}

/**
 * Asserts that payload matches /api/me/ minimal contract.
 */
export function assertCurrentUserPayload(value: unknown): CurrentUser {
  if (!isCurrentUserPayload(value)) {
    throw new Error('Invalid /api/me payload shape');
  }

  return value;
}

/**
 * Auth check response
 */
export interface AuthCheckResponse {
  authenticated: boolean;
  user: CurrentUser | null;
}

/**
 * Login request payload
 */
export interface LoginRequest {
  username: string;
  password: string;
}

/**
 * Login response (success)
 */
export interface LoginResponse {
  detail: string;
  user: CurrentUser;
}

/**
 * Group representation
 */
export interface Group {
  id: ID;
  name: string;
}
