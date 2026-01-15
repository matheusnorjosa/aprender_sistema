/**
 * Stats API - Estatísticas para HomePage
 *
 * GET /api/stats/home/ - Retorna métricas personalizadas por perfil do usuário
 */

import { fetchAPI } from './config';

/**
 * Busca estatísticas da HomePage.
 *
 * Retorna métricas diferentes baseado no perfil do usuário:
 * - pending_approvals: Só para quem pode aprovar (null se não pode)
 * - upcoming_events: Formador=seus eventos, Coord=setor
 * - my_requests: Só para quem pode criar solicitações (null se não pode)
 *
 * @returns {Promise<{pending_approvals: number|null, upcoming_events: number, my_requests: number|null}>}
 */
export async function getHomeStats() {
  return fetchAPI('/stats/home/');
}
