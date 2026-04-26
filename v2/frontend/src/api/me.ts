/**
 * API Client - Me (usuário autenticado)
 *
 * Consome endpoints `/api/me/*` do backend AS v2.
 * Issue #1225 (Epic 2): página `/meus-eventos` (caso primário: Formador).
 */

import { fetchAPI, buildUrl, type QueryParams } from './config';
import type { ID, PaginatedResponse } from '../types';

/**
 * Evento na visão do participante (saída de `GET /api/me/events/`).
 *
 * Espelha `MeEventSerializer` em `apps/core/serializers/me.py`.
 * Campos derivados (`*_nome`, `formadores`) são read-only.
 */
export interface MeEvent {
  id: ID;
  inicio: string; // ISO 8601 datetime
  fim: string; // ISO 8601 datetime
  municipio_nome: string | null;
  projeto_nome: string | null;
  tipo_evento_nome: string | null;
  local: string;
  formadores: string[];
  is_online: boolean;
  meet_link: string | null;
  status: 'aprovado' | 'pendente' | 'reprovado';
}

/**
 * Filtros de paginação para `/api/me/events/`.
 */
export interface MeEventsFilters {
  page?: number;
  page_size?: number;
}

/**
 * Lista eventos em que o usuário autenticado é participante.
 *
 * Backend filtra `participations__usuario=request.user` + `status="aprovado"`,
 * ordenado por `-inicio` (mais recente primeiro).
 *
 * @param filters - Paginação opcional
 * @returns Página de eventos no formato DRF padrão
 */
export async function getMyEvents(
  filters: MeEventsFilters = {}
): Promise<PaginatedResponse<MeEvent>> {
  const url = buildUrl('/me/events/', filters as QueryParams);
  return await fetchAPI<PaginatedResponse<MeEvent>>(url);
}
