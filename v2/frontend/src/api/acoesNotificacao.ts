import { fetchAPI, buildUrl, type QueryParams } from './config';
import type {
  AcaoInstancia,
  CicloAcoes,
  ConcluirAcaoPayload,
  CriarCicloPayload,
  NotificacaoInterna,
  PaginatedAcoes,
  PaginatedCiclos,
  PaginatedNotificacoes,
  RegistrarAncoraPayload,
} from '../types/acoesNotificacao';

export async function listCiclosAcoes(params: QueryParams = {}): Promise<PaginatedCiclos> {
  return fetchAPI(buildUrl('/ciclos-acoes/', params));
}

export async function createCicloAcoes(payload: CriarCicloPayload): Promise<CicloAcoes> {
  return fetchAPI('/ciclos-acoes/', { method: 'POST', body: JSON.stringify(payload) });
}

export async function listAcoesInstancia(params: QueryParams = {}): Promise<PaginatedAcoes> {
  return fetchAPI(buildUrl('/acoes-instancia/', params));
}

export async function listAcoesByCiclo(cicloId: number): Promise<AcaoInstancia[]> {
  const data = await fetchAPI<PaginatedAcoes | AcaoInstancia[]>(`/ciclos-acoes/${cicloId}/acoes/`);
  return Array.isArray(data) ? data : data.results;
}

export async function registrarAncora(acaoId: number, payload: RegistrarAncoraPayload): Promise<AcaoInstancia> {
  return fetchAPI(`/acoes-instancia/${acaoId}/registrar-ancora/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function concluirAcao(acaoId: number, payload: ConcluirAcaoPayload): Promise<AcaoInstancia> {
  return fetchAPI(`/acoes-instancia/${acaoId}/concluir/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function listNotificacoesInternas(params: QueryParams = {}): Promise<PaginatedNotificacoes> {
  return fetchAPI(buildUrl('/notificacoes-internas/', params));
}

export async function marcarNotificacaoLida(notificacaoId: number): Promise<NotificacaoInterna> {
  return fetchAPI(`/notificacoes-internas/${notificacaoId}/marcar-lida/`, { method: 'POST' });
}

export async function getNotificacoesNaoLidasCount(): Promise<{ count: number }> {
  return fetchAPI('/notificacoes-internas/unread-count/');
}

export async function marcarTodasNotificacoesLidas(): Promise<{ updated: number }> {
  return fetchAPI('/notificacoes-internas/marcar-todas-lidas/', { method: 'POST' });
}
