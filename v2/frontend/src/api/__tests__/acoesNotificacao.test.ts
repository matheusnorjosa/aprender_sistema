/**
 * acoesNotificacao API client — exercised against MSW handlers.
 */
import { beforeEach, describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

import {
  concluirAcao,
  createCicloAcoes,
  getNotificacoesNaoLidasCount,
  listAcoesByCiclo,
  listAcoesInstancia,
  listCiclosAcoes,
  listNotificacoesInternas,
  marcarNotificacaoLida,
  marcarTodasNotificacoesLidas,
  registrarAncora,
} from '../acoesNotificacao';
import type {
  ConcluirAcaoPayload,
  CriarCicloPayload,
  RegistrarAncoraPayload,
} from '../../types/acoesNotificacao';

type RequestLog = { url: string; method: string; body?: unknown };

function captureGet(path: string, payload: unknown, log: RequestLog[]) {
  return http.get(apiUrl(path), ({ request }) => {
    log.push({ url: request.url, method: 'GET' });
    return HttpResponse.json(payload);
  });
}

function capturePost(path: string, payload: unknown, log: RequestLog[]) {
  return http.post(apiUrl(path), async ({ request }) => {
    log.push({ url: request.url, method: 'POST', body: await request.json() });
    return HttpResponse.json(payload);
  });
}

function capturePostSemBody(path: string, payload: unknown, log: RequestLog[]) {
  return http.post(apiUrl(path), ({ request }) => {
    log.push({ url: request.url, method: 'POST' });
    return HttpResponse.json(payload);
  });
}

describe('acoesNotificacao API (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  describe('ciclos', () => {
    test('listCiclosAcoes usa GET /ciclos-acoes/ com filtros', async () => {
      server.use(
        captureGet('/ciclos-acoes/', { count: 0, next: null, previous: null, results: [] }, requests),
      );

      await listCiclosAcoes({ ano: 2026, status: 'ativo' });

      expect(requests).toHaveLength(1);
      const u = new URL(requests[0].url);
      expect(u.pathname).toBe('/api/ciclos-acoes/');
      expect(u.searchParams.get('ano')).toBe('2026');
      expect(u.searchParams.get('status')).toBe('ativo');
    });

    test('createCicloAcoes usa POST /ciclos-acoes/ com body', async () => {
      const payload: CriarCicloPayload = {
        projeto_id: 1,
        municipio_id: 2,
        semestre: '1S',
        ano: 2026,
      };
      server.use(capturePost('/ciclos-acoes/', { id: 9, ...payload }, requests));

      await createCicloAcoes(payload);

      expect(requests).toHaveLength(1);
      expect(new URL(requests[0].url).pathname).toBe('/api/ciclos-acoes/');
      expect(requests[0].method).toBe('POST');
      expect(requests[0].body).toEqual(payload);
    });

    test('createCicloAcoes propaga mensagem de erro do backend', async () => {
      server.use(
        http.post(apiUrl('/ciclos-acoes/'), () =>
          HttpResponse.json({ detail: 'Ciclo já existe' }, { status: 400 }),
        ),
      );

      await expect(
        createCicloAcoes({ projeto_id: 1, municipio_id: 2, semestre: '2S', ano: 2026 }),
      ).rejects.toThrow('Ciclo já existe');
    });
  });

  describe('ações', () => {
    test('listAcoesInstancia usa GET /acoes-instancia/ com filtros', async () => {
      server.use(
        captureGet('/acoes-instancia/', { count: 0, next: null, previous: null, results: [] }, requests),
      );

      await listAcoesInstancia({ ciclo: 5, estado: 'pendente' });

      expect(requests).toHaveLength(1);
      const u = new URL(requests[0].url);
      expect(u.pathname).toBe('/api/acoes-instancia/');
      expect(u.searchParams.get('ciclo')).toBe('5');
      expect(u.searchParams.get('estado')).toBe('pendente');
    });

    test('listAcoesByCiclo desembrulha results de resposta paginada', async () => {
      const acao = { id: 11, ciclo: 5, ordem: 1 };
      server.use(
        captureGet(
          '/ciclos-acoes/5/acoes/',
          { count: 1, next: null, previous: null, results: [acao] },
          requests,
        ),
      );

      const data = await listAcoesByCiclo(5);

      expect(requests).toHaveLength(1);
      expect(new URL(requests[0].url).pathname).toBe('/api/ciclos-acoes/5/acoes/');
      expect(data).toEqual([acao]);
    });

    test('listAcoesByCiclo aceita resposta em array direto', async () => {
      const lista = [{ id: 12, ciclo: 6, ordem: 2 }];
      server.use(captureGet('/ciclos-acoes/6/acoes/', lista, requests));

      const data = await listAcoesByCiclo(6);

      expect(data).toEqual(lista);
    });

    test('registrarAncora usa POST /acoes-instancia/{id}/registrar-ancora/ com body', async () => {
      const payload: RegistrarAncoraPayload = { data_ancora: '2026-01-10', observacao: 'nota' };
      server.use(capturePost('/acoes-instancia/11/registrar-ancora/', { id: 11 }, requests));

      await registrarAncora(11, payload);

      expect(requests).toHaveLength(1);
      expect(new URL(requests[0].url).pathname).toBe('/api/acoes-instancia/11/registrar-ancora/');
      expect(requests[0].method).toBe('POST');
      expect(requests[0].body).toEqual(payload);
    });

    test('concluirAcao usa POST /acoes-instancia/{id}/concluir/ com body', async () => {
      const payload: ConcluirAcaoPayload = { data_realizacao: '2026-01-20', observacao: 'feito' };
      server.use(capturePost('/acoes-instancia/11/concluir/', { id: 11 }, requests));

      await concluirAcao(11, payload);

      expect(requests).toHaveLength(1);
      expect(new URL(requests[0].url).pathname).toBe('/api/acoes-instancia/11/concluir/');
      expect(requests[0].method).toBe('POST');
      expect(requests[0].body).toEqual(payload);
    });
  });

  describe('notificações', () => {
    test('listNotificacoesInternas usa GET /notificacoes-internas/ com filtros', async () => {
      server.use(
        captureGet(
          '/notificacoes-internas/',
          { count: 0, next: null, previous: null, results: [] },
          requests,
        ),
      );

      await listNotificacoesInternas({ lida: false, page: 2 });

      expect(requests).toHaveLength(1);
      const u = new URL(requests[0].url);
      expect(u.pathname).toBe('/api/notificacoes-internas/');
      expect(u.searchParams.get('lida')).toBe('false');
      expect(u.searchParams.get('page')).toBe('2');
    });

    test('marcarNotificacaoLida usa POST /notificacoes-internas/{id}/marcar-lida/', async () => {
      server.use(capturePostSemBody('/notificacoes-internas/7/marcar-lida/', { id: 7, lida: true }, requests));

      await marcarNotificacaoLida(7);

      expect(requests).toHaveLength(1);
      expect(new URL(requests[0].url).pathname).toBe('/api/notificacoes-internas/7/marcar-lida/');
      expect(requests[0].method).toBe('POST');
    });

    test('getNotificacoesNaoLidasCount usa GET /notificacoes-internas/unread-count/', async () => {
      server.use(captureGet('/notificacoes-internas/unread-count/', { count: 3 }, requests));

      const data = await getNotificacoesNaoLidasCount();

      expect(requests).toHaveLength(1);
      expect(new URL(requests[0].url).pathname).toBe('/api/notificacoes-internas/unread-count/');
      expect(data).toEqual({ count: 3 });
    });

    test('marcarTodasNotificacoesLidas usa POST /notificacoes-internas/marcar-todas-lidas/', async () => {
      server.use(
        capturePostSemBody('/notificacoes-internas/marcar-todas-lidas/', { updated: 5 }, requests),
      );

      const data = await marcarTodasNotificacoesLidas();

      expect(requests).toHaveLength(1);
      expect(new URL(requests[0].url).pathname).toBe('/api/notificacoes-internas/marcar-todas-lidas/');
      expect(requests[0].method).toBe('POST');
      expect(data).toEqual({ updated: 5 });
    });
  });
});
