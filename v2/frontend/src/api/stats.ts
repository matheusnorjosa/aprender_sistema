/**
 * Stats API - Estatísticas para HomePage
 *
 * GET /api/stats/home/ - Retorna métricas personalizadas por perfil do usuário
 */

import { fetchAPI } from './config';

/**
 * Home page statistics response
 */
export interface HomeStats {
  pending_approvals: number | null;
  upcoming_events: number;
  my_requests: number | null;
}

/**
 * Busca estatísticas da HomePage.
 *
 * Retorna métricas diferentes baseado no perfil do usuário:
 * - pending_approvals: Só para quem pode aprovar (null se não pode)
 * - upcoming_events: Formador=seus eventos, Coord=setor
 * - my_requests: Só para quem pode criar solicitações (null se não pode)
 */
export async function getHomeStats(): Promise<HomeStats> {
  return fetchAPI('/stats/home/');
}
