/**
 * Auditoria UX 30/09, rodada 4 (BAIXA): o upload das importações (`postMultipart`) usava o
 * `fetch` cru. Sem rede, a tela mostrava "Failed to fetch" ou, com o service worker ativo,
 * "HTTP 503: " (o SW devolve 503 com `error.code: OFFLINE`, sem `detail`). Agora passa pelo
 * `fetchNaRede` e diz "Sem conexão com o servidor.", como o `fetchAPI`.
 */
import { describe, test, expect, beforeEach } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';
import { importCompras } from '../ops';

const URL_DO_IMPORT = '/controle/import-compras/';
const planilha = (): File => new File(['a;b\n1;2'], 'compras.csv', { type: 'text/csv' });

describe('postMultipart (importações) — sem conexão', () => {
  beforeEach(() => {
    document.cookie = 'csrftoken=tok; path=/';
  });

  test('controle: com rede, o upload chega ao servidor e devolve o resultado', async () => {
    server.use(http.post(apiUrl(URL_DO_IMPORT), () => HttpResponse.json({ created: 2, updated: 0, errors: [] })));

    await expect(importCompras(planilha())).resolves.toMatchObject({ created: 2 });
  });

  test('sem rede: "Sem conexão com o servidor." (não "Failed to fetch")', async () => {
    server.use(http.post(apiUrl(URL_DO_IMPORT), () => HttpResponse.error()));

    await expect(importCompras(planilha())).rejects.toThrow('Sem conexão com o servidor.');
  });

  test('resposta OFFLINE do service worker: "Sem conexão com o servidor." (não "HTTP 503: ")', async () => {
    server.use(
      http.post(apiUrl(URL_DO_IMPORT), () =>
        HttpResponse.json({ error: { code: 'OFFLINE', message: 'Voce esta offline.' } }, { status: 503 }),
      ),
    );

    await expect(importCompras(planilha())).rejects.toThrow('Sem conexão com o servidor.');
  });
});
