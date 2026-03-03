/**
 * API Client - System Config
 *
 * Centralized wrappers for /api/config/ endpoints.
 */

import { fetchAPI } from './config'

/**
 * System configuration object.
 */
export interface SystemConfig {
  buffer_deslocamento_minutos?: number
  session_cookie_age?: number
  batch_size?: number
  [key: string]: unknown
}

/**
 * Validation errors returned by backend.
 */
export type ConfigValidationErrors = Record<string, string | string[]>

/**
 * Load current system config.
 */
export async function getSystemConfig(): Promise<SystemConfig> {
  return fetchAPI('/config/')
}

/**
 * Persist config changes.
 */
export async function updateSystemConfig(values: SystemConfig): Promise<SystemConfig> {
  return fetchAPI('/config/', {
    method: 'PUT',
    body: JSON.stringify(values),
  })
}
