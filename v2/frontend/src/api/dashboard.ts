/**
 * API Client - Dashboard Overview
 */

import { fetchAPI } from './config'

/**
 * KPI payload for /api/dashboard/overview/.
 */
export interface DashboardKpis {
  eventos_futuros: number
  eventos_aprovados: number
  total_formadores: number
  aprovacoes_pendentes: number
}

/**
 * Flux summary item.
 */
export interface DashboardFluxoItem {
  fluxo: string
  quantidade: number
}

/**
 * Gerencia summary item.
 */
export interface DashboardGerenciaItem {
  gerencia: string
  quantidade?: number
  porcentagem: number
}

/**
 * Coordenador ranking item.
 */
export interface DashboardCoordenadorItem {
  nome: string
  eventos: number
}

/**
 * Response for /api/dashboard/overview/.
 */
export interface DashboardOverviewResponse {
  kpis: DashboardKpis
  por_fluxo: DashboardFluxoItem[]
  por_gerencia: DashboardGerenciaItem[]
  top_coordenadores: DashboardCoordenadorItem[]
}

/**
 * Load dashboard overview data.
 */
export async function getDashboardOverview(): Promise<DashboardOverviewResponse> {
  return fetchAPI('/dashboard/overview/')
}
