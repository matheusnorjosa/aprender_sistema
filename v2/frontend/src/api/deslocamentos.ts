/**
 * API Client - Deslocamentos
 *
 * Consome `/api/deslocamentos/` (CRUD) e `/api/options/formadores-do-setor/`.
 *
 * Issue #1453: a página chamava `fetch` cru, sem `X-CSRFToken` — toda mutação
 * dava 403 em produção (`SessionAuthentication` do DRF). `fetchAPI` injeta o
 * CSRF nos métodos mutantes, faz retry em 403 de CSRF e respeita `VITE_API_URL`.
 *
 * Backend: `DeslocamentoViewSet` (`apps/core/views_deslocamento.py`).
 * Escrita é owner-forced (`usuario=request.user`) desde #1454/PR #1542 — o
 * campo `usuario` no payload de create é ignorado pelo backend.
 */

import { fetchAPI, buildUrl, type QueryParams } from './config';
import type { ID, PaginatedResponse } from '../types';

/**
 * Deslocamento como retornado pelo backend.
 *
 * Espelha `DeslocamentoSerializer` (`apps/core/serializers/workflow.py`).
 * `usuario_nome` é derivado (read-only).
 */
export interface DeslocamentoRecord {
  id: ID;
  usuario: ID;
  usuario_nome: string;
  origem: string;
  destino: string;
  start_date: string; // ISO 8601 date
  end_date: string; // ISO 8601 date
  observacao?: string;
}

/**
 * Formador elegível para o select, já filtrado pela gerência do usuário logado.
 * Saída de `GET /api/options/formadores-do-setor/`.
 */
export interface FormadorOption {
  id: ID;
  first_name: string;
  last_name: string;
}

/**
 * Filtros de `GET /api/deslocamentos/`.
 *
 * O scope por gerência é aplicado no backend (`get_queryset`); estes filtros
 * apenas refinam dentro do que o usuário já pode ver.
 */
export interface DeslocamentoFilters {
  usuario_id?: ID;
  data_inicio?: string; // YYYY-MM-DD
  data_fim?: string; // YYYY-MM-DD
  origem?: string;
  destino?: string;
  page?: number;
}

/**
 * Payload de create/update. `usuario` é enviado apenas em update (o backend
 * força `usuario=request.user` no create — ver #1454).
 */
export interface DeslocamentoPayload {
  usuario?: ID;
  origem: string;
  destino: string;
  start_date: string; // YYYY-MM-DD
  end_date: string; // YYYY-MM-DD
  observacao?: string;
}

/**
 * Lista deslocamentos visíveis ao usuário (paginado, 50 por página).
 */
export async function listDeslocamentos(
  filters: DeslocamentoFilters = {}
): Promise<PaginatedResponse<DeslocamentoRecord>> {
  const url = buildUrl('/deslocamentos/', filters as QueryParams);
  return await fetchAPI<PaginatedResponse<DeslocamentoRecord>>(url);
}

/**
 * Lista formadores do setor do usuário logado (para o select do formulário).
 */
export async function listFormadoresDoSetor(): Promise<FormadorOption[]> {
  return await fetchAPI<FormadorOption[]>('/options/formadores-do-setor/');
}

/**
 * Cria deslocamento. Backend força `usuario=request.user` (#1454).
 */
export async function createDeslocamento(
  payload: DeslocamentoPayload
): Promise<DeslocamentoRecord> {
  return await fetchAPI<DeslocamentoRecord>('/deslocamentos/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Atualiza deslocamento existente.
 */
export async function updateDeslocamento(
  id: ID,
  payload: DeslocamentoPayload
): Promise<DeslocamentoRecord> {
  return await fetchAPI<DeslocamentoRecord>(`/deslocamentos/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

/**
 * Remove deslocamento.
 */
export async function deleteDeslocamento(id: ID): Promise<void> {
  await fetchAPI<void>(`/deslocamentos/${id}/`, { method: 'DELETE' });
}
