/**
 * API Client - Solicitações
 *
 * Consome endpoints do backend AS v2 para gerenciar solicitações de eventos.
 */

import { fetchAPI, buildUrl, type QueryParams } from './config';
import logger from '../utils/logger';
import type {
  ID,
  PaginatedResponse,
  Solicitacao,
  SolicitacaoPayload,
  SolicitacaoFilters,
  MunicipioOption,
  ProjetoOption,
  TipoEventoOption,
  UsuarioOption,
  BatchOperationResult,
  PublishResult,
} from '../types';

// Mapeamento de aliases de status (inglês → português)
// Mantido para compatibilidade com código legado
const STATUS_MAP: Record<string, string> = {
  pending: 'pendente',
  approved: 'aprovado',
  rejected: 'reprovado',
};

/**
 * Publish options for GCal
 */
export interface PublishOptions {
  dry_run?: boolean;
  apply_blocked?: boolean;
}

/**
 * GCal preview payload
 */
export interface GCalPreviewPayload {
  summary: string;
  description: string;
  start: { dateTime: string; timeZone: string };
  end: { dateTime: string; timeZone: string };
  attendees: Array<{ email: string }>;
}

/**
 * Lista solicitações de eventos com filtros.
 *
 * @param filters - Parâmetros de filtro
 */
export async function listSolicitacoes(filters: SolicitacaoFilters = {}): Promise<PaginatedResponse<Solicitacao>> {
  // Mapear status aliases (inglês→português) se necessário
  const normalizedFilters = { ...filters } as Record<string, unknown>;

  if (normalizedFilters.status) {
    normalizedFilters.status = STATUS_MAP[normalizedFilters.status as string] ?? normalizedFilters.status;
  }

  const url = buildUrl('/solicitacoes/', normalizedFilters as QueryParams);
  return await fetchAPI(url);
}

/**
 * Cria uma nova solicitação de evento.
 *
 * @param body - Dados da solicitação
 */
