/**
 * API Client - Team Metrics Dashboard
 */

import { buildUrl, fetchAPI, type QueryParams } from './config'

/**
 * Productivity response.
 */
export interface TeamProductivityData {
  period: string
  events_created: number
  approval_rate: number
  avg_approval_time_hours: number
  gcal_error_rate: number
}

/**
 * Formador row.
 */
export interface TeamFormadorRecord {
  id: number
  nome: string
  eventos: number
  horas_trabalhadas: number
  municipios_atendidos: number
}

/**
 * Formadores response.
 */
export interface TeamFormadoresData {
  period: string
  formadores: TeamFormadorRecord[]
}

/**
 * Quality response.
 */
export interface TeamQualityData {
  period: string
  rejection_rate: number
  conflict_rate: number
  rework_rate: number
  avg_publish_time_minutes: number
}

/**
 * Load productivity metrics.
 */
export async function getTeamProductivity(days: number): Promise<TeamProductivityData> {
  const url = buildUrl('/metrics/team/productivity/', { days } as QueryParams)
  return fetchAPI(url)
}

/**
 * Load formadores metrics.
 */
export async function getTeamFormadores(days: number): Promise<TeamFormadoresData> {
  const url = buildUrl('/metrics/team/formadores/', { days } as QueryParams)
  return fetchAPI(url)
}

/**
 * Load quality metrics.
 */
export async function getTeamQuality(days: number): Promise<TeamQualityData> {
  const url = buildUrl('/metrics/team/quality/', { days } as QueryParams)
  return fetchAPI(url)
}
