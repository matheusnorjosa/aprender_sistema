/**
 * API Client - Feedback de uso (botão "Dar feedback", 11/11/2026)
 *
 * POST `/api/feedback/`: qualquer pessoa logada. Lista e CSV: o superusuário e o DAT
 * (policy `manage_admin_registries`). Espelha `FeedbackSerializer` em
 * `apps/core/serializers/feedback.py`.
 */

import { buildUrl, fetchAPI, fetchBlob, type QueryParams } from './config';
import type { ID, PaginatedResponse } from '../types';

export type TipoFeedback = 'ELOGIO' | 'PROBLEMA' | 'SUGESTAO' | 'DUVIDA';

/** Rótulo de cada tipo, na ordem em que aparece na tela. */
export const TIPOS_FEEDBACK: ReadonlyArray<{ value: TipoFeedback; label: string }> = [
  { value: 'ELOGIO', label: 'Elogio' },
  { value: 'PROBLEMA', label: 'Problema' },
  { value: 'SUGESTAO', label: 'Sugestão' },
  { value: 'DUVIDA', label: 'Dúvida' },
];

export const COMENTARIO_MAX = 2000;

export interface FeedbackPayload {
  nota: number;
  tipo: TipoFeedback;
  comentario: string;
  /** A rota da tela (`location.pathname`). */
  pagina: string;
}

export interface FeedbackRecord extends FeedbackPayload {
  id: ID;
  /** Nome de quem enviou (nunca CPF ou login); "Usuário removido" se a conta saiu. */
  pessoa: string;
  created_at: string;
}

export interface FeedbackFiltros {
  tipo?: TipoFeedback | undefined;
  nota?: number | undefined;
  /** Dia inicial (AAAA-MM-DD, inclusivo). */
  desde?: string | undefined;
  /** Dia final (AAAA-MM-DD, inclusivo). */
  ate?: string | undefined;
  page?: number;
  page_size?: number;
}

export async function enviarFeedback(payload: FeedbackPayload): Promise<FeedbackRecord> {
  return fetchAPI<FeedbackRecord>('/feedback/', { method: 'POST', body: JSON.stringify(payload) });
}

export async function listFeedbacks(filtros: FeedbackFiltros = {}): Promise<PaginatedResponse<FeedbackRecord>> {
  return fetchAPI(buildUrl('/feedback/', filtros as QueryParams));
}

export async function exportarFeedbacks(filtros: FeedbackFiltros = {}): Promise<Blob> {
  const { page: _page, page_size: _pageSize, ...semPagina } = filtros;
  return fetchBlob(buildUrl('/feedback/exportar/', semPagina));
}