export async function createSolicitacao(body: SolicitacaoPayload): Promise<Solicitacao> {
  logger.debug('=== createSolicitacao ===');
  logger.debug('Body enviado:', body);
  logger.debug('JSON stringificado:', JSON.stringify(body));

  return await fetchAPI('/solicitacoes/', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Aprova uma solicitação pendente.
 *
 * @param id - ID da solicitação
 * @param reason - Motivo/justificativa (opcional)
 */
export async function approveSolicitacao(id: ID, reason: string = ''): Promise<Solicitacao> {
  return await fetchAPI(`/solicitacoes/${id}/approve/`, {
    method: 'PATCH',
    body: JSON.stringify(reason ? { reason } : {}),
  });
}

/**
 * Reprova uma solicitação pendente.
 *
 * @param id - ID da solicitação
 * @param reason - Motivo/justificativa (opcional)
 */
export async function rejectSolicitacao(id: ID, reason: string = ''): Promise<Solicitacao> {
  return await fetchAPI(`/solicitacoes/${id}/reject/`, {
    method: 'PATCH',
    body: JSON.stringify(reason ? { reason } : {}),
  });
}

/**
 * Busca detalhes de uma solicitação específica.
 *
 * @param id - ID da solicitação
 */
export async function getSolicitacao(id: ID): Promise<Solicitacao> {
  return await fetchAPI(`/solicitacoes/${id}/`);
}

/**
 * Atualiza uma solicitação existente (PATCH parcial).
 *
 * Regras:
 * - Apenas o criador ou usuários privilegiados (Superintendência/DAT) podem editar
 * - Não é possível editar solicitações já publicadas no Google Calendar
 * - Não é possível editar solicitações reprovadas
 *
 * @param id - ID da solicitação
 * @param data - Campos a atualizar (parcial)
 */
export async function updateSolicitacao(id: ID, data: Partial<SolicitacaoPayload>): Promise<Solicitacao> {
  logger.debug('=== updateSolicitacao ===');
  logger.debug('ID:', id);
  logger.debug('Data:', data);

  return await fetchAPI(`/solicitacoes/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

/**
 * Exclui uma solicitação existente (DELETE).
 *
 * Regras:
 * - Apenas o criador ou usuários privilegiados (Superintendência/DAT) podem excluir
 * - Não é possível excluir solicitações já publicadas no Google Calendar
 *
 * @param id - ID da solicitação
 */
export async function deleteSolicitacao(id: ID): Promise<void> {
  logger.debug('=== deleteSolicitacao ===');
  logger.debug('ID:', id);

  return await fetchAPI(`/solicitacoes/${id}/`, {
    method: 'DELETE',
  });
}

/**
 * Preview do payload GCal de uma solicitação.
 *
 * @param id - ID da solicitação
 */
export async function previewSolicitacao(id: ID): Promise<GCalPreviewPayload> {
  return await fetchAPI(`/solicitacoes/${id}/preview-gcal/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

/**
 * Publica solicitação no Google Calendar.
 *
 * @param id - ID da solicitação
 * @param body - Opções (dry_run, apply_blocked, etc.)
 */
export async function publishSolicitacao(id: ID, body: PublishOptions = {}): Promise<PublishResult> {
  return await fetchAPI(`/solicitacoes/${id}/publish/`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * Republicar solicitação no Google Calendar (força UPDATE) - Fase 4.
 *
 * Reseta gcal_payload_hash para forçar UPDATE mesmo se já publicado.
 * Enfileira task_publish_solicitacao_to_gcal para republicação.
 *
 * @param id - ID da solicitação aprovada
 */
export async function resyncSolicitacao(id: ID): Promise<PublishResult> {
  return await fetchAPI(`/solicitacoes/${id}/resync-gcal/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

/**
 * Cancelar evento no Google Calendar e limpar campos - Fase 4.
 *
 * Deleta evento do Calendar (trata 404 como sucesso - idempotência) e limpa
 * todos os campos relacionados: external_event_id, meet_link, gcal_payload_hash.
 *
 * @param id - ID da solicitação com evento publicado
 */
export async function cancelSolicitacao(id: ID): Promise<PublishResult> {
  return await fetchAPI(`/solicitacoes/${id}/cancel-gcal/`, {
    method: 'POST',
    body: JSON.stringify({}),
  });
}

// ========================================
// Endpoints de opções (dropdowns/selects)
// ========================================

/**
 * Lista municípios para seleção.
 */
export async function listMunicipiosOptions(): Promise<MunicipioOption[]> {
  return await fetchAPI('/options/municipios/');
}

/**
 * Lista projetos para seleção.
 */
export async function listProjetosOptions(): Promise<ProjetoOption[]> {
  return await fetchAPI('/options/projetos/');
}

/**
 * Lista tipos de evento para seleção.
 */
export async function listTiposEventoOptions(): Promise<TipoEventoOption[]> {
  return await fetchAPI('/options/tipos-evento/');
}

/**
 * Lista usuários para seleção.
 *
 * @param params - Parâmetros opcionais (ex: search)
 */
export async function listUsuariosOptions(params: QueryParams = {}): Promise<UsuarioOption[]> {
  const url = buildUrl('/options/usuarios/', params);
  return await fetchAPI(url);
}

// ========================================
// Endpoints de operações em lote
// ========================================

/**
 * Aprovar múltiplas solicitações em lote.
 *
 * @param ids - IDs das solicitações a aprovar
 */
export async function approveSolicitacoesBatch(ids: ID[]): Promise<BatchOperationResult> {
  return await fetchAPI('/solicitacoes/batch-approve/', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  });
}

/**
 * Reprovar múltiplas solicitações em lote.
 *
 * @param ids - IDs das solicitações a reprovar
 */
export async function rejectSolicitacoesBatch(ids: ID[]): Promise<BatchOperationResult> {
  return await fetchAPI('/solicitacoes/batch-reject/', {
    method: 'POST',
    body: JSON.stringify({ ids }),
  });
}

// Re-exportar checkAvailability de availability
export { checkAvailability } from './availability';
