/**
 * datModule API client — exercised against MSW handlers (issue #849, phase 2).
 */
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

vi.mock('../../services/syncChannel', () => ({
  syncChannel: { publish: vi.fn(), subscribe: vi.fn(() => () => {}) },
}));

import { getCoordenadorAlocacoes, updateCadastroEtapa } from '../datModule';

type RequestLog = { url: string; method: string; body?: unknown };

describe('datModule API (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
  });

  test('updateCadastroEtapa uses POST on /dat/cadastros/{id}/etapa/', async () => {
    const payload = { id: 7, etapa: 'chaves', status: 'concluido' };
    server.use(
      http.post(apiUrl('/dat/cadastros/7/etapa/'), async ({ request }) => {
        requests.push({ url: request.url, method: request.method, body: await request.json() });
        return HttpResponse.json(payload);
      }),
    );

    const response = await updateCadastroEtapa(7, 'chaves', 'concluido');

    expect(response).toEqual(payload);
    expect(requests).toHaveLength(1);
    expect(requests[0].body).toEqual({ etapa: 'chaves', status: 'concluido' });
  });

  test('getCoordenadorAlocacoes devolve as ações do objeto {acoes,total_acoes} (M18-04)', async () => {
    const acao = { id: 1, projeto_nome: 'P', municipio_nome: 'M' };
    server.use(
      http.get(apiUrl('/dat/coordenadores/5/alocacoes/'), () =>
        HttpResponse.json({ acoes: [acao], total_acoes: 1 }),
      ),
    );

    expect(await getCoordenadorAlocacoes(5)).toEqual([acao]);
  });
});
