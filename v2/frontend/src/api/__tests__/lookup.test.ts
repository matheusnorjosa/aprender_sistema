/**
 * lookup API client — exercised against MSW handlers (issue #849, phase 2).
 */
import { beforeEach, describe, expect, test } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../test/mocks/server';
import { apiUrl } from '../../test/mocks/handlers';

import {
  lookupMunicipios,
  lookupMunicipiosWithFilters,
  lookupProjetos,
  lookupUsuarios,
} from '../lookup';

type RequestLog = { pathname: string; params: URLSearchParams };

describe('lookup API filters (MSW)', () => {
  let requests: RequestLog[];

  beforeEach(() => {
    requests = [];
    server.use(
      http.get(apiUrl('/lookup/municipios/'), ({ request }) => {
        const u = new URL(request.url);
        requests.push({ pathname: u.pathname, params: u.searchParams });
        return HttpResponse.json([]);
      }),
      http.get(apiUrl('/lookup/projetos/'), ({ request }) => {
        const u = new URL(request.url);
        requests.push({ pathname: u.pathname, params: u.searchParams });
        return HttpResponse.json([]);
      }),
      http.get(apiUrl('/lookup/usuarios/'), ({ request }) => {
        const u = new URL(request.url);
        requests.push({ pathname: u.pathname, params: u.searchParams });
        return HttpResponse.json([]);
      }),
    );
  });

  test('lookupUsuarios com projeto envia projeto_id (P9-5: pessoas da gerência do projeto)', async () => {
    await lookupUsuarios('', 'Coordenador', 123);

    expect(requests).toHaveLength(1);
    expect(requests[0].pathname).toBe('/api/lookup/usuarios/');
    expect(requests[0].params.get('role')).toBe('Coordenador');
    expect(requests[0].params.get('projeto_id')).toBe('123');
  });

  test('lookupUsuarios sem projeto não envia projeto_id', async () => {
    await lookupUsuarios('ana', 'Formador');

    expect(requests).toHaveLength(1);
    expect(requests[0].params.get('q')).toBe('ana');
    expect(requests[0].params.has('projeto_id')).toBe(false);
  });

  test('lookupMunicipios mantém contrato atual (q simples)', async () => {
    await lookupMunicipios('Fort');

    expect(requests).toHaveLength(1);
    expect(requests[0].pathname).toBe('/api/lookup/municipios/');
    expect(requests[0].params.get('q')).toBe('Fort');
  });

  test('lookupMunicipiosWithFilters envia com_compra + projeto_id', async () => {
    await lookupMunicipiosWithFilters({ q: '', com_compra: true, projeto_id: 123 });

    expect(requests).toHaveLength(1);
    expect(requests[0].pathname).toBe('/api/lookup/municipios/');
    expect(requests[0].params.get('com_compra')).toBe('true');
    expect(requests[0].params.get('projeto_id')).toBe('123');
  });

  test('lookupProjetos mantém contrato atual (q simples)', async () => {
    await lookupProjetos('Ace');

    expect(requests).toHaveLength(1);
    expect(requests[0].pathname).toBe('/api/lookup/projetos/');
    expect(requests[0].params.get('q')).toBe('Ace');
    expect(requests[0].params.has('com_compra')).toBe(false);
  });

  test('lookupProjetos envia com_compra quando pedido (regra da compra)', async () => {
    await lookupProjetos('', { com_compra: true });

    expect(requests).toHaveLength(1);
    expect(requests[0].pathname).toBe('/api/lookup/projetos/');
    expect(requests[0].params.get('com_compra')).toBe('true');
  });
});
