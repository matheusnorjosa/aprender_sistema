/**
 * User-related TypeScript types for AS v2 Frontend
 *
 * Maps to backend serializers:
 * - UserSlimSerializer
 * - UsuarioOptionSerializer
 * - UsuarioAdminSerializer
 */

import type { ID, ISODateTime } from './common';

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
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  date_joined: ISODateTime;
  last_login: ISODateTime | null;
  groups: string[];
  setores: string[];
  funcoes: string[];
  permissions: string[];
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
