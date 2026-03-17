import type { AxiosResponse } from 'axios';

import api from '../api';
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

async function apiRequest<T>(requestFn: () => Promise<AxiosResponse<T>>): Promise<T> {
  const response = await requestFn();
  return response.data;
}

export async function listCiclosAcoes(params?: Record<string, unknown>): Promise<PaginatedCiclos> {
  return apiRequest(() => api.get('/ciclos-acoes/', { params }));
}

export async function createCicloAcoes(payload: CriarCicloPayload): Promise<CicloAcoes> {
  return apiRequest(() => api.post('/ciclos-acoes/', payload));
}

export async function listAcoesInstancia(params?: Record<string, unknown>): Promise<PaginatedAcoes> {
  return apiRequest(() => api.get('/acoes-instancia/', { params }));
}

export async function listAcoesByCiclo(cicloId: number): Promise<AcaoInstancia[]> {
  const data = await apiRequest<PaginatedAcoes | AcaoInstancia[]>(() => api.get(`/ciclos-acoes/${cicloId}/acoes/`));
  if (Array.isArray(data)) {
    return data;
  }
  return data.results;
}

export async function registrarAncora(acaoId: number, payload: RegistrarAncoraPayload): Promise<AcaoInstancia> {
  return apiRequest(() => api.post(`/acoes-instancia/${acaoId}/registrar-ancora/`, payload));
}

export async function concluirAcao(acaoId: number, payload: ConcluirAcaoPayload): Promise<AcaoInstancia> {
  return apiRequest(() => api.post(`/acoes-instancia/${acaoId}/concluir/`, payload));
}

export async function listNotificacoesInternas(params?: Record<string, unknown>): Promise<PaginatedNotificacoes> {
  return apiRequest(() => api.get('/notificacoes-internas/', { params }));
}

export async function marcarNotificacaoLida(notificacaoId: number): Promise<NotificacaoInterna> {
  return apiRequest(() => api.post(`/notificacoes-internas/${notificacaoId}/marcar-lida/`));
}

export async function getNotificacoesNaoLidasCount(): Promise<{ count: number }> {
  return apiRequest(() => api.get('/notificacoes-internas/unread-count/'));
}

export async function marcarTodasNotificacoesLidas(): Promise<{ updated: number }> {
  return apiRequest(() => api.post('/notificacoes-internas/marcar-todas-lidas/'));
}
