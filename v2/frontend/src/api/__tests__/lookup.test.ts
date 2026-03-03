import { beforeEach, describe, expect, test, vi } from 'vitest';

const { fetchAPIMock, buildUrlMock } = vi.hoisted(() => ({
  fetchAPIMock: vi.fn(),
  buildUrlMock: vi.fn(),
}));

vi.mock('../config', () => ({
  fetchAPI: fetchAPIMock,
  buildUrl: buildUrlMock,
}));

import {
  lookupMunicipios,
  lookupMunicipiosWithFilters,
  lookupProjetos,
  lookupProjetosWithFilters,
} from '../lookup';

describe('lookup API filters', () => {
  beforeEach(() => {
    fetchAPIMock.mockReset();
    buildUrlMock.mockReset();
    buildUrlMock.mockImplementation((path: string) => path);
    fetchAPIMock.mockResolvedValue([]);
  });

  test('lookupMunicipios mantém contrato atual (q simples)', async () => {
    await lookupMunicipios('Fort');

    expect(buildUrlMock).toHaveBeenCalledWith('/lookup/municipios/', { q: 'Fort' });
    expect(fetchAPIMock).toHaveBeenCalledWith('/lookup/municipios/');
  });

  test('lookupMunicipiosWithFilters envia com_compra + projeto_id', async () => {
    await lookupMunicipiosWithFilters({ q: '', com_compra: true, projeto_id: 123 });

    expect(buildUrlMock).toHaveBeenCalledWith('/lookup/municipios/', {
      q: '',
      com_compra: true,
      projeto_id: 123,
    });
    expect(fetchAPIMock).toHaveBeenCalledWith('/lookup/municipios/');
  });

  test('lookupProjetos mantém contrato atual (q simples)', async () => {
    await lookupProjetos('Ace');

    expect(buildUrlMock).toHaveBeenCalledWith('/lookup/projetos/', { q: 'Ace' });
    expect(fetchAPIMock).toHaveBeenCalledWith('/lookup/projetos/');
  });

  test('lookupProjetosWithFilters envia municipio_id + com_compra', async () => {
    await lookupProjetosWithFilters({ q: 'A', com_compra: true, municipio_id: 77 });

    expect(buildUrlMock).toHaveBeenCalledWith('/lookup/projetos/', {
      q: 'A',
      com_compra: true,
      municipio_id: 77,
    });
    expect(fetchAPIMock).toHaveBeenCalledWith('/lookup/projetos/');
  });
});
